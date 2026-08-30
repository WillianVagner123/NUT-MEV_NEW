"""Deterministic machine profiles for reviewer triage after deepening.

This layer classifies document *shape* and operational topic signals for review
navigation. It never emits eligibility, inclusion/exclusion, quality, risk of
bias, certainty, causal interpretation, or recommendation decisions.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Any, Iterable, Mapping
from uuid import uuid4

from nutev.audit_guardrails import sha256_file


PROFILE_VERSION = "nutev_review_profile_rule_v1"
_TIERS = {"A", "B", "C", "D"}


class ReviewProfileError(RuntimeError):
    """Raised when review profiles cannot be built with proven integrity."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ReviewProfileError(f"missing JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReviewProfileError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReviewProfileError(f"expected JSON object at {path}")
    return value


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


def _active_database(workbench_root: Path) -> tuple[dict[str, Any], Path, str]:
    manifest_path = workbench_root / "WORKBENCH_MANIFEST.json"
    manifest = _read_json(manifest_path)
    if manifest.get("workbench_type") != "NUTEV_ARTICLE_WORKBENCH_V1":
        raise ReviewProfileError("unexpected Workbench manifest type")
    if manifest.get("status") != "PASS":
        raise ReviewProfileError("Workbench manifest is not PASS")
    output = (manifest.get("outputs") or {}).get("database") or {}
    raw = str(output.get("path") or "").strip()
    expected = str(output.get("sha256") or "").strip().lower()
    database = Path(raw) if raw else workbench_root / "evidence_workbench.sqlite"
    if not database.is_absolute():
        candidate = workbench_root / database.name
        database = candidate if candidate.is_file() else database.resolve()
    if not database.is_file() or not expected:
        raise ReviewProfileError("active Workbench database or hash is missing")
    actual = sha256_file(database)
    if actual != expected:
        raise ReviewProfileError(
            f"Workbench database SHA-256 mismatch: expected {expected}, got {actual}"
        )
    return manifest, database, actual


def _normalize(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _flatten_strings(value: Any) -> list[str]:
    output: list[str] = []
    if isinstance(value, str):
        if value.strip():
            output.append(value)
    elif isinstance(value, Mapping):
        for item in value.values():
            output.extend(_flatten_strings(item))
    elif isinstance(value, list):
        for item in value:
            output.extend(_flatten_strings(item))
    return output


def _profile_text(row: Mapping[str, Any]) -> str:
    parts = [
        str(row.get("title") or ""),
        str(row.get("reference_stub") or ""),
        str(row.get("search_text") or ""),
    ]
    try:
        card = json.loads(str(row.get("card_json") or "{}"))
    except json.JSONDecodeError:
        card = {}
    parts.extend(_flatten_strings(card))
    return _normalize(" ".join(parts))[:120000]


def _hits(text: str, phrases: Iterable[str]) -> list[str]:
    found: list[str] = []
    for phrase in phrases:
        needle = _normalize(phrase)
        if needle and needle in text:
            found.append(phrase)
    return list(dict.fromkeys(found))


_DOCUMENT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "food_based_dietary_guideline",
        (
            "food-based dietary guideline",
            "food based dietary guideline",
            "food-based dietary guidelines",
            "dietary guidelines for americans",
            "national dietary guideline",
            "guias alimentares",
            "guia alimentar",
        ),
    ),
    (
        "clinical_practice_guideline",
        (
            "clinical practice guideline",
            "practice guideline",
            "clinical guideline",
            "guideline from the",
            "guideline for",
            "guidelines for",
        ),
    ),
    (
        "consensus_statement",
        ("consensus statement", "expert consensus", "consensus report", "consensus recommendations"),
    ),
    (
        "position_statement",
        ("position statement", "scientific statement", "professional statement", "position paper"),
    ),
    (
        "framework_model",
        (
            "conceptual framework",
            "operational framework",
            "care framework",
            "practice model",
            "conceptual model",
            "implementation framework",
        ),
    ),
    (
        "competency_curriculum",
        (
            "competenc",
            "curriculum",
            "medical education",
            "nutrition education",
            "culinary medicine curriculum",
            "training program",
        ),
    ),
    (
        "evidence_synthesis",
        ("systematic review", "scoping review", "meta-analysis", "meta analysis", "umbrella review"),
    ),
    (
        "implementation_evaluation",
        ("implementation study", "implementation evaluation", "feasibility study", "quality improvement"),
    ),
)


