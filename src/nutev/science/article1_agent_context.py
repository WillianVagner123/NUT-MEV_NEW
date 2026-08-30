"""Build a verified, rank-blind context bundle for Article 1 agents.

The bundle is navigation/context infrastructure only. It never emits eligibility,
inclusion/exclusion, PRISMA events, quality, risk of bias, certainty, causal
interpretation or recommendations, and it never copies protected full text.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Mapping
from uuid import uuid4

from nutev.audit_guardrails import sha256_file


AGENT_CONTEXT_VERSION = "nutev_article1_agent_context_v1"
DEFAULT_SEARCH_MASTER = Path("config/nutev/article1_search_master_v1.json")
_FORBIDDEN_SUMMARY_FIELDS = {
    "reference_rank",
    "reference_score",
    "reference_tier",
    "machine_relevance_score",
    "machine_relevance_band",
}


class Article1AgentContextError(RuntimeError):
    """Raised when the agent context cannot be proven from verified inputs."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise Article1AgentContextError(f"missing JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Article1AgentContextError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise Article1AgentContextError(f"expected JSON object at {path}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise Article1AgentContextError(f"missing JSONL file: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise Article1AgentContextError(
                    f"invalid JSONL at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise Article1AgentContextError(
                    f"non-object JSONL record at {path}:{line_number}"
                )
            rows.append(value)
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


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> str:
    return _atomic_text(
        path,
        "".join(
            json.dumps(dict(row), ensure_ascii=False, sort_keys=True, default=str) + "\n"
            for row in rows
        ),
    )


def _resolve_output_path(root: Path, raw: object, *, fallback_root: Path) -> Path:
    path = Path(str(raw or ""))
    if path.is_absolute():
        return path
    candidate = fallback_root / path.name
    if candidate.is_file():
        return candidate
    return (root.parent / path).resolve()


def _verified_workbench(output_root: Path) -> tuple[dict[str, Any], Path, str]:
    workbench_root = output_root / "scientific" / "workbench"
    manifest_path = workbench_root / "WORKBENCH_MANIFEST.json"
    manifest = _read_json(manifest_path)
    if manifest.get("workbench_type") != "NUTEV_ARTICLE_WORKBENCH_V1":
        raise Article1AgentContextError("unexpected Workbench manifest type")
    if manifest.get("status") != "PASS":
        raise Article1AgentContextError("Workbench manifest is not PASS")
    output = (manifest.get("outputs") or {}).get("database") or {}
    database = _resolve_output_path(
        output_root,
        output.get("path"),
        fallback_root=workbench_root,
    )
    expected = str(output.get("sha256") or "").strip().lower()
    if not database.is_file() or not expected:
        raise Article1AgentContextError("active Workbench database/hash missing")
    actual = sha256_file(database)
    if actual != expected:
        raise Article1AgentContextError(
            f"Workbench database SHA-256 mismatch: expected {expected}, got {actual}"
        )
    return manifest, database, actual


def _verified_routes(
    output_root: Path,
    search_id: str,
) -> tuple[dict[str, Any], dict[str, list[str]], Path, str]:
    route_root = output_root / "scientific" / "review_routes" / search_id / "article1"
    manifest_path = route_root / "ROUTE_QUEUE_MANIFEST.json"
    manifest = _read_json(manifest_path)
    if manifest.get("queue_type") != "NUTEV_ARTICLE1_ROUTE_REVIEW_QUEUE":
        raise Article1AgentContextError("unexpected Article 1 route manifest type")
    if manifest.get("status") != "PASS":
        raise Article1AgentContextError("Article 1 route manifest is not PASS")

    membership: dict[str, list[str]] = defaultdict(list)
    outputs = manifest.get("outputs") or {}
    for route in ("B-NORM", "C-STRUCT"):
        item = outputs.get(route) or {}
        path = _resolve_output_path(output_root, item.get("path"), fallback_root=route_root)
        expected = str(item.get("sha256") or "").strip().lower()
        if not path.is_file() or not expected:
            raise Article1AgentContextError(f"missing route file/hash for {route}")
        actual = sha256_file(path)
        if actual != expected:
            raise Article1AgentContextError(
                f"{route} SHA-256 mismatch: expected {expected}, got {actual}"
            )
        for row in _read_jsonl(path):
            leaked = _FORBIDDEN_SUMMARY_FIELDS & set(row)
            if leaked:
                raise Article1AgentContextError(
                    f"rank-blind route {route} exposes forbidden fields: {sorted(leaked)}"
                )
            document_id = str(row.get("document_id") or "").strip()
            if document_id and route not in membership[document_id]:
                membership[document_id].append(route)
    return manifest, membership, manifest_path, sha256_file(manifest_path)


def _optional_manifest(path: Path) -> dict[str, Any] | None:
    return _read_json(path) if path.is_file() else None


def _parse_review_profile(raw: object) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _profile_summary(profile: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "profile_version": profile.get("profile_version"),
        "primary_document_class": profile.get("primary_document_class"),
        "document_classification_basis": profile.get("document_classification_basis"),
        "document_class_confidence": profile.get("document_class_confidence"),
        "document_class_matches": profile.get("document_class_matches") or {},
        "document_class_warnings": profile.get("document_class_warnings") or [],
        "operational_domains": profile.get("operational_domains") or [],
        "operational_domain_matches": profile.get("operational_domain_matches") or {},
    }


def _article_summaries(
    database: Path,
    membership: Mapping[str, list[str]],
    *,
    expected_tier_records: int | None,
) -> list[dict[str, Any]]:
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(article_cards)").fetchall()
        }
        required = {
            "document_id",
            "title",
            "year",
            "doi",
            "pmid",
            "source_provider",
            "document_class",
            "full_text_status",
            "reference_stub",
            "reference_tier",
            "review_profile_json",
        }
        missing = sorted(required - columns)
        if missing:
            raise Article1AgentContextError(
                "Workbench lacks required Article 1 context columns: " + ", ".join(missing)
            )

        article_rows = connection.execute(
            """
            SELECT document_id, title, year, doi, pmid, source_provider,
                   document_class, full_text_status, reference_stub, review_profile_json
            FROM article_cards
            WHERE reference_tier = 'BANK_A_PROCESSING_PRIORITY'
            ORDER BY document_id ASC
            """
        ).fetchall()
        excerpt_counts = {
            str(row[0]): int(row[1])
            for row in connection.execute(
                "SELECT document_id, COUNT(*) FROM evidence_excerpts GROUP BY document_id"
            ).fetchall()
        }
        bundle_counts = {
            str(row[0]): int(row[1])
            for row in connection.execute(
                "SELECT document_id, COUNT(*) FROM result_bundles GROUP BY document_id"
            ).fetchall()
        }

    if expected_tier_records is not None and len(article_rows) != expected_tier_records:
        raise Article1AgentContextError(
            f"Tier A summary coverage mismatch: expected {expected_tier_records}, got {len(article_rows)}"
        )

    summaries: list[dict[str, Any]] = []
    for row in article_rows:
        document_id = str(row["document_id"])
        profile = _profile_summary(_parse_review_profile(row["review_profile_json"]))
        summary = {
            "context_version": AGENT_CONTEXT_VERSION,
            "document_id": document_id,
            "title": row["title"],
            "year": row["year"],
            "doi": row["doi"],
            "pmid": row["pmid"],
            "source_provider": row["source_provider"],
            "document_class": row["document_class"],
            "full_text_status": row["full_text_status"],
            "reference_stub": row["reference_stub"],
            "routes": sorted(membership.get(document_id, [])),
            "review_profile": profile,
            "evidence_excerpt_count": excerpt_counts.get(document_id, 0),
            "result_bundle_count": bundle_counts.get(document_id, 0),
            "guardrail": (
                "Rank-blind agent navigation summary only; not eligibility, inclusion/exclusion, "
                "quality, risk of bias, certainty, recommendation, or PRISMA."
            ),
        }
        leaked = _FORBIDDEN_SUMMARY_FIELDS & set(summary)
        if leaked:
            raise Article1AgentContextError(
                f"generated agent summary exposes forbidden fields: {sorted(leaked)}"
            )
        summaries.append(summary)
    return summaries


