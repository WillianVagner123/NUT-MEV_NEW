from __future__ import annotations

import json
from pathlib import Path

import pytest

from nutev.governance import (
    governance_context,
    governance_digest,
    load_governance_manifest,
    normalize_article_scope,
    validate_governance_manifest,
)


def test_repository_manifest_preserves_canonical_a1_a4_objects() -> None:
    manifest = load_governance_manifest(Path("config/nutev_governance_manifest.json"))
    assert manifest["governance_version"] == "2026-08-18.a1-a4"
    assert manifest["articles"]["A1"]["object"] == "normative_and_structuring_documents"
    assert (
        manifest["articles"]["A2"]["object"]
        == "dietary_prescription_or_intervention_plus_operational_package"
    )
    assert manifest["articles"]["A3"]["object"] == "dietary_protocol_development"
    assert manifest["articles"]["A4"]["object"] == "conceptual_clinical_reasoning_framework"


def test_a2_cannot_be_redefined_as_generic_implementation_review() -> None:
    manifest = load_governance_manifest(Path("config/nutev_governance_manifest.json"))
    assert "generic_implementation_review" in manifest["articles"]["A2"]["forbidden_reclassification"]
    assert "implementation" in manifest["articles"]["A2"]["explanatory_dimensions"]


def test_a4_cannot_absorb_cfd_or_algorithmic_products() -> None:
    manifest = load_governance_manifest(Path("config/nutev_governance_manifest.json"))
    forbidden = set(manifest["articles"]["A4"]["forbidden_reclassification"])
    assert {"CFD-I", "CFD-8", "score", "flag_engine", "algorithm"}.issubset(forbidden)
    assert manifest["external_products"]["CFD-I"] == "parallel_manuscript_outside_A1_A4"
    assert manifest["external_products"]["CFD-8"] == "postdoctoral_A6"


def test_governance_validation_fails_closed_if_article_object_drifts() -> None:
    manifest = load_governance_manifest(Path("config/nutev_governance_manifest.json"))
    changed = json.loads(json.dumps(manifest))
    changed["articles"]["A2"]["object"] = "generic_implementation_review"
    with pytest.raises(ValueError, match="A2 object violates canonical"):
        validate_governance_manifest(changed)


def test_article_scope_normalization_is_closed() -> None:
    assert normalize_article_scope("a1") == "A1"
    assert normalize_article_scope("A4") == "A4"
    assert normalize_article_scope("all_articles") == "all_articles"
    with pytest.raises(ValueError, match="article_scope must be one of"):
        normalize_article_scope("A6")


def test_governance_context_is_auditable_and_deterministic() -> None:
    path = Path("config/nutev_governance_manifest.json")
    manifest = load_governance_manifest(path)
    first = governance_context("A2", path=path)
    second = governance_context("a2", path=path)
    assert first == second
    assert first["article_scope"] == "A2"
    assert first["article"]["object"] == "dietary_prescription_or_intervention_plus_operational_package"
    assert first["governance_sha256"] == governance_digest(manifest)
    assert first["engine_role"] == "reference_discovery_and_ranking_only"
    assert first["scientific_decision_policy"] == "human_only"


def test_reference_profiles_match_governance_version_and_boundaries() -> None:
    profiles = json.loads(Path("config/article_reference_profiles.json").read_text(encoding="utf-8"))
    assert profiles["governance_version"] == "2026-08-18.a1-a4"
    assert profiles["profiles"]["A2"]["interpretation_rule"].startswith(
        "implementation_competencies_and_context_are_explanatory"
    )
    assert "CFD-I" in profiles["profiles"]["A4"]["interpretation_rule"]