_DOMAIN_RULES: dict[str, tuple[str, ...]] = {
    "nutrition_assessment": (
        "dietary assessment", "nutrition assessment", "nutritional assessment", "diet assessment",
        "24-hour recall", "24 h recall", "food record", "food frequency questionnaire", "screening",
    ),
    "dietary_counseling": (
        "dietary counseling", "dietary counselling", "nutrition counseling", "nutrition counselling",
        "behavior change", "behaviour change", "motivational interviewing", "shared decision making",
    ),
    "nutrition_prescription": (
        "nutrition prescription", "diet prescription", "dietary prescription", "meal plan",
        "individualized diet", "individualised diet", "nutrition therapy", "dietary intervention",
    ),
    "monitoring_follow_up": (
        "monitoring", "follow-up", "follow up", "reassessment", "re-assessment", "longitudinal follow",
    ),
    "food_skills_competencies": (
        "food skills", "cooking skills", "culinary skills", "culinary medicine", "food competence",
        "food competencies", "nutrition competenc", "lifestyle medicine competenc",
    ),
    "food_literacy": (
        "food literacy", "nutrition literacy", "health literacy", "label literacy", "food knowledge",
    ),
    "social_context": (
        "social context", "social determinants", "food insecurity", "household", "family meal",
        "commensality", "socioeconomic", "socio-economic", "cultural", "culture", "community context",
    ),
    "food_based_guidance": (
        "food-based dietary guideline", "food based dietary guideline", "dietary guideline",
        "healthy eating pattern", "dietary pattern", "plate model", "food guide",
    ),
    "nutrition_care_process": (
        "nutrition care process", "nutrition diagnosis", "nutrition intervention", "adime",
        "nutrition monitoring and evaluation", "nutrition care",
    ),
    "lifestyle_medicine": (
        "lifestyle medicine", "lifestyle intervention", "healthy lifestyle", "lifestyle behavior",
        "lifestyle behaviour",
    ),
    "implementation_practice": (
        "implementation", "clinical workflow", "practice integration", "care pathway", "clinical pathway",
        "primary care", "healthcare delivery", "health care delivery",
    ),
}


_CLASS_WEIGHTS = {
    "food_based_dietary_guideline": 28,
    "clinical_practice_guideline": 28,
    "consensus_statement": 24,
    "position_statement": 22,
    "framework_model": 24,
    "competency_curriculum": 20,
    "evidence_synthesis": 15,
    "implementation_evaluation": 12,
    "primary_randomized": 8,
    "primary_observational": 6,
    "primary_qualitative": 8,
    "review": 10,
    "guidance": 20,
    "unclassified": 0,
}

_DOMAIN_WEIGHTS = {
    "nutrition_assessment": 9,
    "dietary_counseling": 10,
    "nutrition_prescription": 10,
    "monitoring_follow_up": 9,
    "food_skills_competencies": 12,
    "food_literacy": 10,
    "social_context": 10,
    "food_based_guidance": 12,
    "nutrition_care_process": 12,
    "lifestyle_medicine": 12,
    "implementation_practice": 7,
}


