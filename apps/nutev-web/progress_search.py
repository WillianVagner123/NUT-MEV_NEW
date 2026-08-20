from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from nutev.reference_identity import dedupe_records

from search_adapter import (
    DIRECT_PROVIDERS,
    LATIN_PROVIDERS,
    MAX_PER_PROVIDER,
    MAX_RESULTS,
    PROVIDER_LABELS,
    PROVIDER_ORDER,
    _clean_query,
    _latin_rows_and_status,
    _normalize_provider_result,
    _now,
    _output_root,
    _persist_search,
    _provider_call,
    _score_rows,
)

ProgressCallback = Callable[[dict[str, Any]], None]


def _emit(callback: ProgressCallback | None, event: dict[str, Any]) -> None:
    if callback is None:
        return
    try:
        callback(event)
    except Exception:
        # UI/progress reporting must never change retrieval or ranking semantics.
        return


def _decorate_rows(
    rows: list[dict[str, Any]],
    *,
    provider: str,
    question: str,
    search_id: str,
) -> list[dict[str, Any]]:
    decorated: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item.setdefault("source_provider", provider)
        item.setdefault("source", provider)
        item["query"] = question
        item["provider_query"] = item.get("provider_query") or question
        item["interactive_search_id"] = search_id
        item["interactive_retrieved_at"] = _now()
        decorated.append(item)
    return decorated


def search_evidence_progressive(
    query: object,
    *,
    providers: list[str] | None = None,
    per_provider: int = 25,
    max_results: int = 100,
    output_root: Path | None = None,
    on_progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Run the existing NutEV search sequentially while emitting provider progress.

    This function deliberately reuses the same provider clients, Latin-source runner,
    canonical deduplication and score helpers as the synchronous web search. Progress
    reporting is presentation-only and does not alter scientific behavior.
    """

    question = _clean_query(query)
    chosen = list(dict.fromkeys(providers or PROVIDER_ORDER))
    invalid = [provider for provider in chosen if provider not in PROVIDER_ORDER]
    if invalid:
        raise ValueError("Providers inválidos: " + ", ".join(invalid))
    if not chosen:
        raise ValueError("Selecione pelo menos um provider.")

    per_provider = max(1, min(int(per_provider), MAX_PER_PROVIDER))
    max_results = max(1, min(int(max_results), MAX_RESULTS))
    search_id = (
        "web_"
        + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")
        + "_"
        + uuid4().hex[:8]
    )
    root = _output_root(output_root)
    network_disabled = os.environ.get("NUTEV_DISABLE_NETWORK") == "1"

    provider_status: list[dict[str, Any]] = []
    combined: list[dict[str, Any]] = []
    latin_summary_paths: list[str] = []

    _emit(
        on_progress,
        {
            "type": "search_started",
            "search_id": search_id,
            "query": question,
            "total_providers": len(chosen),
        },
    )

    for index, provider in enumerate(chosen, start=1):
        started = _now()
        _emit(
            on_progress,
            {
                "type": "provider_started",
                "provider": provider,
                "label": PROVIDER_LABELS[provider],
                "completed_providers": index - 1,
                "total_providers": len(chosen),
            },
        )

        rows: list[dict[str, Any]] = []
        status_item: dict[str, Any]
        latin_summary_path: str | None = None

        if network_disabled:
            status_item = {
                "provider": provider,
                "label": PROVIDER_LABELS[provider],
                "status": "skipped",
                "returned": 0,
                "total_found": None,
                "error": "network_disabled",
                "started_at": started,
                "finished_at": _now(),
            }
        elif provider in DIRECT_PROVIDERS:
            try:
                raw = _provider_call(provider, question, per_provider)()
                rows, status, total_found, error = _normalize_provider_result(raw)
            except Exception as exc:
                rows = []
                status = "failed"
                total_found = None
                error = f"{type(exc).__name__}: {exc}"
            status_item = {
                "provider": provider,
                "label": PROVIDER_LABELS[provider],
                "status": status,
                "returned": len(rows),
                "total_found": total_found,
                "error": error,
                "started_at": started,
                "finished_at": _now(),
            }
        elif provider in LATIN_PROVIDERS:
            try:
                rows, statuses, latin_summary_path = _latin_rows_and_status(
                    question,
                    [provider],
                    output_root=root,
                )
                status_item = statuses[0] if statuses else {
                    "provider": provider,
                    "label": PROVIDER_LABELS[provider],
                    "status": "failed",
                    "returned": 0,
                    "total_found": None,
                    "error": "latin_provider_missing_status",
                    "started_at": started,
                    "finished_at": _now(),
                }
            except Exception as exc:
                rows = []
                status_item = {
                    "provider": provider,
                    "label": PROVIDER_LABELS[provider],
                    "status": "failed",
                    "returned": 0,
                    "total_found": None,
                    "error": f"{type(exc).__name__}: {exc}",
                    "started_at": started,
                    "finished_at": _now(),
                }
        else:
            raise ValueError(f"Provider não suportado: {provider}")

        combined.extend(
            _decorate_rows(
                rows,
                provider=provider,
                question=question,
                search_id=search_id,
            )
        )
        provider_status.append(status_item)
        if latin_summary_path:
            latin_summary_paths.append(latin_summary_path)

        _emit(
            on_progress,
            {
                "type": "provider_completed",
                "provider": status_item,
                "completed_providers": index,
                "total_providers": len(chosen),
            },
        )

    _emit(
        on_progress,
        {
            "type": "finalizing",
            "completed_providers": len(chosen),
            "total_providers": len(chosen),
            "records_before_dedup": len(combined),
        },
    )

    unique = dedupe_records(combined)
    ranked = _score_rows(unique) if unique else []
    returned = ranked[:max_results]
    failed = [item["provider"] for item in provider_status if item["status"] == "failed"]
    unavailable = [
        item["provider"] for item in provider_status if item["status"] == "unavailable"
    ]

    result = {
        "schema_version": 2,
        "search_id": search_id,
        "query": question,
        "created_at": _now(),
        "status": "COMPLETE_WITH_PROVIDER_GAPS" if (failed or unavailable) else "COMPLETE",
        "providers": provider_status,
        "failed_providers": failed,
        "unavailable_providers": unavailable,
        "records_before_dedup": len(combined),
        "unique_records": len(unique),
        "returned_records": len(returned),
        "ranking_policy": "query-conditioned retrieval + canonical NutEV reference priority score",
        "ranking_warning": "Ranking é prioridade de leitura; não representa recomendação clínica, elegibilidade científica ou qualidade metodológica.",
        "latin_summary_path": latin_summary_paths[-1] if latin_summary_paths else None,
        "latin_summary_paths": latin_summary_paths,
        "interactive_limitations": [
            "LILACS/BVS e SciELO usam as interfaces públicas nativas; bloqueios HTTP são registrados como indisponibilidade e nunca substituídos por resultados fabricados.",
            "Scopus e Web of Science não são simulados e exigem acesso licenciado separado.",
        ],
        "results": returned,
    }
    _persist_search(result, root)
    _emit(
        on_progress,
        {
            "type": "search_completed",
            "search_id": search_id,
            "completed_providers": len(chosen),
            "total_providers": len(chosen),
        },
    )
    return result