def _search_state(
    *,
    master: Mapping[str, Any],
    search_id: str,
    workbench_manifest: Mapping[str, Any],
    workbench_sha: str,
    route_manifest: Mapping[str, Any],
    route_manifest_sha: str,
    deepening_manifest: Mapping[str, Any] | None,
    review_manifest: Mapping[str, Any] | None,
    vocabulary_audit: Mapping[str, Any] | None,
    article_count: int,
) -> dict[str, Any]:
    return {
        "context_version": AGENT_CONTEXT_VERSION,
        "created_at": _now(),
        "search_id": search_id,
        "question": master.get("question"),
        "master_status": master.get("status"),
        "formal_search": master.get("formal_search") or {},
        "runtime": {
            "workbench": {
                "status": workbench_manifest.get("status"),
                "counts": workbench_manifest.get("counts") or {},
                "database_sha256": workbench_sha,
            },
            "deepening": {
                "present": deepening_manifest is not None,
                "status": (deepening_manifest or {}).get("status"),
                "counts": (deepening_manifest or {}).get("counts") or {},
                "retrieval_status_counts": (deepening_manifest or {}).get("retrieval_status_counts") or {},
                "extraction_method_counts": (deepening_manifest or {}).get("extraction_method_counts") or {},
            },
            "review_profiles": {
                "present": review_manifest is not None,
                "status": (review_manifest or {}).get("status"),
                "profile_version": (review_manifest or {}).get("profile_version"),
                "counts": (review_manifest or {}).get("counts") or {},
            },
            "article1_routes": {
                "status": route_manifest.get("status"),
                "queue_version": route_manifest.get("queue_version"),
                "counts": route_manifest.get("counts") or {},
                "manifest_sha256": route_manifest_sha,
            },
            "vocabulary_audit": {
                "present": vocabulary_audit is not None,
                "status": (vocabulary_audit or {}).get("status"),
                "audit_version": (vocabulary_audit or {}).get("audit_version"),
            },
            "agent_article_summaries": article_count,
        },
        "guardrails": {
            "discovery_is_not_formal_prisma_search": True,
            "agent_summaries_are_rank_blind": True,
            "agent_summaries_contain_full_text": False,
            "agent_summaries_are_not_screening_decisions": True,
            "formal_gate_is_not_changed_by_context_build": True,
        },
    }