def build_review_profile(row: Mapping[str, Any]) -> dict[str, Any]:
    """Build one deterministic reviewer-navigation profile."""
    text = _profile_text(row)
    class_hits: dict[str, list[str]] = {}
    primary = str(row.get("document_class") or "unclassified").strip() or "unclassified"
    for label, phrases in _DOCUMENT_RULES:
        matches = _hits(text, phrases)
        if matches:
            class_hits[label] = matches
            if primary in {"", "unclassified", "review", "guidance"}:
                primary = label
            break

    domains: dict[str, list[str]] = {}
    for label, phrases in _DOMAIN_RULES.items():
        matches = _hits(text, phrases)
        if matches:
            domains[label] = matches

    score = int(_CLASS_WEIGHTS.get(primary, 0))
    score += sum(_DOMAIN_WEIGHTS.get(label, 0) for label in domains)
    score = max(0, min(score, 100))
    if score >= 60:
        band = "high"
    elif score >= 30:
        band = "medium"
    else:
        band = "low"

    return {
        "profile_version": PROFILE_VERSION,
        "document_id": str(row.get("document_id") or ""),
        "reference_rank": row.get("reference_rank"),
        "reference_score": row.get("reference_score"),
        "reference_tier": row.get("reference_tier"),
        "title": row.get("title"),
        "primary_document_class": primary,
        "document_class_matches": class_hits,
        "operational_domains": list(domains),
        "operational_domain_matches": domains,
        "machine_relevance_score": score,
        "machine_relevance_band": band,
        "full_text_status": row.get("full_text_status"),
        "guardrails": {
            "machine_profile_not_eligibility": True,
            "machine_profile_not_inclusion_or_exclusion": True,
            "machine_relevance_not_quality": True,
            "machine_relevance_not_risk_of_bias": True,
            "machine_relevance_not_certainty": True,
            "machine_relevance_not_recommendation": True,
            "no_prisma_event_emitted": True,
        },
    }


