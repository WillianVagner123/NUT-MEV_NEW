from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from nutev.reference_identity import dedupe_records

from pubmed_search_details import collect_pubmed_search_details
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
EXHAUSTIVE_SENTINEL = 2_147_483_647
MAX_PROVIDER_QUERY_LENGTH = 20_000


def _emit(callback: ProgressCallback | None, event: dict[str, Any]) -> None:
    if callback is None:
        return
    try:
        callback(event)
    except Exception:
        return


def _provider_query_for(
    provider: str,
    question: str,
    provider_queries: dict[str, str] | None,
) -> str:
    query = str((provider_queries or {}).get(provider) or question).strip()
    if not query:
        query = question
    if len(query) > MAX_PROVIDER_QUERY_LENGTH:
        raise ValueError(
            f"Query compilada para {provider} excede {MAX_PROVIDER_QUERY_LENGTH} caracteres"
        )
    return query


def _decorate_rows(
    rows: list[dict[str, Any]],
    *,
    provider: str,
    question: str,
    provider_query: str,
    search_id: str,
) -> list[dict[str, Any]]:
    decorated: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item.setdefault("source_provider", provider)
        item.setdefault("source", provider)
        item["query"] = question
        item["provider_query"] = provider_query
        item["interactive_search_id"] = search_id
        item["interactive_retrieved_at"] = _now()
        decorated.append(item)
    return decorated


def _pubmed_audit_gap(status_item: dict[str, Any]) -> str | None:
    if status_item.get("provider") != "pubmed":
        return None
    audit_error = str(status_item.get("search_details_error") or "").strip()
    if audit_error:
        return audit_error
    details = status_item.get("search_details")
    if not isinstance(details, dict) or not details.get("search_details_complete"):
        return "pubmed_search_details_missing"
    if details.get("errors_present"):
        return "pubmed_search_details_errors_present"
    count = details.get("count")
    total_found = status_item.get("total_found")
    if count is not None and total_found is not None and int(count) != int(total_found):
        return f"pubmed_count_mismatch:{count}!={total_found}"
    return None