def _summary_markdown(state: Mapping[str, Any]) -> str:
    runtime = state.get("runtime") or {}
    routes = (runtime.get("article1_routes") or {}).get("counts") or {}
    formal = state.get("formal_search") or {}
    return "\n".join(
        [
            "# Article 1 — live agent summary",
            "",
            f"Search id: `{state.get('search_id')}`",
            f"Master status: `{state.get('master_status')}`",
            "",
            "## Formal-search gate",
            "",
            f"- PRESS: `{formal.get('press_status')}`",
            f"- GF-10 authorized: `{formal.get('gf10_authorized')}`",
            f"- query freeze complete: `{formal.get('query_freeze_complete')}`",
            f"- formal provider search executed: `{formal.get('formal_provider_search_executed')}`",
            f"- PRISMA search event emitted: `{formal.get('prisma_search_event_emitted')}`",
            "",
            "## Live context",
            "",
            f"- agent article summaries: {runtime.get('agent_article_summaries')}",
            f"- B-NORM: {routes.get('B-NORM')}",
            f"- C-STRUCT: {routes.get('C-STRUCT')}",
            f"- route union: {routes.get('route_union_documents')}",
            f"- route overlap: {routes.get('route_overlap_documents')}",
            f"- unrouted: {routes.get('unrouted_documents')}",
            "",
            "## Interpretation boundary",
            "",
            "This bundle is navigation/context only. Discovery, Bank tier, route membership, retrieval status and machine profiles are not scientific inclusion, evidence quality or PRISMA decisions.",
            "",
            "Use `ARTICLE_SUMMARIES.jsonl` for rank-blind article-level context and the Workbench detail API for deeper inspection of a selected document.",
            "",
        ]
    )


