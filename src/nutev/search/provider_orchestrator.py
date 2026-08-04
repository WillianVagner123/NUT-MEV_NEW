from __future__ import annotations

import csv
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from nutev.engine.events import emit_event, write_event
from nutev.search.arxiv import search_arxiv
from nutev.search.base import ProviderResult
from nutev.search.brave_optional import search_brave
from nutev.search.checkpoint import query_hash
from nutev.search.clinicaltrials import search_clinicaltrials
from nutev.search.crossref import search_crossref
from nutev.search.doaj import search_doaj
from nutev.search.europepmc import search_europepmc
from nutev.search.google_pse import search_google_pse
from nutev.search.official_sources import manifest_sources
from nutev.search.openalex import search_openalex
from nutev.search.pubmed import PubMedClient
from nutev.search.scielo import search_scielo
from nutev.search.semantic_scholar import search_semantic_scholar
from nutev.search.serpapi_optional import search_serpapi

OPTIONAL_PROVIDERS = {"google", "google_pse", "serpapi", "brave"}
PERFORMANCE_FIELDS = [
    "run_id",
    "provider",
    "workstream",
    "query_hash",
    "query",
    "status",
    "total_found",
    "rows_returned",
    "duration_seconds",
    "resume_used",
    "checkpoint_path",
]
FAILURE_FIELDS = [
    "run_id",
    "timestamp",
    "provider",
    "workstream",
    "query_hash",
    "query",
    "stage",
    "status",
    "error_type",
    "error_message",
    "recoverable",
    "fallback_used",
    "checkpoint_path",
]


def _append_csv(path: Path, row: dict[str, Any], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in fields})


def _optional_missing(provider: str) -> str | None:
    if provider in {"google", "google_pse"} and not (os.environ.get("GOOGLE_API_KEY") and os.environ.get("GOOGLE_CSE_ID")):
        return "missing GOOGLE_API_KEY/GOOGLE_CSE_ID"
    if provider == "serpapi" and not os.environ.get("SERPAPI_API_KEY"):
        return "missing SERPAPI_API_KEY"
    if provider == "brave" and not os.environ.get("BRAVE_API_KEY"):
        return "missing BRAVE_API_KEY"
    return None


def _registry() -> dict[str, Callable[[str, int, dict[str, Any]], ProviderResult | list[dict[str, Any]]]]:
    return {
        "europepmc": lambda q, limit, ctx: search_europepmc(q, page_size=limit),
        "openalex": lambda q, limit, ctx: search_openalex(
            q,
            per_page=limit,
            filter_value=str(ctx.get("provider_filter") or ""),
        ),
        "crossref": lambda q, limit, ctx: search_crossref(
            q,
            rows=limit,
            filter_value=str(ctx.get("provider_filter") or ""),
        ),
        "doaj": lambda q, limit, ctx: search_doaj(q, page_size=limit),
        "clinicaltrials": lambda q, limit, ctx: search_clinicaltrials(q, page_size=limit),
        "scielo": lambda q, limit, ctx: search_scielo(q, rows=limit),
        "semantic_scholar": lambda q, limit, ctx: search_semantic_scholar(q, page_size=limit),
        "arxiv": lambda q, limit, ctx: search_arxiv(q, page_size=limit),
        "google": lambda q, limit, ctx: search_google_pse(q, limit=limit, context=ctx),
        "google_pse": lambda q, limit, ctx: search_google_pse(q, limit=limit, context=ctx),
        "serpapi": lambda q, limit, ctx: search_serpapi(q, limit=limit, context=ctx),
        "brave": lambda q, limit, ctx: search_brave(q, limit=limit, context=ctx),
        "official_web": lambda q, limit, ctx: manifest_sources(ctx.get("official_manifest") or {}, ctx.get("workstream") or "")[:limit],
        "official_sources": lambda q, limit, ctx: manifest_sources(ctx.get("official_manifest") or {}, ctx.get("workstream") or "")[:limit],
    }


def implemented_search_providers() -> list[str]:
    """Canonical provider ids the orchestrator can actually execute.

    The authority for *which providers exist* is
    ``config/provider_registry.json``; this is the implementation side, and
    ``nutev.search.provider_registry.reconcile_providers`` cross-checks the two so
    they can never silently diverge.
    """
    return sorted(set(_registry()) | {"pubmed"})


def _coerce_result(provider: str, query: str, raw: ProviderResult | list[dict[str, Any]]) -> ProviderResult:
    if isinstance(raw, ProviderResult):
        return raw
    rows = raw or []
    return ProviderResult(
        provider=provider,
        query=query,
        rows=rows,
        total_returned=len(rows),
        status="completed" if rows else "empty",
    )


