from __future__ import annotations

import csv
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from nutev.engine.events import emit_event, write_event
from nutev.engine.ids import make_document_id, make_run_id
from nutev.engine.job import (
    create_search_case,
    create_search_job,
    write_search_case,
    write_search_job_snapshot,
)
from nutev.engine.validators import validate_workstream
from nutev.global_watch.watch_capture import capture_watch_items
from nutev.global_watch.watch_diff import (
    load_seen_items,
    mark_new_items,
    save_seen_items,
    update_seen_items,
)
from nutev.global_watch.watch_digest import write_digest
from nutev.global_watch.watch_export import export_watch_outputs
from nutev.global_watch.watch_query_builder import build_watch_queries
from nutev.global_watch.watch_scoring import score_watch_item
from nutev.global_watch.watch_webhook import maybe_send_webhook
from nutev.search.checkpoint import query_hash
from nutev.search.pubmed import search_pubmed

# europepmc/openalex/crossref dispatch through the orchestrator registry (Phase 1
# of docs/REFACTOR_GLOBAL_WATCH_UNIFICATION.md); only pubmed is called directly.
# search_crossref is still imported to gate whether the crossref entry is added.
try:
    from nutev.search.crossref import search_crossref
except Exception:  # pragma: no cover
    search_crossref = None

try:
    from nutev.search.official_sources import manifest_sources
except Exception:  # pragma: no cover
    manifest_sources = None

def _append_provider_csv(path: Path, row: dict[str, Any], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in fields})


def _watch_provider_logs(
    logs_dir: Path,
    run_id: str,
    provider: str,
    category: str,
    query: str,
    status: str,
    rows: int,
    duration: float,
    error: str = "",
) -> None:
    qh = query_hash(provider, category, query)
    _append_provider_csv(
        logs_dir / "provider_performance.csv",
        {"run_id": run_id, "provider": provider, "workstream": category, "query_hash": qh, "query": query, "status": status, "total_found": "", "rows_returned": rows, "duration_seconds": round(duration, 3), "resume_used": False, "checkpoint_path": ""},
        ["run_id", "provider", "workstream", "query_hash", "query", "status", "total_found", "rows_returned", "duration_seconds", "resume_used", "checkpoint_path"],
    )
    if status in {"failed", "partial", "skipped"}:
        _append_provider_csv(
            logs_dir / "provider_failures.csv",
            {"run_id": run_id, "timestamp": datetime.now(timezone.utc).isoformat(), "provider": provider, "workstream": category, "query_hash": qh, "query": query, "stage": f"provider_{status}", "status": status, "error_type": status, "error_message": error, "recoverable": True, "fallback_used": False, "checkpoint_path": ""},
            ["run_id", "timestamp", "provider", "workstream", "query_hash", "query", "stage", "status", "error_type", "error_message", "recoverable", "fallback_used", "checkpoint_path"],
        )


_PROVIDER_PRIORITY = {
    "official_sources": 5,
    "pubmed": 4,
    "europepmc": 4,
    "openalex": 3,
    "crossref": 2,
    "watch_seed": 1,
}

_DOWNLOAD_STATUS_PRIORITY = {
    "pdf": 4,
    "html_snapshot": 3,
    "metadata_only": 2,
    "failed": 1,
}


def _provider_query(base: str, provider: str, since_days: int) -> str:
    date_from = (
        datetime.now(timezone.utc).date() - timedelta(days=max(since_days, 0))
    ).isoformat()
    if provider == "pubmed":
        return (
            f"({base}) AND (\"{date_from}\"[Date - Publication] : "
            f"\"3000\"[Date - Publication])"
        )
    if provider == "europepmc":
        return f"({base}) AND FIRST_PDATE:[{date_from} TO *]"
    if provider == "openalex":
        return f"{base} from_publication_date:{date_from}"
    if provider == "crossref":
        return f"{base} from-pub-date:{date_from}"
    return base


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def _provider_rank(provider: object) -> int:
    return _PROVIDER_PRIORITY.get(str(provider or "").lower(), 0)