def build_article1_agent_context(
    search_id: str | None = None,
    *,
    output_root: Path = Path("project_output_reference"),
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Materialize the verified Article 1 context bundle."""
    output_root = output_root.resolve()
    repo_root = (repo_root or Path(__file__).resolve().parents[3]).resolve()
    master_path = repo_root / DEFAULT_SEARCH_MASTER
    master = _read_json(master_path)
    if master.get("master_type") != "NUTEV_ARTICLE1_SEARCH_MASTER":
        raise Article1AgentContextError("unexpected Article 1 search master type")
    selected_search_id = str(
        search_id or master.get("production_search_id") or ""
    ).strip()
    if not selected_search_id:
        raise Article1AgentContextError("search_id is required")

    workbench_manifest, database, database_sha = _verified_workbench(output_root)
    route_manifest, membership, route_manifest_path, route_manifest_sha = _verified_routes(
        output_root, selected_search_id
    )
    route_counts = route_manifest.get("counts") or {}
    expected_tier_records = route_counts.get("tier_records")
    expected = int(expected_tier_records) if expected_tier_records is not None else None
    summaries = _article_summaries(
        database,
        membership,
        expected_tier_records=expected,
    )

    deepening_root = (
        output_root / "scientific" / "deepening" / selected_search_id / "tier-A"
    )
    review_root = (
        output_root / "scientific" / "review_queue" / selected_search_id / "tier-A"
    )
    route_root = (
        output_root / "scientific" / "review_routes" / selected_search_id / "article1"
    )
    deepening_manifest = _optional_manifest(deepening_root / "DEEPENING_MANIFEST.json")
    review_manifest = _optional_manifest(review_root / "REVIEW_QUEUE_MANIFEST.json")
    vocabulary_audit = _optional_manifest(route_root / "VOCABULARY_AUDIT.json")

    state = _search_state(
        master=master,
        search_id=selected_search_id,
        workbench_manifest=workbench_manifest,
        workbench_sha=database_sha,
        route_manifest=route_manifest,
        route_manifest_sha=route_manifest_sha,
        deepening_manifest=deepening_manifest,
        review_manifest=review_manifest,
        vocabulary_audit=vocabulary_audit,
        article_count=len(summaries),
    )

    output_dir = output_root / "agent_context" / "article1"
    summaries_path = output_dir / "ARTICLE_SUMMARIES.jsonl"
    state_path = output_dir / "SEARCH_STATE.json"
    summary_path = output_dir / "SEARCH_SUMMARY.md"
    summaries_sha = _write_jsonl(summaries_path, summaries)
    state_sha = _write_json(state_path, state)
    summary_sha = _atomic_text(summary_path, _summary_markdown(state))

    class_counts = Counter(str(row.get("document_class") or "unclassified") for row in summaries)
    route_counts_live = Counter(
        route for row in summaries for route in (row.get("routes") or [])
    )
    manifest = {
        "schema_version": 1,
        "context_type": "NUTEV_ARTICLE1_AGENT_CONTEXT",
        "context_version": AGENT_CONTEXT_VERSION,
        "status": "PASS",
        "created_at": _now(),
        "search_id": selected_search_id,
        "source": {
            "search_master": str(master_path),
            "search_master_sha256": sha256_file(master_path),
            "workbench_database": str(database),
            "workbench_database_sha256": database_sha,
            "route_queue_manifest": str(route_manifest_path),
            "route_queue_manifest_sha256": route_manifest_sha,
        },
        "counts": {
            "article_summaries": len(summaries),
            "document_class_counts": dict(sorted(class_counts.items())),
            "route_counts": dict(sorted(route_counts_live.items())),
        },
        "outputs": {
            "search_state": {"path": str(state_path), "sha256": state_sha},
            "search_summary": {"path": str(summary_path), "sha256": summary_sha},
            "article_summaries": {"path": str(summaries_path), "sha256": summaries_sha},
        },
        "safety": {
            "rank_blind": True,
            "full_text_included": False,
            "eligibility_decisions_included": False,
            "prisma_events_included": False,
            "external_llm_calls": 0,
        },
    }
    manifest_path = output_dir / "CONTEXT_MANIFEST.json"
    manifest_sha = _write_json(manifest_path, manifest)

    return {
        "mode": "NUTEV_ARTICLE1_AGENT_CONTEXT",
        "status": "COMPLETE",
        "context_version": AGENT_CONTEXT_VERSION,
        "search_id": selected_search_id,
        "article_summaries": len(summaries),
        "B-NORM": int(route_counts_live.get("B-NORM", 0)),
        "C-STRUCT": int(route_counts_live.get("C-STRUCT", 0)),
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "manifest_sha256": manifest_sha,
        "rank_blind": True,
        "full_text_included": False,
        "external_llm_calls": 0,
        "guardrail": (
            "Agent context only; does not change PRESS, GF-10, query freeze, eligibility, "
            "screening or PRISMA state."
        ),
    }
