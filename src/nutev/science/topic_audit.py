"""Active topic/competency audit layer for the NutEV evidence bank.

The engine maps versioned topic/competency definitions onto relational CORE records,
identifies coverage gaps, and materializes an auditable active-search plan. It may
execute PubMed searches because that connector exposes explicit completed/partial/
failed/skipped status. Other providers remain planned until their connector exposes
an equally explicit status contract; an opaque empty list must never be interpreted
as a scientific zero.

Topic matches, audit priorities, and search results are machine aids. They are not
eligibility decisions, evidence quality, certainty, clinical recommendations, or
PRISMA events.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping
from uuid import uuid4

from nutev.audit_guardrails import sha256_file
from nutev.search.pubmed import PubMedClient


class TopicAuditError(RuntimeError):
    """Raised when topic/competency audit inputs are invalid or unverifiable."""


_TOPIC_KINDS = {"topic", "competency", "context", "implementation"}
_PROFILE_STATUSES = {"PREFREEZE", "CANONICAL"}
_EXECUTION_PROVIDERS = (
    "pubmed",
    "europepmc",
    "openalex",
    "crossref",
    "doaj",
    "semantic_scholar",
    "lilacs_bvs",
    "scielo",
    "scopus",
    "wos",
)


@dataclass(frozen=True, slots=True)
class TopicDefinition:
    id: str
    label: str
    kind: str
    terms: tuple[str, ...]
    anchor_terms: tuple[str, ...] = ()
    qualifier_terms: tuple[str, ...] = ()
    query_mode: str = "anchor_and_terms"
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class TopicAssignment:
    id: str
    document_id: str
    topic_id: str
    topic_kind: str
    matched_terms: tuple[str, ...]
    matched_sources: tuple[str, ...]
    lexical_match_score: float
    status: str = "machine_candidate"


@dataclass(frozen=True, slots=True)
class TopicAuditResult:
    topic_id: str
    topic_kind: str
    document_count: int
    provider_count: int
    providers: tuple[str, ...]
    full_text_count: int
    semantic_count: int
    relational_count: int
    latest_year: int | None
    flags: tuple[str, ...]
    active_search_priority: str
    active_search_required: bool
    status: str = "machine_audit"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise TopicAuditError(f"missing JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TopicAuditError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise TopicAuditError(f"expected JSON object at {path}")
    return value


def _read_jsonl(path: Path, *, label: str, allow_empty: bool = False) -> list[dict[str, Any]]:
    if not path.is_file():
        raise TopicAuditError(f"missing {label} JSONL: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise TopicAuditError(f"invalid JSONL at {path}:{line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise TopicAuditError(f"non-object JSONL row at {path}:{line_number}")
            rows.append(value)
    if not rows and not allow_empty:
        raise TopicAuditError(f"{label} JSONL is empty: {path}")
    return rows


def _atomic_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return sha256_file(path)


def _write_json(path: Path, value: Any) -> str:
    return _atomic_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
    )


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> str:
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n"
        for row in rows
    )
    return _atomic_text(path, payload)


def _string_tuple(value: Any, *, field: str) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if not isinstance(value, list):
        raise TopicAuditError(f"profile field {field} must be a list")
    items = tuple(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))
    return items


def load_topic_profile(path: Path) -> dict[str, Any]:
    profile = _read_json(path)
    if int(profile.get("schema_version") or 0) != 1:
        raise TopicAuditError("unsupported topic profile schema version")
    if profile.get("profile_kind") != "NUTEV_TOPIC_COMPETENCY_REGISTRY":
        raise TopicAuditError("profile_kind must be NUTEV_TOPIC_COMPETENCY_REGISTRY")
    profile_id = str(profile.get("profile_id") or "").strip()
    version = str(profile.get("version") or "").strip()
    status = str(profile.get("status") or "").strip().upper()
    if not profile_id or not version:
        raise TopicAuditError("topic profile requires profile_id and version")
    if status not in _PROFILE_STATUSES:
        raise TopicAuditError(f"unsupported topic profile status: {status}")
    formal_gate = profile.get("formal_gate") or {}
    if not isinstance(formal_gate, Mapping):
        raise TopicAuditError("formal_gate must be an object")
    if status == "CANONICAL" and not bool(formal_gate.get("authorized")):
        raise TopicAuditError("CANONICAL profile requires explicit formal_gate.authorized=true")
    raw_topics = profile.get("topics")
    if not isinstance(raw_topics, list) or not raw_topics:
        raise TopicAuditError("topic profile requires at least one topic definition")

    seen: set[str] = set()
    topics: list[TopicDefinition] = []
    for raw in raw_topics:
        if not isinstance(raw, Mapping):
            raise TopicAuditError("each topic definition must be an object")
        topic_id = str(raw.get("id") or "").strip()
        label = str(raw.get("label") or "").strip()
        kind = str(raw.get("kind") or "topic").strip().lower()
        if not topic_id or not label:
            raise TopicAuditError("topic definition requires id and label")
        if topic_id in seen:
            raise TopicAuditError(f"duplicate topic id: {topic_id}")
        seen.add(topic_id)
        if kind not in _TOPIC_KINDS:
            raise TopicAuditError(f"unsupported topic kind for {topic_id}: {kind}")
        terms = _string_tuple(raw.get("terms"), field=f"topics.{topic_id}.terms")
        if not terms:
            raise TopicAuditError(f"topic {topic_id} requires terms")
        topics.append(
            TopicDefinition(
                id=topic_id,
                label=label,
                kind=kind,
                terms=terms,
                anchor_terms=_string_tuple(
                    raw.get("anchor_terms"), field=f"topics.{topic_id}.anchor_terms"
                ),
                qualifier_terms=_string_tuple(
                    raw.get("qualifier_terms"), field=f"topics.{topic_id}.qualifier_terms"
                ),
                query_mode=str(raw.get("query_mode") or "anchor_and_terms"),
                enabled=bool(raw.get("enabled", True)),
            )
        )
    profile["_topics"] = topics
    return profile


def _verify_relational_input(records_path: Path, manifest_path: Path) -> dict[str, str]:
    manifest = _read_json(manifest_path)
    if (
        manifest.get("relations_type") != "NUTEV_CORE_RELATIONAL_MAPPING"
        or manifest.get("status") != "PASS"
    ):
        raise TopicAuditError("relations manifest is not a passing NutEV relational manifest")
    expected = str(
        ((((manifest.get("outputs") or {}).get("relational_core_records") or {}).get("sha256")) or "")
    ).strip().lower()
    if not expected:
        raise TopicAuditError("relations manifest is missing relational_core_records SHA-256")
    actual = sha256_file(records_path)
    if actual != expected:
        raise TopicAuditError(
            f"relational CORE records SHA-256 mismatch: expected {expected}, got {actual}"
        )
    return {
        "relational_records": actual,
        "relations_manifest": sha256_file(manifest_path),
    }


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def _contains_term(text: str, term: str) -> bool:
    needle = _norm(term).replace("*", "")
    if not needle:
        return False
    haystack = _norm(text)
    if " " in needle or "-" in needle:
        return needle in haystack
    return bool(re.search(rf"\b{re.escape(needle)}\w*\b", haystack))


def _record_text_sources(record: Mapping[str, Any]) -> dict[str, str]:
    sources: dict[str, str] = {}
    identity = record.get("identity") or {}
    bibliography = record.get("bibliography") or {}
    if isinstance(identity, Mapping):
        sources["title"] = str(identity.get("title") or "")
    if isinstance(bibliography, Mapping):
        sources["abstract"] = str(bibliography.get("abstract") or "")
        keywords = bibliography.get("keywords") or []
        if isinstance(keywords, list):
            sources["keywords"] = " ; ".join(str(item) for item in keywords)
        else:
            sources["keywords"] = str(keywords or "")

    semantic = record.get("semantic") or {}
    if isinstance(semantic, Mapping):
        facts = semantic.get("facts") or []
        if isinstance(facts, list):
            sources["semantic_facts"] = "\n".join(
                str(item.get("value") or "")
                for item in facts
                if isinstance(item, Mapping)
            )

    relational = record.get("relational") or {}
    if isinstance(relational, Mapping):
        entities = relational.get("entities") or []
        if isinstance(entities, list):
            sources["relational_entities"] = "\n".join(
                str(item.get("label") or "")
                for item in entities
                if isinstance(item, Mapping)
            )
    return sources


def assign_topics(
    records: Iterable[Mapping[str, Any]],
    topics: Iterable[TopicDefinition],
) -> tuple[TopicAssignment, ...]:
    assignments: list[TopicAssignment] = []
    for record in records:
        document_id = str(record.get("document_id") or "").strip()
        if not document_id:
            raise TopicAuditError("relational CORE record missing document_id")
        sources = _record_text_sources(record)
        for topic in topics:
            if not topic.enabled:
                continue
            matched_terms: list[str] = []
            matched_sources: set[str] = set()
            for term in topic.terms:
                for source_name, text in sources.items():
                    if text and _contains_term(text, term):
                        matched_terms.append(term)
                        matched_sources.add(source_name)
                        break
            unique_terms = tuple(dict.fromkeys(matched_terms))
            if not unique_terms:
                continue
            score = round(min(1.0, len(unique_terms) / max(1, min(5, len(topic.terms)))), 2)
            digest = sha256(
                f"{document_id}|{topic.id}|{'|'.join(unique_terms)}".encode("utf-8")
            ).hexdigest()[:18]
            assignments.append(
                TopicAssignment(
                    id=f"topic-assignment:{digest}",
                    document_id=document_id,
                    topic_id=topic.id,
                    topic_kind=topic.kind,
                    matched_terms=unique_terms,
                    matched_sources=tuple(sorted(matched_sources)),
                    lexical_match_score=score,
                )
            )
    return tuple(sorted(assignments, key=lambda item: (item.topic_id, item.document_id)))


def _provider(record: Mapping[str, Any]) -> str:
    identity = record.get("identity") or {}
    provenance = record.get("provenance") or {}
    if isinstance(identity, Mapping):
        value = identity.get("source_provider") or identity.get("provider")
        if value:
            return str(value).strip().lower()
    if isinstance(provenance, Mapping):
        value = provenance.get("source_provider") or provenance.get("provider")
        if value:
            return str(value).strip().lower()
    return "unknown"


def _year(record: Mapping[str, Any]) -> int | None:
    identity = record.get("identity") or {}
    bibliography = record.get("bibliography") or {}
    for container in (identity, bibliography):
        if not isinstance(container, Mapping):
            continue
        value = container.get("year")
        if value is None:
            continue
        match = re.search(r"\b(19|20)\d{2}\b", str(value))
        if match:
            return int(match.group(0))
    return None


def audit_topics(
    records: Iterable[Mapping[str, Any]],
    topics: Iterable[TopicDefinition],
    assignments: Iterable[TopicAssignment],
    *,
    min_documents: int = 3,
    min_providers: int = 2,
    freshness_years: int = 5,
) -> tuple[TopicAuditResult, ...]:
    records_by_id = {
        str(record.get("document_id") or ""): record for record in records
    }
    by_topic: dict[str, list[TopicAssignment]] = defaultdict(list)
    for item in assignments:
        by_topic[item.topic_id].append(item)
    current_year = datetime.now(timezone.utc).year
    audits: list[TopicAuditResult] = []
    for topic in topics:
        if not topic.enabled:
            continue
        topic_assignments = by_topic.get(topic.id, [])
        topic_records = [
            records_by_id[item.document_id]
            for item in topic_assignments
            if item.document_id in records_by_id
        ]
        providers = tuple(sorted({_provider(record) for record in topic_records}))
        years = [year for record in topic_records if (year := _year(record)) is not None]
        full_text_count = 0
        semantic_count = 0
        relational_count = 0
        for record in topic_records:
            acquisition = record.get("acquisition") or {}
            if isinstance(acquisition, Mapping) and str(
                acquisition.get("full_text_status") or ""
            ).lower() in {"retrieved", "full_text", "available"}:
                full_text_count += 1
            semantic = record.get("semantic") or {}
            if isinstance(semantic, Mapping) and semantic.get("facts"):
                semantic_count += 1
            relational = record.get("relational") or {}
            if isinstance(relational, Mapping) and relational.get("entities"):
                relational_count += 1

        flags: list[str] = []
        if not topic_records:
            flags.append("no_documents")
        elif len(topic_records) < min_documents:
            flags.append("low_document_count")
        if topic_records and len(providers) < min_providers:
            flags.append("low_provider_diversity")
        latest_year = max(years) if years else None
        if topic_records and (latest_year is None or latest_year < current_year - freshness_years):
            flags.append("stale_or_unknown_recency")
        if topic_records and full_text_count == 0:
            flags.append("no_full_text")
        if topic_records and semantic_count < len(topic_records):
            flags.append("semantic_incomplete")
        if topic_records and relational_count < len(topic_records):
            flags.append("relational_incomplete")

        if "no_documents" in flags:
            priority = "P1_HIGH"
        elif {"low_document_count", "stale_or_unknown_recency"} & set(flags):
            priority = "P2_MEDIUM"
        elif flags:
            priority = "P3_LOW"
        else:
            priority = "P4_MONITOR"
        audits.append(
            TopicAuditResult(
                topic_id=topic.id,
                topic_kind=topic.kind,
                document_count=len(topic_records),
                provider_count=len(providers),
                providers=providers,
                full_text_count=full_text_count,
                semantic_count=semantic_count,
                relational_count=relational_count,
                latest_year=latest_year,
                flags=tuple(flags),
                active_search_priority=priority,
                active_search_required=bool(flags),
            )
        )
    return tuple(audits)


def _quote_term(term: str, *, pubmed: bool) -> str:
    raw = term.strip().replace("*", "")
    quoted = f'"{raw}"' if " " in raw or "-" in raw else raw
    return f"{quoted}[Title/Abstract]" if pubmed else quoted


def _or_group(terms: Iterable[str], *, pubmed: bool) -> str:
    values = [_quote_term(term, pubmed=pubmed) for term in terms if term.strip()]
    return "(" + " OR ".join(values) + ")" if values else ""


def compile_topic_query(topic: TopicDefinition, *, provider: str) -> str:
    is_pubmed = provider == "pubmed"
    terms = _or_group(topic.terms, pubmed=is_pubmed)
    anchors = _or_group(topic.anchor_terms, pubmed=is_pubmed)
    qualifiers = _or_group(topic.qualifier_terms, pubmed=is_pubmed)
    parts: list[str] = []
    if topic.query_mode in {"anchor_and_terms", "anchor_terms_qualifiers"} and anchors:
        parts.append(anchors)
    parts.append(terms)
    if topic.query_mode == "anchor_terms_qualifiers" and qualifiers:
        parts.append(qualifiers)
    return " AND ".join(part for part in parts if part)


def build_active_search_plan(
    topics: Iterable[TopicDefinition],
    audits: Iterable[TopicAuditResult],
    *,
    profile_id: str,
    limit: int,
) -> dict[str, Any]:
    audits_by_topic = {audit.topic_id: audit for audit in audits}
    searches: list[dict[str, Any]] = []
    for topic in topics:
        if not topic.enabled:
            continue
        audit = audits_by_topic[topic.id]
        for provider in _EXECUTION_PROVIDERS:
            if provider == "pubmed":
                execution = "EXECUTABLE_STATUS_AWARE"
            elif provider in {"scopus", "wos"}:
                execution = "MANUAL_LICENSED"
            else:
                execution = "PLAN_ONLY_STATUS_ADAPTER_REQUIRED"
            searches.append(
                {
                    "profile_id": profile_id,
                    "topic_id": topic.id,
                    "topic_kind": topic.kind,
                    "priority": audit.active_search_priority,
                    "reason_flags": list(audit.flags),
                    "provider": provider,
                    "execution": execution,
                    "limit": limit,
                    "query": compile_topic_query(topic, provider=provider),
                    "auto_ingest": False,
                    "feeds_prisma": False,
                }
            )
    return {
        "schema_version": 1,
        "plan_type": "NUTEV_ACTIVE_TOPIC_SEARCH_PLAN",
        "profile_id": profile_id,
        "created_at": _now(),
        "searches": searches,
        "guardrail": (
            "The plan is gap-driven discovery. Results do not enter the CORE bank or PRISMA "
            "until they pass the normal normalization, traceability, deduplication and audit pipeline."
        ),
    }


def _run_pubmed_searches(
    plan: Mapping[str, Any],
    *,
    checkpoint_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    runs: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    client = PubMedClient()
    for item in plan.get("searches") or []:
        if not isinstance(item, Mapping) or item.get("provider") != "pubmed":
            continue
        topic_id = str(item.get("topic_id") or "")
        query = str(item.get("query") or "")
        limit = int(item.get("limit") or 20)
        provider_result = client.search(
            query,
            limit=limit,
            context={
                "workstream": f"topic-audit-{topic_id}",
                "checkpoint_dir": checkpoint_dir,
                "resume": True,
            },
        )
        runs.append(
            {
                "topic_id": topic_id,
                "provider": provider_result.provider,
                "query": provider_result.query,
                "status": provider_result.status,
                "error": provider_result.error,
                "total_found": provider_result.total_found,
                "total_returned": provider_result.total_returned,
                "checkpoint_path": provider_result.checkpoint_path,
                "feeds_prisma": False,
                "auto_ingest": False,
            }
        )
        for row in provider_result.rows:
            result = dict(row)
            result["topic_id"] = topic_id
            result["topic_search_status"] = "discovery_candidate"
            result["feeds_prisma"] = False
            result["auto_ingest"] = False
            results.append(result)
    for item in plan.get("searches") or []:
        if not isinstance(item, Mapping) or item.get("provider") == "pubmed":
            continue
        runs.append(
            {
                "topic_id": item.get("topic_id"),
                "provider": item.get("provider"),
                "query": item.get("query"),
                "status": "planned_not_executed",
                "error": "explicit_provider_status_adapter_required",
                "total_found": None,
                "total_returned": 0,
                "feeds_prisma": False,
                "auto_ingest": False,
            }
        )
    return runs, results


def run_topic_competency_audit(
    relational_records_jsonl: Path,
    relations_manifest: Path,
    topic_profile: Path,
    output_dir: Path,
    *,
    execute_search: bool = False,
    limit: int = 20,
) -> dict[str, Any]:
    """Audit topic/competency coverage and optionally execute status-aware PubMed search."""

    if limit < 1:
        raise TopicAuditError("active-search limit must be positive")
    source_shas = _verify_relational_input(relational_records_jsonl, relations_manifest)
    profile = load_topic_profile(topic_profile)
    topics = tuple(profile["_topics"])
    records = _read_jsonl(relational_records_jsonl, label="relational CORE records")
    assignments = assign_topics(records, topics)

    audit_cfg = profile.get("audit") or {}
    if not isinstance(audit_cfg, Mapping):
        raise TopicAuditError("profile audit must be an object")
    audits = audit_topics(
        records,
        topics,
        assignments,
        min_documents=int(audit_cfg.get("min_documents") or 3),
        min_providers=int(audit_cfg.get("min_providers") or 2),
        freshness_years=int(audit_cfg.get("freshness_years") or 5),
    )
    plan = build_active_search_plan(
        topics,
        audits,
        profile_id=str(profile["profile_id"]),
        limit=limit,
    )

    runs: list[dict[str, Any]] = []
    active_results: list[dict[str, Any]] = []
    if execute_search:
        runs, active_results = _run_pubmed_searches(
            plan,
            checkpoint_dir=output_dir / "checkpoints",
        )
    else:
        for item in plan["searches"]:
            runs.append(
                {
                    "topic_id": item["topic_id"],
                    "provider": item["provider"],
                    "query": item["query"],
                    "status": "planned_not_executed",
                    "error": None,
                    "total_found": None,
                    "total_returned": 0,
                    "feeds_prisma": False,
                    "auto_ingest": False,
                }
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    assignments_path = output_dir / "topic_assignments.jsonl"
    audits_path = output_dir / "topic_audits.jsonl"
    plan_path = output_dir / "active_search_plan.json"
    runs_path = output_dir / "active_search_runs.jsonl"
    results_path = output_dir / "active_search_results.jsonl"
    manifest_path = output_dir / "TOPIC_AUDIT_MANIFEST.json"

    assignments_sha = _write_jsonl(assignments_path, (asdict(item) for item in assignments))
    audits_sha = _write_jsonl(audits_path, (asdict(item) for item in audits))
    plan_sha = _write_json(plan_path, plan)
    runs_sha = _write_jsonl(runs_path, runs)
    results_sha = _write_jsonl(results_path, active_results)

    kind_counts = Counter(item.topic_kind for item in assignments)
    priority_counts = Counter(item.active_search_priority for item in audits)
    profile_status = str(profile.get("status") or "").upper()
    manifest = {
        "schema_version": 1,
        "audit_type": "NUTEV_TOPIC_COMPETENCY_AUDIT",
        "status": "PASS",
        "created_at": _now(),
        "profile": {
            "path": str(topic_profile),
            "profile_id": profile.get("profile_id"),
            "version": profile.get("version"),
            "status": profile_status,
            "sha256": sha256_file(topic_profile),
        },
        "source": {
            "relational_records": str(relational_records_jsonl),
            "relations_manifest": str(relations_manifest),
            "source_sha256": source_shas,
        },
        "counts": {
            "records": len(records),
            "topics": len(topics),
            "assignments": len(assignments),
            "assignment_kind_counts": dict(sorted(kind_counts.items())),
            "audit_priority_counts": dict(sorted(priority_counts.items())),
            "active_search_runs": len(runs),
            "active_search_results": len(active_results),
        },
        "outputs": {
            "topic_assignments": {"path": str(assignments_path), "sha256": assignments_sha},
            "topic_audits": {"path": str(audits_path), "sha256": audits_sha},
            "active_search_plan": {"path": str(plan_path), "sha256": plan_sha},
            "active_search_runs": {"path": str(runs_path), "sha256": runs_sha},
            "active_search_results": {"path": str(results_path), "sha256": results_sha},
        },
        "assertions": [
            {"name": "relational_input_hash_verified", "status": "PASS"},
            {"name": "profile_is_versioned", "status": "PASS"},
            {"name": "topic_matches_are_machine_candidates", "status": "PASS"},
            {"name": "opaque_provider_empty_not_treated_as_zero", "status": "PASS"},
            {"name": "active_search_does_not_auto_ingest", "status": "PASS"},
            {"name": "active_search_does_not_feed_prisma", "status": "PASS"},
            {"name": "prisma_not_required", "status": "PASS"},
        ],
        "guardrail": (
            "Topic and competency assignments are lexical/structured machine candidates. Audit priority "
            "measures coverage gaps, not scientific quality. Active-search results remain discovery candidates "
            "until they re-enter the normal NutEV traceability pipeline."
        ),
    }
    manifest_sha = _write_json(manifest_path, manifest)
    return {
        "mode": "NUTEV_TOPIC_COMPETENCY_AUDIT",
        "status": "COMPLETE",
        "profile_status": profile_status,
        "records": len(records),
        "topics": len(topics),
        "assignments": len(assignments),
        "active_search_executed": execute_search,
        "active_search_results": len(active_results),
        "prisma_required": False,
        "outputs": {
            "assignments": str(assignments_path),
            "audits": str(audits_path),
            "search_plan": str(plan_path),
            "search_runs": str(runs_path),
            "search_results": str(results_path),
            "manifest": str(manifest_path),
        },
        "output_sha256": {
            "assignments": assignments_sha,
            "audits": audits_sha,
            "search_plan": plan_sha,
            "search_runs": runs_sha,
            "search_results": results_sha,
            "manifest": manifest_sha,
        },
    }