def _stamp_retrieved_at(result: ProviderResult, retrieved_at: str) -> None:
    """Record the UTC retrieval timestamp on every row (the audit's 'data da
    recuperação'). No connector stamped this; without it a record cannot be tied
    to *when* it was pulled, which reproducible search reporting requires. Existing
    values are preserved (a resumed/checkpointed row keeps its original date)."""
    for row in getattr(result, "rows", None) or []:
        if isinstance(row, dict):
            row.setdefault("retrieved_at", retrieved_at)


def search_provider(
    *,
    provider: str,
    query: str,
    workstream: str,
    limit: int,
    checkpoint_dir: Path,
    resume: bool = False,
    logger: Any | None = None,
    run_id: str | None = None,
    logs_dir: Path | None = None,
    mode: str | None = None,
    context: dict[str, Any] | None = None,
) -> ProviderResult:
    logs_dir = logs_dir or checkpoint_dir.parent
    context = dict(context or {})
    context.update({"workstream": workstream, "checkpoint_dir": checkpoint_dir, "resume": resume, "logger": logger, "mode": mode})
    qh = query_hash(provider, workstream, query)
    events_path = logs_dir / "run_events.jsonl"
    started = time.monotonic()

    def event(stage: str, message: str, *, kind: str = "progress", meta: dict[str, Any] | None = None) -> None:
        if not run_id:
            return
        write_event(
            emit_event(
                run_id,
                stage,
                message,
                event_kind=kind,
                provider=provider,
                meta_json={"workstream": workstream, "query_hash": qh, "query": query, **(meta or {})},
            ),
            events_path,
        )

    def finish(result: ProviderResult) -> ProviderResult:
        duration = time.monotonic() - started
        if result.meta.get("resume_used"):
            event("checkpoint_loaded", f"Provider {provider} checkpoint loaded", meta={"checkpoint_path": result.checkpoint_path})
        if result.checkpoint_path:
            event("checkpoint_saved", f"Provider {provider} checkpoint saved", meta={"checkpoint_path": result.checkpoint_path, "status": result.status})
        stage_by_status = {
            "completed": "provider_completed",
            "partial": "provider_partial",
            "failed": "provider_failed",
            "skipped": "provider_skipped",
            "empty": "provider_empty",
        }
        stage = stage_by_status.get(result.status, "provider_failed")
        kind = "progress" if result.status in {"completed", "empty"} else "warning"
        event(stage, f"Provider {provider} {result.status}", kind=kind, meta={"total_found": result.total_found, "total_returned": result.total_returned, "error": result.error, "duration_seconds": round(duration, 3)})
        _append_csv(
            logs_dir / "provider_performance.csv",
            {
                "run_id": run_id or "",
                "provider": provider,
                "workstream": workstream,
                "query_hash": qh,
                "query": query,
                "status": result.status,
                "total_found": result.total_found if result.total_found is not None else "",
                "rows_returned": result.total_returned,
                "duration_seconds": round(duration, 3),
                "resume_used": bool(result.meta.get("resume_used")),
                "checkpoint_path": result.checkpoint_path or "",
            },
            PERFORMANCE_FIELDS,
        )
        if result.status in {"failed", "partial", "skipped"}:
            _append_csv(
                logs_dir / "provider_failures.csv",
                {
                    "run_id": run_id or "",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "provider": provider,
                    "workstream": workstream,
                    "query_hash": qh,
                    "query": query,
                    "stage": stage,
                    "status": result.status,
                    "error_type": result.status,
                    "error_message": result.error or "",
                    "recoverable": True,
                    "fallback_used": bool(result.meta.get("fallback_used")),
                    "checkpoint_path": result.checkpoint_path or "",
                },
                FAILURE_FIELDS,
            )
        return result

    event("provider_started", f"Provider {provider} started")
    skip_error = _optional_missing(provider)
    if skip_error:
        return finish(ProviderResult(provider, query, status="skipped", error=skip_error, meta={"query_hash": qh}))

    try:
        if provider == "pubmed":
            result = PubMedClient().search(query, limit=limit, context=context)
        else:
            fn = _registry().get(provider)
            if fn is None:
                result = ProviderResult(provider, query, status="skipped", error="unsupported_provider", meta={"query_hash": qh})
            else:
                result = _coerce_result(provider, query, fn(query, limit, context))
        _stamp_retrieved_at(result, datetime.now(timezone.utc).isoformat())
        result.meta.setdefault("query_hash", qh)
        return finish(result)
    except Exception as exc:
        if logger:
            logger.warning("provider_failed provider=%s workstream=%s error=%s", provider, workstream, exc)
        return finish(ProviderResult(provider, query, status="failed", error=str(exc), meta={"query_hash": qh}))