def build_tier_review_profiles(
    search_id: str,
    *,
    output_root: Path = Path("project_output_reference"),
    tier: str = "A",
) -> dict[str, Any]:
    """Profile one bank tier and atomically attach profiles to the Workbench."""
    output_root = output_root.resolve()
    tier = str(tier or "").strip().upper()
    if tier not in _TIERS:
        raise ReviewProfileError(f"invalid tier: {tier}")

    workbench_root = output_root / "scientific" / "workbench"
    manifest, active_database, source_database_sha = _active_database(workbench_root)

    with sqlite3.connect(f"file:{active_database}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(article_cards)")}
        required = {"reference_rank", "reference_score", "reference_tier"}
        if not required.issubset(columns):
            raise ReviewProfileError("Workbench bank-priority extension is required")
        rows = connection.execute(
            """
            SELECT document_id, title, reference_stub, search_text, card_json,
                   document_class, full_text_status, reference_rank, reference_score,
                   reference_tier
            FROM article_cards
            WHERE reference_tier = ?
            ORDER BY reference_rank ASC, document_id ASC
            """,
            (f"BANK_{tier}_PROCESSING_PRIORITY",),
        ).fetchall()

    if not rows:
        raise ReviewProfileError(f"no Workbench rows found for Tier {tier}")

    profiles = [build_review_profile(dict(row)) for row in rows]
    if len({p["document_id"] for p in profiles}) != len(profiles):
        raise ReviewProfileError("duplicate document_id in review profiles")

    review_root = output_root / "scientific" / "review_queue" / search_id / f"tier-{tier}"
    profiles_path = review_root / "review_profiles.jsonl"
    profiles_sha = _write_jsonl(profiles_path, profiles)

    target_database = workbench_root / "evidence_workbench_review.sqlite"
    tmp_database = workbench_root / f".evidence_workbench_review.{uuid4().hex}.tmp.sqlite"
    shutil.copy2(active_database, tmp_database)
    try:
        with sqlite3.connect(tmp_database) as connection:
            columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(article_cards)")}
            if "review_profile_json" not in columns:
                connection.execute("ALTER TABLE article_cards ADD COLUMN review_profile_json TEXT")
            if "machine_relevance_score" not in columns:
                connection.execute("ALTER TABLE article_cards ADD COLUMN machine_relevance_score REAL")
            if "machine_relevance_band" not in columns:
                connection.execute("ALTER TABLE article_cards ADD COLUMN machine_relevance_band TEXT")

            for profile in profiles:
                connection.execute(
                    """
                    UPDATE article_cards
                    SET document_class=?, review_profile_json=?,
                        machine_relevance_score=?, machine_relevance_band=?
                    WHERE document_id=?
                    """,
                    (
                        profile["primary_document_class"],
                        json.dumps(profile, ensure_ascii=False, sort_keys=True),
                        profile["machine_relevance_score"],
                        profile["machine_relevance_band"],
                        profile["document_id"],
                    ),
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_article_machine_relevance ON article_cards(machine_relevance_score DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_article_machine_relevance_band ON article_cards(machine_relevance_band)"
            )
            connection.execute(
                "INSERT OR REPLACE INTO workbench_meta(key,value) VALUES (?,?)",
                (f"review_profile_{tier}_search_id", search_id),
            )
            connection.execute(
                "INSERT OR REPLACE INTO workbench_meta(key,value) VALUES (?,?)",
                (f"review_profile_{tier}_sha256", profiles_sha),
            )
            connection.commit()
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise ReviewProfileError("review Workbench SQLite integrity_check failed")
            matched = int(
                connection.execute(
                    "SELECT COUNT(*) FROM article_cards WHERE reference_tier=? AND review_profile_json IS NOT NULL",
                    (f"BANK_{tier}_PROCESSING_PRIORITY",),
                ).fetchone()[0]
            )
    except Exception:
        tmp_database.unlink(missing_ok=True)
        raise

    if matched != len(profiles):
        tmp_database.unlink(missing_ok=True)
        raise ReviewProfileError(
            f"review profile join incomplete: profiles={len(profiles)}, matched={matched}"
        )

    database_sha = sha256_file(tmp_database)
    tmp_database.replace(target_database)

    class_counts = Counter(str(p["primary_document_class"]) for p in profiles)
    band_counts = Counter(str(p["machine_relevance_band"]) for p in profiles)
    domain_counts: Counter[str] = Counter()
    for profile in profiles:
        domain_counts.update(str(x) for x in profile["operational_domains"])

    extension = {
        "status": "PASS",
        "profile_version": PROFILE_VERSION,
        "created_at": _now(),
        "search_id": search_id,
        "tier": tier,
        "records": len(profiles),
        "profiles_jsonl": str(profiles_path),
        "profiles_sha256": profiles_sha,
        "source_database_sha256": source_database_sha,
        "class_counts": dict(sorted(class_counts.items())),
        "machine_relevance_band_counts": dict(sorted(band_counts.items())),
        "operational_domain_counts": dict(sorted(domain_counts.items())),
        "semantics": (
            "Deterministic reviewer-navigation profile only; not eligibility, inclusion/exclusion, "
            "quality, risk of bias, certainty, causal interpretation, recommendation, or PRISMA event."
        ),
    }

    manifest.setdefault("extensions", {})[f"review_profile_tier_{tier}"] = extension
    manifest["outputs"]["database"] = {"path": str(target_database), "sha256": database_sha}
    manifest_path = workbench_root / "WORKBENCH_MANIFEST.json"
    manifest_sha = _write_json(manifest_path, manifest)

    review_manifest = {
        "schema_version": 1,
        "review_queue_type": "NUTEV_TIER_REVIEW_PROFILE",
        "status": "PASS",
        "created_at": _now(),
        "search_id": search_id,
        "tier": tier,
        "profile_version": PROFILE_VERSION,
        "source": {
            "workbench_database": str(active_database),
            "workbench_database_sha256": source_database_sha,
        },
        "counts": {
            "records": len(profiles),
            "document_classes": dict(sorted(class_counts.items())),
            "machine_relevance_bands": dict(sorted(band_counts.items())),
            "operational_domains": dict(sorted(domain_counts.items())),
        },
        "outputs": {
            "review_profiles": {"path": str(profiles_path), "sha256": profiles_sha},
            "workbench_database": {"path": str(target_database), "sha256": database_sha},
            "workbench_manifest": {"path": str(manifest_path), "sha256": manifest_sha},
        },
        "guardrail": extension["semantics"],
    }
    review_manifest_path = review_root / "REVIEW_QUEUE_MANIFEST.json"
    review_manifest_sha = _write_json(review_manifest_path, review_manifest)

    return {
        "mode": "NUTEV_TIER_REVIEW_PROFILE",
        "status": "COMPLETE",
        "search_id": search_id,
        "tier": tier,
        "records": len(profiles),
        "document_class_counts": dict(sorted(class_counts.items())),
        "machine_relevance_band_counts": dict(sorted(band_counts.items())),
        "operational_domain_counts": dict(sorted(domain_counts.items())),
        "review_profiles": str(profiles_path),
        "review_profiles_sha256": profiles_sha,
        "database": str(target_database),
        "database_sha256": database_sha,
        "manifest": str(review_manifest_path),
        "manifest_sha256": review_manifest_sha,
        "external_llm_calls": 0,
        "guardrail": extension["semantics"],
    }
