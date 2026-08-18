"""Canonical NutEV A1-A4 governance contracts.

This module keeps article scope explicit and auditable without turning the
reference engine into a scientific or clinical decision-maker.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

CANONICAL_ARTICLE_SCOPES = frozenset({"A1", "A2", "A3", "A4", "all_articles"})
DEFAULT_GOVERNANCE_VERSION = "2026-08-18.a1-a4"

_EMBEDDED_ARTICLES: dict[str, dict[str, Any]] = {
    "A1": {
        "object": "normative_and_structuring_documents",
        "question": "what_is_recommended_and_how_recommendations_are_operationalized",
    },
    "A2": {
        "object": "dietary_prescription_or_intervention_plus_operational_package",
        "question": "how_current_dietary_prescriptions_are_structured_and_where_execution_or_maintenance_difficulties_arise",
    },
    "A3": {
        "object": "dietary_protocol_development",
        "question": "how_to_build_individualize_grade_adapt_and_sustain_the_dietary_prescription",
    },
    "A4": {
        "object": "conceptual_clinical_reasoning_framework",
        "question": "how_to_understand_longitudinally_the_path_from_prescription_to_execution_consequences_results_and_clinical_revision",
    },
}


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def governance_digest(manifest: Mapping[str, Any]) -> str:
    """Return a stable SHA-256 digest for the effective governance payload."""
    return sha256(_canonical_json(dict(manifest)).encode("utf-8")).hexdigest()


def embedded_governance_manifest() -> dict[str, Any]:
    """Return the minimum fail-safe governance embedded in the package."""
    return {
        "schema_version": 1,
        "governance_version": DEFAULT_GOVERNANCE_VERSION,
        "engine_role": "reference_discovery_and_ranking_only",
        "scientific_decision_policy": "human_only",
        "articles": {key: dict(value) for key, value in _EMBEDDED_ARTICLES.items()},
        "external_products": {
            "CFD-I": "parallel_manuscript_outside_A1_A4",
            "CFD-8": "postdoctoral_A6",
        },
    }


def default_governance_path() -> Path:
    """Resolve the repository governance file when running from a checkout."""
    return Path(__file__).resolve().parents[2] / "config" / "nutev_governance_manifest.json"


def validate_governance_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the canonical article boundaries and return a normalized copy."""
    if not isinstance(manifest, Mapping):
        raise TypeError("governance manifest must be a mapping")
    version = str(manifest.get("governance_version") or "").strip()
    if not version:
        raise ValueError("governance_version is required")
    if str(manifest.get("engine_role") or "") != "reference_discovery_and_ranking_only":
        raise ValueError("engine_role must remain reference_discovery_and_ranking_only")
    if str(manifest.get("scientific_decision_policy") or "") != "human_only":
        raise ValueError("scientific_decision_policy must remain human_only")

    articles = manifest.get("articles")
    if not isinstance(articles, Mapping):
        raise ValueError("articles mapping is required")
    if set(articles) != {"A1", "A2", "A3", "A4"}:
        raise ValueError("governance must define exactly A1, A2, A3 and A4")

    expected_objects = {
        "A1": "normative_and_structuring_documents",
        "A2": "dietary_prescription_or_intervention_plus_operational_package",
        "A3": "dietary_protocol_development",
        "A4": "conceptual_clinical_reasoning_framework",
    }
    for article, expected in expected_objects.items():
        payload = articles.get(article)
        if not isinstance(payload, Mapping):
            raise ValueError(f"{article} governance payload must be a mapping")
        if str(payload.get("object") or "") != expected:
            raise ValueError(f"{article} object violates canonical A1-A4 governance")

    external = manifest.get("external_products") or {}
    if not isinstance(external, Mapping):
        raise ValueError("external_products must be a mapping")
    if str(external.get("CFD-I") or "") != "parallel_manuscript_outside_A1_A4":
        raise ValueError("CFD-I must remain outside A1-A4")
    if str(external.get("CFD-8") or "") != "postdoctoral_A6":
        raise ValueError("CFD-8 must remain postdoctoral A6")
    return json.loads(_canonical_json(dict(manifest)))


def load_governance_manifest(path: Path | None = None) -> dict[str, Any]:
    """Load repository governance when available, otherwise use fail-safe embedded governance."""
    resolved = Path(path) if path is not None else default_governance_path()
    if resolved.is_file():
        data = json.loads(resolved.read_text(encoding="utf-8"))
        return validate_governance_manifest(data)
    return validate_governance_manifest(embedded_governance_manifest())


def normalize_article_scope(value: object) -> str:
    """Normalize article scope and reject ambiguous article-specific values."""
    raw = str(value or "all_articles").strip()
    if raw.casefold() == "all_articles":
        return "all_articles"
    normalized = raw.upper()
    if normalized not in {"A1", "A2", "A3", "A4"}:
        raise ValueError("article_scope must be one of A1, A2, A3, A4 or all_articles")
    return normalized


def governance_context(article_scope: object, *, path: Path | None = None) -> dict[str, Any]:
    """Return the auditable governance context that should accompany a run."""
    manifest = load_governance_manifest(path)
    scope = normalize_article_scope(article_scope)
    article = None if scope == "all_articles" else dict(manifest["articles"][scope])
    return {
        "governance_version": manifest["governance_version"],
        "governance_sha256": governance_digest(manifest),
        "article_scope": scope,
        "article": article,
        "engine_role": manifest["engine_role"],
        "scientific_decision_policy": manifest["scientific_decision_policy"],
    }


__all__ = [
    "CANONICAL_ARTICLE_SCOPES",
    "DEFAULT_GOVERNANCE_VERSION",
    "default_governance_path",
    "embedded_governance_manifest",
    "governance_context",
    "governance_digest",
    "load_governance_manifest",
    "normalize_article_scope",
    "validate_governance_manifest",
]
