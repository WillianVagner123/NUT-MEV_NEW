"""Route deepened Article 1 evidence into rank-blind human reading queues.

The queues are navigation aids only. They do not emit eligibility, inclusion or
exclusion, PRISMA events, quality judgments, risk-of-bias judgments, certainty,
causal interpretation, or recommendations.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Mapping
from uuid import uuid4

from nutev.audit_guardrails import sha256_file


ROUTE_QUEUE_VERSION = "nutev_article1_route_queue_v1"
REQUIRED_PROFILE_VERSION = "nutev_review_profile_rule_v2"
ROUTES = ("B-NORM", "C-STRUCT")

_B_NORM_CLASSES = {
    "food_based_dietary_guideline",
    "clinical_practice_guideline",
    "consensus_statement",
    "position_statement",
}

_C_STRUCT_CLASSES = {
    "framework_model",
    "implementation_evaluation",
    "competency_curriculum",
}

_C_STRUCT_STRONG_DOMAINS = {
    "food_skills_competencies",
    "food_literacy",
    "nutrition_care_process",
    "implementation_practice",
}

_CARE_PROCESS_DOMAINS = {
    "nutrition_assessment",
    "dietary_counseling",
    "nutrition_prescription",
    "monitoring_follow_up",
}


class Article1RouteQueueError(RuntimeError):
    """Raised when Article 1 route queues cannot be proven from verified inputs."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise Article1RouteQueueError(f"missing JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Article1RouteQueueError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise Article1RouteQueueError(f"expected JSON object at {path}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise Article1RouteQueueError(f"missing JSONL file: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise Article1RouteQueueError(
                    f"invalid JSONL at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise Article1RouteQueueError(
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


def route_profile(profile: Mapping[str, Any]) -> dict[str, list[str]]:
    """Return Article 1 reading routes and explicit machine-routing bases."""
    document_class = str(profile.get("primary_document_class") or "unclassified")
    domains = {str(value) for value in (profile.get("operational_domains") or [])}
    routes: dict[str, list[str]] = {}

    if document_class in _B_NORM_CLASSES:
        routes["B-NORM"] = [f"document_class:{document_class}"]

    c_basis: list[str] = []
    if document_class in _C_STRUCT_CLASSES:
        c_basis.append(f"document_class:{document_class}")

    strong = sorted(domains & _C_STRUCT_STRONG_DOMAINS)
    c_basis.extend(f"domain:{value}" for value in strong)

    care = sorted(domains & _CARE_PROCESS_DOMAINS)
    if "lifestyle_medicine" in domains and care:
        c_basis.append("domain:lifestyle_medicine")
        c_basis.extend(f"care_process:{value}" for value in care)
    elif len(care) >= 2:
        c_basis.extend(f"care_process_pair:{value}" for value in care)

    if "social_context" in domains and (
        strong or care or "food_based_guidance" in domains
    ):
        c_basis.append("domain:social_context")

    if c_basis:
        routes["C-STRUCT"] = list(dict.fromkeys(c_basis))

    return routes


def _verified_profiles(
    output_root: Path,
    search_id: str,
    tier: str,
) -> tuple[list[dict[str, Any]], Path, str, dict[str, Any]]:
    review_root = output_root / "scientific" / "review_queue" / search_id / f"tier-{tier}"
    manifest_path = review_root / "REVIEW_QUEUE_MANIFEST.json"
    manifest = _read_json(manifest_path)
    if manifest.get("review_queue_type") != "NUTEV_TIER_REVIEW_PROFILE":
        raise Article1RouteQueueError("unexpected review queue manifest type")
    if manifest.get("status") != "PASS":
        raise Article1RouteQueueError("review profile manifest is not PASS")
    if str(manifest.get("profile_version") or "") != REQUIRED_PROFILE_VERSION:
        raise Article1RouteQueueError(
            "Article 1 route queues require review profile v2; rebuild Tier A profiles first"
        )

    output = ((manifest.get("outputs") or {}).get("review_profiles") or {})
    path = Path(str(output.get("path") or ""))
    if not path.is_absolute():
        path = (output_root.parent / path).resolve()
    expected = str(output.get("sha256") or "").strip().lower()
    if not path.is_file() or not expected:
        raise Article1RouteQueueError("review profiles path/hash missing")
    actual = sha256_file(path)
    if actual != expected:
        raise Article1RouteQueueError(
            f"review profiles SHA-256 mismatch: expected {expected}, got {actual}"
        )
    rows = _read_jsonl(path)
    if not rows:
        raise Article1RouteQueueError("review profiles are empty")
    return rows, path, actual, manifest


def _verified_workbench(output_root: Path) -> tuple[Path, str]:
    root = output_root / "scientific" / "workbench"
    manifest = _read_json(root / "WORKBENCH_MANIFEST.json")
    if manifest.get("workbench_type") != "NUTEV_ARTICLE_WORKBENCH_V1":
        raise Article1RouteQueueError("unexpected Workbench manifest type")
    if manifest.get("status") != "PASS":
        raise Article1RouteQueueError("Workbench manifest is not PASS")
    output = ((manifest.get("outputs") or {}).get("database") or {})
    path = Path(str(output.get("path") or ""))
    if not path.is_absolute():
        candidate = root / path.name
        path = candidate if candidate.is_file() else path.resolve()
    expected = str(output.get("sha256") or "").strip().lower()
    if not path.is_file() or not expected:
        raise Article1RouteQueueError("Workbench database/hash missing")
    actual = sha256_file(path)
    if actual != expected:
        raise Article1RouteQueueError(
            f"Workbench database SHA-256 mismatch: expected {expected}, got {actual}"
        )
    return path, actual


def _article_metadata(database: Path, document_ids: set[str]) -> dict[str, dict[str, Any]]:
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT document_id, title, year, doi, pmid, source_provider,
                   document_class, full_text_status, reference_stub
            FROM article_cards
            """
        ).fetchall()
    result = {
        str(row["document_id"]): dict(row)
        for row in rows
        if str(row["document_id"]) in document_ids
    }
    missing = sorted(document_ids - set(result))
    if missing:
        raise Article1RouteQueueError(
            f"Workbench is missing {len(missing)} profiled documents; first={missing[0]}"
        )
    return result


def _blind_order(search_id: str, route: str, document_id: str) -> str:
    return sha256(f"{search_id}|{route}|{document_id}".encode("utf-8")).hexdigest()


def build_article1_route_queues(
    search_id: str,
    *,
    output_root: Path = Path("project_output_reference"),
    tier: str = "A",
) -> dict[str, Any]:
    """Build rank-blind Article 1 B-NORM and C-STRUCT human reading queues."""
    output_root = output_root.resolve()
    tier = str(tier or "A").strip().upper()
    if tier != "A":
        raise Article1RouteQueueError("Article 1 route queue v1 is intentionally limited to Tier A")

    profiles, profiles_path, profiles_sha, profile_manifest = _verified_profiles(
        output_root, search_id, tier
    )
    database, database_sha = _verified_workbench(output_root)
    profile_by_id: dict[str, dict[str, Any]] = {}
    for profile in profiles:
        document_id = str(profile.get("document_id") or "").strip()
        if not document_id:
            raise Article1RouteQueueError("review profile missing document_id")
        if document_id in profile_by_id:
            raise Article1RouteQueueError(f"duplicate review profile: {document_id}")
        profile_by_id[document_id] = profile

    metadata = _article_metadata(database, set(profile_by_id))
    route_rows: dict[str, list[dict[str, Any]]] = {route: [] for route in ROUTES}
    document_routes: dict[str, set[str]] = {}

    for document_id, profile in profile_by_id.items():
        assigned = route_profile(profile)
        document_routes[document_id] = set(assigned)
        article = metadata[document_id]
        for route, basis in assigned.items():
            route_rows[route].append(
                {
                    "queue_version": ROUTE_QUEUE_VERSION,
                    "route": route,
                    "document_id": document_id,
                    "title": article.get("title"),
                    "year": article.get("year"),
                    "doi": article.get("doi"),
                    "pmid": article.get("pmid"),
                    "source_provider": article.get("source_provider"),
                    "document_class": profile.get("primary_document_class"),
                    "document_class_confidence": profile.get("document_class_confidence"),
                    "full_text_status": article.get("full_text_status"),
                    "reference_stub": article.get("reference_stub"),
                    "operational_domains": list(profile.get("operational_domains") or []),
                    "route_basis": basis,
                    "review_state": "unreviewed",
                    "guardrail": (
                        "Route assignment is a machine navigation aid only; not eligibility, "
                        "inclusion/exclusion, quality, risk of bias, certainty, recommendation, "
                        "or PRISMA event."
                    ),
                }
            )

    output_dir = output_root / "scientific" / "review_routes" / search_id / "article1"
    output_hashes: dict[str, str] = {}
    for route in ROUTES:
        rows = sorted(
            route_rows[route],
            key=lambda row: _blind_order(search_id, route, str(row["document_id"])),
        )
        for index, row in enumerate(rows, start=1):
            row["queue_order"] = index
        route_rows[route] = rows
        output_hashes[route] = _write_jsonl(output_dir / f"{route}.jsonl", rows)

    both = sum(1 for routes in document_routes.values() if len(routes) == 2)
    unrouted = sum(1 for routes in document_routes.values() if not routes)
    union = sum(1 for routes in document_routes.values() if routes)
    class_counts: dict[str, Counter[str]] = {route: Counter() for route in ROUTES}
    domain_counts: dict[str, Counter[str]] = {route: Counter() for route in ROUTES}
    for route in ROUTES:
        for row in route_rows[route]:
            class_counts[route].update([str(row.get("document_class") or "unclassified")])
            domain_counts[route].update(str(value) for value in row.get("operational_domains") or [])

    manifest = {
        "schema_version": 1,
        "queue_type": "NUTEV_ARTICLE1_ROUTE_REVIEW_QUEUE",
        "queue_version": ROUTE_QUEUE_VERSION,
        "status": "PASS",
        "created_at": _now(),
        "search_id": search_id,
        "tier": tier,
        "source": {
            "review_profiles": str(profiles_path),
            "review_profiles_sha256": profiles_sha,
            "review_profile_version": profile_manifest.get("profile_version"),
            "workbench_database": str(database),
            "workbench_database_sha256": database_sha,
        },
        "counts": {
            "tier_records": len(profiles),
            "B-NORM": len(route_rows["B-NORM"]),
            "C-STRUCT": len(route_rows["C-STRUCT"]),
            "route_union_documents": union,
            "route_overlap_documents": both,
            "unrouted_documents": unrouted,
        },
        "route_document_class_counts": {
            route: dict(sorted(counter.items())) for route, counter in class_counts.items()
        },
        "route_operational_domain_counts": {
            route: dict(sorted(counter.items())) for route, counter in domain_counts.items()
        },
        "outputs": {
            route: {
                "path": str(output_dir / f"{route}.jsonl"),
                "sha256": output_hashes[route],
            }
            for route in ROUTES
        },
        "blindness": {
            "reference_rank_exposed": False,
            "reference_score_exposed": False,
            "reference_tier_exposed": False,
            "machine_relevance_score_exposed": False,
            "machine_relevance_band_exposed": False,
            "queue_order": "deterministic_hash_not_bank_rank",
        },
        "guardrails": {
            "routes_are_navigation_only": True,
            "unrouted_is_not_excluded": True,
            "overlap_allowed": True,
            "no_prisma_event_emitted": True,
            "no_screening_decision_emitted": True,
            "external_llm_calls": 0,
        },
    }
    manifest_path = output_dir / "ROUTE_QUEUE_MANIFEST.json"
    manifest_sha = _write_json(manifest_path, manifest)

    return {
        "mode": "NUTEV_ARTICLE1_ROUTE_REVIEW_QUEUE",
        "status": "COMPLETE",
        "queue_version": ROUTE_QUEUE_VERSION,
        "search_id": search_id,
        "tier": tier,
        **manifest["counts"],
        "route_document_class_counts": manifest["route_document_class_counts"],
        "route_operational_domain_counts": manifest["route_operational_domain_counts"],
        "outputs": manifest["outputs"],
        "manifest": str(manifest_path),
        "manifest_sha256": manifest_sha,
        "external_llm_calls": 0,
        "guardrail": (
            "Rank-blind human reading queues only; no eligibility, inclusion/exclusion, "
            "quality, risk of bias, certainty, recommendation, or PRISMA event."
        ),
    }