def search_evidence_progressive(
    query: object,
    *,
    providers: list[str] | None = None,
    per_provider: int = 25,
    max_results: int = 100,
    provider_queries: dict[str, str] | None = None,
    query_plan: dict[str, Any] | None = None,
    output_root: Path | None = None,
    on_progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Run NutEV search sequentially while emitting provider progress.

    ``0/0`` removes NutEV's internal result ceilings. Provider-specific review
    queries are persisted exactly. Review-grade PubMed runs also preserve ESearch
    Search Details (translation, warnings, errors and count) separately from the
    retrieval result so syntax warnings cannot be silently lost.
    """

    question = _clean_query(query)
    chosen = list(dict.fromkeys(providers or PROVIDER_ORDER))
    invalid = [provider for provider in chosen if provider not in PROVIDER_ORDER]
    if invalid:
        raise ValueError("Providers inválidos: " + ", ".join(invalid))
    if not chosen:
        raise ValueError("Selecione pelo menos um provider.")

    raw_per_provider = int(per_provider)
    raw_max_results = int(max_results)
    exhaustive = raw_per_provider == 0 and raw_max_results == 0
    if exhaustive:
        provider_limit = EXHAUSTIVE_SENTINEL
        result_limit: int | None = None
    else:
        provider_limit = max(1, min(raw_per_provider, MAX_PER_PROVIDER))
        result_limit = max(1, min(raw_max_results, MAX_RESULTS))

    plan_mode = str((query_plan or {}).get("mode") or "")
    structured_review = plan_mode == "structured_review"
    exact_review = plan_mode == "exact_review"
    review_mode = structured_review or exact_review
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
            "exhaustive": exhaustive,
            "structured_review": structured_review,
            "exact_review": exact_review,
        },
    )

    for index, provider in enumerate(chosen, start=1):
        started = _now()
        effective_query = _provider_query_for(provider, question, provider_queries)
        _emit(
            on_progress,
            {
                "type": "provider_started",
                "provider": provider,
                "label": PROVIDER_LABELS[provider],
                "completed_providers": index - 1,
                "total_providers": len(chosen),
                "exhaustive": exhaustive,
                "structured_review": structured_review,
                "exact_review": exact_review,
            },
        )

        rows: list[dict[str, Any]] = []
        status_item: dict[str, Any]
        latin_summary_path: str | None = None
        search_details: dict[str, Any] | None = None
        search_details_error = ""

        if review_mode and provider == "pubmed" and not network_disabled:
            try:
                search_details = collect_pubmed_search_details(effective_query)
            except Exception as exc:
                search_details_error = f"{type(exc).__name__}: {exc}"

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
                raw = _provider_call(provider, effective_query, provider_limit)()
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
                    effective_query,
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
            if exhaustive:
                status_item["exhaustive_complete"] = False
                status_item["coverage_note"] = (
                    "Native HTML route exposes only the records returned by the public interface; "
                    "NutEV records this as non-demonstrably-exhaustive rather than inventing coverage."
                )
        else:
            raise ValueError(f"Provider não suportado: {provider}")

        status_item["provider_query"] = effective_query
        if query_plan:
            provider_plan = (query_plan.get("provider_queries") or {}).get(provider) or {}
            if isinstance(provider_plan, dict):
                status_item["query_dialect"] = provider_plan.get("dialect")
        if provider == "pubmed" and review_mode:
            status_item["search_details"] = search_details
            status_item["search_details_error"] = search_details_error

        if exhaustive and provider in DIRECT_PROVIDERS:
            total_found = status_item.get("total_found")
            status_item["exhaustive_complete"] = (
                bool(
                    status_item.get("status")
                    in {"completed", "empty", "completed_no_candidates_parsed"}
                )
                and (total_found is None or int(total_found) <= len(rows))
            )

        combined.extend(
            _decorate_rows(
                rows,
                provider=provider,
                question=question,
                provider_query=effective_query,
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
                "exhaustive": exhaustive,
                "structured_review": structured_review,
                "exact_review": exact_review,
            },
        )

    _emit(
        on_progress,
        {
            "type": "finalizing",
            "completed_providers": len(chosen),
            "total_providers": len(chosen),
            "records_before_dedup": len(combined),
            "exhaustive": exhaustive,
            "structured_review": structured_review,
            "exact_review": exact_review,
        },
    )

    unique = dedupe_records(combined)
    ranked = _score_rows(unique) if unique else []
    returned = ranked if result_limit is None else ranked[:result_limit]
    failed = [item["provider"] for item in provider_status if item["status"] == "failed"]
    unavailable = [
        item["provider"] for item in provider_status if item["status"] == "unavailable"
    ]
    non_exhaustive = [
        item["provider"]
        for item in provider_status
        if exhaustive and item.get("exhaustive_complete") is False
    ]
    audit_gaps: list[dict[str, str]] = []
    if review_mode:
        for item in provider_status:
            gap = _pubmed_audit_gap(item)
            if gap:
                audit_gaps.append({"provider": str(item.get("provider") or ""), "reason": gap})

    if exact_review and exhaustive:
        search_mode = "exact_review_global_exhaustive"
    elif exact_review:
        search_mode = "exact_review_bounded"
    elif structured_review and exhaustive:
        search_mode = "structured_review_global_exhaustive"
    elif structured_review:
        search_mode = "structured_review_bounded"
    elif exhaustive:
        search_mode = "global_exhaustive"
    else:
        search_mode = "interactive_bounded"

    limitations = [
        "Busca global não aplica teto interno de quantidade: cada conector direto pagina até esgotar a fonte ou até a própria fonte impor um limite/erro.",
        "LILACS/BVS e SciELO usam as interfaces públicas nativas; se a interface não demonstrar paginação exaustiva, o provider é marcado como não exaustivo em vez de receber cobertura fabricada.",
        "Scopus e Web of Science não são simulados e exigem acesso licenciado separado.",
    ]
    if exact_review:
        limitations.insert(
            0,
            "Modo revisão exata: o NutEV preserva literalmente a sintaxe fornecida para cada provider e registra strategy_id, strategy_version, run_class, query e dialect no query_plan.",
        )
    elif structured_review:
        limitations.insert(
            0,
            "Modo revisão estruturada: cada provider recebe a query compilada registrada no query_plan; vocabulário controlado só é usado quando explicitamente informado/aprovado.",
        )
    if review_mode and "pubmed" in chosen:
        limitations.insert(
            1,
            "PubMed review audit preserva query translation, warninglist, errorlist e count do ESearch em providers[].search_details.",
        )

    if audit_gaps:
        overall_status = "COMPLETE_WITH_AUDIT_GAPS"
    elif failed or unavailable or non_exhaustive:
        overall_status = "COMPLETE_WITH_PROVIDER_GAPS"
    else:
        overall_status = "COMPLETE"

    result = {
        "schema_version": 6 if exact_review else (4 if structured_review else (3 if exhaustive else 2)),
        "search_id": search_id,
        "query": question,
        "created_at": _now(),
        "search_mode": search_mode,
        "exhaustive_requested": exhaustive,
        "status": overall_status,
        "providers": provider_status,
        "failed_providers": failed,
        "unavailable_providers": unavailable,
        "non_exhaustive_providers": non_exhaustive,
        "audit_gaps": audit_gaps,
        "records_before_dedup": len(combined),
        "unique_records": len(unique),
        "returned_records": len(returned),
        "ranking_policy": "query-conditioned retrieval + canonical NutEV reference priority score",
        "ranking_warning": "Ranking é prioridade de leitura; não representa recomendação clínica, elegibilidade científica ou qualidade metodológica.",
        "query_plan": query_plan,
        "latin_summary_path": latin_summary_paths[-1] if latin_summary_paths else None,
        "latin_summary_paths": latin_summary_paths,
        "interactive_limitations": limitations,
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
            "exhaustive": exhaustive,
            "structured_review": structured_review,
            "exact_review": exact_review,
            "review_mode": review_mode,
        },
    )
    return result