def _download_status_rank(status: object) -> int:
    return _DOWNLOAD_STATUS_PRIORITY.get(str(status or "").lower(), 0)


def _dedupe_values(*values: object) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in (None, ""):
            continue
        if isinstance(value, (list, tuple, set)):
            candidates = value
        else:
            candidates = str(value).split("|")
        for candidate in candidates:
            text = str(candidate).strip()
            if not text:
                continue
            lowered = text.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            out.append(text)
    return out


def _canonical_workstream_values(*values: object) -> list[str]:
    canonical: list[str] = []
    seen: set[str] = set()
    for value in _dedupe_values(*values):
        normalized = validate_workstream(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            canonical.append(normalized)
    return canonical


def _prefer_longer_text(existing: object, incoming: object) -> str:
    existing_text = str(existing or "").strip()
    incoming_text = str(incoming or "").strip()
    if not existing_text:
        return incoming_text
    if len(incoming_text) > len(existing_text):
        return incoming_text
    return existing_text


def _merge_watch_rows(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    prefer_incoming_provider = _provider_rank(incoming.get("source_provider")) > _provider_rank(
        merged.get("source_provider")
    )

    for field in ("title", "abstract", "snippet"):
        merged[field] = _prefer_longer_text(merged.get(field), incoming.get(field))

    for field in ("doi", "evidence_type", "failure_reason"):
        if prefer_incoming_provider and incoming.get(field):
            merged[field] = incoming[field]
        elif not merged.get(field) and incoming.get(field):
            merged[field] = incoming[field]

    incoming_url = str(incoming.get("url") or "").strip()
    existing_url = str(merged.get("url") or "").strip()
    if incoming_url and (
        not existing_url
        or prefer_incoming_provider
        or incoming_url.lower().endswith(".pdf")
        or "pmc.ncbi.nlm.nih.gov" in incoming_url.lower()
    ):
        merged["url"] = incoming_url

    if merged.get("year") in (None, "") and incoming.get("year") not in (None, ""):
        merged["year"] = incoming["year"]

    if prefer_incoming_provider and incoming.get("source_provider"):
        merged["source_provider"] = incoming["source_provider"]

    if _download_status_rank(incoming.get("download_status")) > _download_status_rank(
        merged.get("download_status")
    ):
        merged["download_status"] = incoming.get("download_status")

    merged["relevance_score"] = max(
        float(merged.get("relevance_score") or 0),
        float(incoming.get("relevance_score") or 0),
    )
    merged["is_recent_publication"] = bool(
        merged.get("is_recent_publication") or incoming.get("is_recent_publication")
    )
    merged["fallback_used"] = bool(
        merged.get("fallback_used") or incoming.get("fallback_used")
    )
    merged["workstream_affinity"] = _canonical_workstream_values(
        merged.get("workstream_affinity"),
        incoming.get("workstream_affinity"),
    )
    merged["matched_categories"] = "|".join(
        _dedupe_values(
            merged.get("matched_categories"),
            merged.get("category"),
            incoming.get("matched_categories"),
            incoming.get("category"),
        )
    )
    merged["matched_providers"] = "|".join(
        _dedupe_values(
            merged.get("matched_providers"),
            merged.get("source_provider"),
            incoming.get("matched_providers"),
            incoming.get("source_provider"),
        )
    )
    if not merged.get("category") and incoming.get("category"):
        merged["category"] = incoming["category"]
    if not merged.get("query") and incoming.get("query"):
        merged["query"] = incoming["query"]
    if not merged.get("document_id") and incoming.get("document_id"):
        merged["document_id"] = incoming["document_id"]
    return merged


def _dedup_watch_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for row in rows:
        document_id = str(row.get("document_id") or make_document_id(row))
        normalized = dict(row)
        normalized["document_id"] = document_id
        normalized["workstream_affinity"] = _canonical_workstream_values(
            normalized.get("workstream_affinity")
        )
        normalized["matched_categories"] = "|".join(
            _dedupe_values(
                normalized.get("matched_categories"), normalized.get("category")
            )
        )
        normalized["matched_providers"] = "|".join(
            _dedupe_values(
                normalized.get("matched_providers"), normalized.get("source_provider")
            )
        )
        if document_id not in by_id:
            by_id[document_id] = normalized
            order.append(document_id)
            continue
        by_id[document_id] = _merge_watch_rows(by_id[document_id], normalized)
    return [by_id[document_id] for document_id in order]


def infer_evidence_type(title: str, abstract: str, url: str) -> str:
    text = f"{title} {abstract} {url}".lower()
    guideline_terms = [
        "guideline",
        "diretriz",
        "practice guideline",
        "clinical guidance",
        "practice advisory",
        "practice guidance",
        "guidance statement",
        "joint statement",
        "joint guideline",
        "recommendation",
        "food guide",
        "dietary guideline",
        "standards of care",
        "clinical pathway",
        "care pathway",
        "clinical decision pathway",
        "decision pathway",
        "living guideline",
        "best practice advice",
        "guideline update",
        "clinical practice update",
        "clinical practice recommendation",
        "clinical practice recommendations",
        "scientific advisory",
    ]
    consensus_terms = [
        "consensus",
        "consensus statement",
        "scientific statement",
        "position statement",
        "position paper",
        "expert consensus",
        "consensus report",
        "consensus guidance",
    ]
    review_terms = [
        "systematic review",
        "meta-analysis",
        "meta analysis",
        "umbrella review",
        "scoping review",
        "integrative review",
        "network meta-analysis",
        "network meta analysis",
        "rapid review",
        "living systematic review",
        "overview of reviews",
        "review of reviews",
    ]
    trial_terms = [
        "randomized",
        "randomised",
        "trial",
        "controlled trial",
        "pragmatic trial",
        "feasibility study",
        "pilot study",
    ]
    framework_terms = [
        "framework",
        "questionnaire",
        "instrument",
        "scale development",
        "psychometric",
        "validation study",
        "questionnaire validation",
        "survey instrument",
        "index validation",
    ]
    if _contains_any(text, guideline_terms):
        return "guideline"
    if _contains_any(text, consensus_terms):
        return "consensus"
    if _contains_any(text, review_terms):
        return "systematic_review"
    if _contains_any(text, trial_terms):
        return "trial"
    if _contains_any(text, framework_terms):
        return "framework_or_instrument"
    return "study"


def infer_workstream_affinity(
    title: str,
    category: str,
    abstract: str = "",
    snippet: str = "",
) -> list[str]:
    text = f"{title} {abstract} {snippet} {category}".lower()
    workstreams: list[str] = []

    policy_systems_terms = [
        "guideline",
        "guidelines",
        "dietary guideline",
        "food-based dietary guideline",
        "food guide",
        "nutrition guideline",
        "guidelines_consensus",
        "diet",
        "food",
        "nutrition",
    ]
    clinical_outcomes_terms = [
        "obesity",
        "cardio",
        "cardiometabolic",
        "metabolic syndrome",
        "diabetes",
        "hypertension",
        "dyslipidemia",
        "dyslipidaemia",
        "insulin resistance",
        "masld",
        "nafld",
        "mafld",
        "mash",
        "nash",
        "fatty liver",
        "steatotic liver disease",
    ]
    implementation_terms = [
        "adherence",
        "dietary adherence",
        "treatment adherence",
        "implementation",
        "implementation science",
        "implementation strategy",
        "implementation outcomes",
        "implementation fidelity",
        "implementation support",
        "implementation determinant",
        "implementation determinants",
        "implementation barrier",
        "implementation barriers",
        "implementation facilitator",
        "implementation facilitators",
        "process evaluation",
        "knowledge translation",
        "behavior",
        "behaviour",
        "behavior change",
        "behavior change technique",
        "behavioral lifestyle intervention",
        "behavioral weight loss",
        "feasibility",
        "acceptability",
        "motivational interviewing",
        "goal setting",
        "social support",
        "self-management",
        "self management",
        "self-management support",
        "shared decision making",
        "weight loss maintenance",
        "registered dietitian",
        "registered dietitian nutritionist",
        "dietitian-led",
        "dietitian led",
        "dietitian-led intervention",
        "dietitian led intervention",
        "practice facilitation",
        "health coaching",
        "nutrition counseling",
        "nutrition counselling",
        "dietary counseling",
        "dietary counselling",
        "trial",
        "randomized",
        "randomised",
        "mediterranean",
        "dash",
        "mind diet",
        "plant-based",
        "whole-food plant-based",
        "whole food plant based",
        "portfolio diet",
        "nordic diet",
        "meal replacement",
        "time-restricted eating",
        "intermittent fasting",
        "medical nutrition therapy",
        "nutrition counseling",
        "nutrition counselling",
        "registered dietitian",
        "registered dietitian nutritionist",
        "dietitian-led",
        "dietitian led",
        "lifestyle intervention",
        "lifestyle modification",
        "therapeutic lifestyle changes",
        "food is medicine",
        "food as medicine",
        "food is medicine intervention",
        "produce prescription",
        "produce prescriptions",
        "produce rx",
        "fruit and vegetable prescription",
        "healthy food prescription",
        "food prescription program",
        "produce prescription program",
        "medically tailored meal",
        "medically tailored meals",
        "medically tailored grocery",
        "medically tailored groceries",
        "teaching kitchen",
        "teaching kitchens",
        "culinary medicine",
        "masld",
        "nafld",
        "mafld",
        "mash",
        "nash",
        "fatty liver",
        "steatotic liver disease",
        "steatohepatitis",
        "nonalcoholic fatty liver disease",
        "non-alcoholic fatty liver disease",
        "nonalcoholic steatohepatitis",
        "non-alcoholic steatohepatitis",
        "metabolic dysfunction-associated fatty liver disease",
        "metabolic dysfunction associated fatty liver disease",
        "metabolic dysfunction-associated steatotic liver disease",
    ]
    framework_terms = [
        "framework",
        "questionnaire",
        "instrument",
        "scale",
        "psychometric",
        "validation",
        "competencies",
        "food literacy",
        "food and nutrition literacy",
        "nutrition literacy",
        "health literacy",
        "culinary medicine",
        "cooking skills",
        "cooking confidence",
        "food skills",
        "food agency",
        "food environment",
        "food label",
        "meal planning",
        "commensality",
        "shared meals",
        "family meals",
        "social eating",
        "eat together",
        "self-efficacy",
        "self efficacy",
        "survey instrument",
        "questionnaire validation",
        "scale development",
    ]

    if _contains_any(text, policy_systems_terms):
        workstreams.append("policy_systems")
    if _contains_any(text, clinical_outcomes_terms):
        workstreams.append("clinical_outcomes")
    if _contains_any(text, implementation_terms) or category == "implementation_behavior":
        workstreams.append("implementation")
    if _contains_any(text, framework_terms) or category in {
        "frameworks_instruments",
        "food_literacy_culinary_commensality",
    }:
        workstreams.append("framework")

    if workstreams:
        return list(dict.fromkeys(workstreams))
    return ["policy_systems"]


def normalize_watch_hit(
    raw_hit: dict,
    provider_name: str,
    category: str,
    query: str,
    since_days: int = 30,
) -> dict[str, Any]:
    title = raw_hit.get("title") or ""
    abstract = raw_hit.get("abstract") or ""
    snippet = raw_hit.get("snippet") or raw_hit.get("summary") or ""
    evidence_text = abstract or snippet
    year = raw_hit.get("year")
    try:
        year = int(year) if year is not None else None
    except Exception:
        year = None

    is_recent = bool(
        year
        and year
        >= datetime.now(timezone.utc).year - (1 if since_days <= 365 else 2)
    )
    item = {
        "title": title,
        "abstract": abstract,
        "snippet": snippet,
        "url": raw_hit.get("url") or "",
        "doi": raw_hit.get("doi") or "",
        "year": year,
        "source_provider": provider_name,
        "category": category,
        "query": query,
        "evidence_type": infer_evidence_type(
            title,
            evidence_text,
            raw_hit.get("url") or "",
        ),
        "workstream_affinity": infer_workstream_affinity(
            title,
            category,
            abstract=abstract,
            snippet=snippet,
        ),
        "matched_categories": category,
        "matched_providers": provider_name,
        "download_status": "metadata_only",
        "relevance_score": 50,
        "failure_reason": "",
        "fallback_used": False,
        "is_recent_publication": is_recent,
    }
    item["document_id"] = make_document_id(item)
    return item


def _build_provider_map() -> dict[str, Any]:
    # Phase 1 of docs/REFACTOR_GLOBAL_WATCH_UNIFICATION.md: europepmc/openalex/
    # crossref reuse the orchestrator's connector definitions (one source of truth
    # for the connector call), passing Watch's caps as the limit. Phase 0 proved
    # these make the identical call, so output is unchanged. pubmed stays on
    # search_pubmed — the orchestrator runs it via a different client (PubMedClient).
    from nutev.search.provider_orchestrator import _registry

    registry = _registry()
    provider_map: dict[str, Any] = {
        "pubmed": lambda query: search_pubmed(query, retmax=12),
        "europepmc": lambda query: registry["europepmc"](query, 12, {}),
        "openalex": lambda query: registry["openalex"](query, 10, {}),
    }
    if search_crossref and "crossref" in registry:
        provider_map["crossref"] = lambda query: registry["crossref"](query, 10, {})
    return provider_map


def watch_provider_ids() -> list[str]:
    """Provider ids the Global Watch stack can execute.

    Global Watch keeps its own query-building/dispatch stack (separate from
    ``search.provider_orchestrator``), but it must not drift onto a provider the
    central registry (``config/provider_registry.json``) never declared. This
    accessor is reconciled against the registry by ``test_watch_provider_reconcile``
    — the same single-source-of-truth guard the orchestrator has — so the two
    stacks can share connectors without their provider sets silently diverging.
    """
    return sorted(_build_provider_map().keys())


def run_watch_provider(
    provider_name: str,
    query: str,
    category: str,
    logger,
    run_id: str,
    logs_dir: Path,
    since_days: int,
) -> list[dict[str, Any]]:
    started = time.monotonic()
    write_event(
        emit_event(
            run_id,
            "provider_started",
            f"Provider {provider_name} started",
            provider=provider_name,
            meta_json={"category": category},
        ),
        logs_dir / "run_events.jsonl",
    )
    if __import__("os").environ.get("NUTEV_DISABLE_NETWORK") == "1":
        write_event(
            emit_event(
                run_id,
                "provider_skipped",
                f"Provider {provider_name} skipped because network is disabled",
                event_kind="warning",
                provider=provider_name,
                meta_json={"category": category, "reason": "network_disabled"},
            ),
            logs_dir / "run_events.jsonl",
        )
        _watch_provider_logs(logs_dir, run_id, provider_name, category, query, "skipped", 0, time.monotonic() - started, "network_disabled")
        return []
    filtered_query = _provider_query(query, provider_name, since_days)
    provider_fn = _build_provider_map().get(provider_name)
    if provider_fn is None:
        write_event(
            emit_event(
                run_id,
                "provider_disabled",
                f"Provider {provider_name} unavailable",
                event_kind="warning",
                provider=provider_name,
            ),
            logs_dir / "run_events.jsonl",
        )
        _watch_provider_logs(logs_dir, run_id, provider_name, category, query, "skipped", 0, time.monotonic() - started, "provider_unavailable")
        return []
    try:
        rows = provider_fn(filtered_query) or []
        out = [
            normalize_watch_hit(r, provider_name, category, query, since_days)
            for r in rows
        ]
        write_event(
            emit_event(
                run_id,
                "provider_completed",
                f"Provider {provider_name} completed",
                provider=provider_name,
                meta_json={"hits": len(out)},
            ),
            logs_dir / "run_events.jsonl",
        )
        _watch_provider_logs(logs_dir, run_id, provider_name, category, filtered_query, "completed" if out else "empty", len(out), time.monotonic() - started)
        return out
    except Exception as exc:
        logger.warning(
            "provider_failed provider=%s query=%s error=%s",
            provider_name,
            query,
            exc,
        )
        write_event(
            emit_event(
                run_id,
                "provider_failed",
                f"Provider {provider_name} failed",
                event_kind="warning",
                provider=provider_name,
                meta_json={"error": str(exc)},
            ),
            logs_dir / "run_events.jsonl",
        )
        _watch_provider_logs(logs_dir, run_id, provider_name, category, filtered_query if 'filtered_query' in locals() else query, "failed", 0, time.monotonic() - started, str(exc))
        return []


def run_global_watch(
    settings,
    logger,
    since_days,
    mode,
    resume,
    official_crawl,
    country_discovery,
    llm_enabled,
    capture_enabled=False,
    capture_limit=None,
    notify_webhook=False,
    webhook_url=None,
):
    run_id = make_run_id()
    logs = settings.output_dirs["07_logs"]
    case = create_search_case(
        "NutMEV Global Watch",
        ["global_watch"],
        "watch",
        ["pubmed", "europepmc", "openalex", "crossref", "official_sources"],
        since_days=since_days,
        official_crawl=official_crawl,
        country_discovery=country_discovery,
        web_enabled=settings.web_enabled,
        llm_enabled=llm_enabled,
    )
    job = create_search_job(case.case_id, run_id, [])
    write_search_case(case, logs / "search_case.json")
    write_event(
        emit_event(run_id, "global_watch_started", "Global watch started"),
        logs / "run_events.jsonl",
    )
    if llm_enabled and not os.getenv("OPENAI_API_KEY"):
        write_event(
            emit_event(
                run_id,
                "llm_disabled",
                "OPENAI_API_KEY not found",
                event_kind="warning",
            ),
            logs / "run_events.jsonl",
        )

    queries = build_watch_queries([], since_days, mode)
    providers = ["pubmed", "europepmc", "openalex", "crossref"]
    rows: list[dict[str, Any]] = []
    query_limit = 8 if mode == "quick" else 20 if mode == "thesis" else 30
    for query_item in queries[:query_limit]:
        for provider in providers:
            rows.extend(
                run_watch_provider(
                    provider,
                    query_item["query"],
                    query_item["category"],
                    logger,
                    run_id,
                    logs,
                    since_days,
                )
            )

    if official_crawl and manifest_sources is not None:
        try:
            # With --country-discovery, expand official sources to the global
            # per-country/region manifest (all countries); otherwise use the
            # base manifest only.
            from nutev.search.official_sources import load_official_manifest

            manifest = load_official_manifest(
                settings.config_root, include_countries=bool(country_discovery)
            )
            for ws in ["policy_systems", "clinical_outcomes", "implementation", "framework"]:
                for record in manifest_sources(manifest, ws):
                    rows.append(
                        normalize_watch_hit(
                            record,
                            "official_sources",
                            "guidelines_consensus",
                            "official manifest",
                            since_days,
                        )
                    )
        except Exception as exc:
            write_event(
                emit_event(
                    run_id,
                    "provider_failed",
                    "official_sources failed",
                    event_kind="warning",
                    provider="official_sources",
                    meta_json={"error": str(exc)},
                ),
                logs / "run_events.jsonl",
            )

    if not rows:
        fallback = normalize_watch_hit(
            {
                "title": "global watch fallback item",
                "url": "https://fallback.local",
                "doi": "",
            },
            "watch_seed",
            "guidelines_consensus",
            "fallback",
            since_days,
        )
        fallback["fallback_used"] = True
        fallback["failure_reason"] = "no_provider_results"
        rows = [fallback]

    rows = _dedup_watch_rows(rows)
    seen_path = (
        settings.project_root / "09_global_watch" / "watch_state" / "seen_items.json"
    )
    seen = load_seen_items(seen_path) if resume else {}
    rows = mark_new_items(rows, seen)
    for row in rows:
        row["is_new_to_system"] = bool(row.get("is_new"))
        row["novelty_score"] = 1.0 if row.get("is_new") else 0.2
        row["watch_score"] = score_watch_item(row)
    rows.sort(key=lambda item: item.get("watch_score", 0), reverse=True)
    save_seen_items(seen_path, update_seen_items(rows, seen))

    captured_items: list[dict[str, Any]] = []
    if capture_enabled:
        rows, captured_items = capture_watch_items(
            rows,
            settings,
            logger,
            run_id,
            mode,
            capture_limit=capture_limit,
        )

    run_dir = (
        settings.project_root
        / "09_global_watch"
        / "runs"
        / datetime.now(timezone.utc).date().isoformat()
    )
    new_rows = [row for row in rows if row.get("is_new")]
    host_failures = [
        {
            "host": row.get("host", ""),
            "failure_reason": row.get("failure_reason", ""),
            "http_status": row.get("http_status", ""),
        }
        for row in rows
        if row.get("failure_reason")
    ]
    provider_perf = []
    for provider in providers:
        provider_rows = [
            row for row in rows if row.get("source_provider") == provider
        ]
        provider_perf.append(
            {
                "provider": provider,
                "hits": len(provider_rows),
                "captured": sum(
                    1
                    for row in provider_rows
                    if row.get("download_status") in {"pdf", "html_snapshot"}
                ),
            }
        )
    capture_manifest = [
        {
            "document_id": row.get("document_id"),
            "download_status": row.get("download_status"),
            "capture_status": row.get("capture_status"),
            "artifact_paths": row.get("artifact_paths", {}),
        }
        for row in captured_items
    ]
    digest_md, _ = write_digest(
        rows,
        run_dir,
        settings.output_dirs["08_docs"] / "NUTEV_GLOBAL_WATCH_LATEST.md",
    )
    summary = {
        "mode": mode,
        "total_items": len(rows),
        "new_items": len(new_rows),
        "high_priority": sum(
            1 for row in rows if (row.get("watch_score") or 0) >= 80
        ),
        "pdf": sum(1 for row in rows if row.get("download_status") == "pdf"),
        "html_snapshot": sum(
            1 for row in rows if row.get("download_status") == "html_snapshot"
        ),
        "metadata_only": sum(
            1 for row in rows if row.get("download_status") == "metadata_only"
        ),
        "failed": sum(
            1 for row in rows if row.get("download_status") == "failed"
        ),
    }
    webhook_result = maybe_send_webhook(
        rows,
        digest_md,
        summary,
        settings,
        logger,
        run_id,
        enabled=notify_webhook,
        webhook_url=webhook_url,
    )
    included_ids = {row.get("document_id") for row in rows[:10]}
    for row in rows:
        row["webhook_included"] = (
            row.get("document_id") in included_ids
            and webhook_result.get("status") == "sent"
        )
    export_watch_outputs(
        rows,
        new_rows,
        settings.project_root / "09_global_watch",
        run_dir,
        provider_perf=provider_perf,
        host_failures=host_failures,
        capture_manifest=capture_manifest,
    )
    job.status = "completed"
    job.finished_at = datetime.now(timezone.utc)
    write_search_job_snapshot(
        job,
        logs / "search_job_snapshot.json",
        {"mode": mode, "since_days": since_days, "resume": resume, "providers": providers},
    )
    write_event(
        emit_event(
            run_id,
            "global_watch_completed",
            "Global watch completed",
        ),
        logs / "run_events.jsonl",
    )
    return {"rows": len(rows), "new_items": len(new_rows)}