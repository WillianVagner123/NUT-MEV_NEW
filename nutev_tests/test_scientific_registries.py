from __future__ import annotations

import json
from pathlib import Path

import pytest

from nutev.search.scientific_registries import (
    GuidelineRepositoryRecord,
    SourceRegistryRecord,
    guideline_repository_records,
    registry_freeze_blockers,
    source_records_from_official_manifest,
    validate_guideline_repository_record,
    validate_source_record,
)


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict:
    return json.loads((ROOT / "config" / name).read_text(encoding="utf-8"))


def test_official_manifest_builds_deduplicated_candidate_registry_with_semantic_labels():
    records = source_records_from_official_manifest(_load("official_sources_manifest.json"))

    assert records
    assert len({row.source_id for row in records}) == len(records)
    assert all(row.status == "CANDIDATE" for row in records)
    assert all(not label.startswith("busca") for row in records for label in row.analytical_labels)
    assert any("policy_systems" in row.analytical_labels for row in records)
    assert any("clinical_outcomes" in row.analytical_labels for row in records)
    assert any("implementation" in row.analytical_labels for row in records)
    assert any("framework" in row.analytical_labels for row in records)


def test_candidate_source_can_be_incomplete_but_frozen_source_requires_reproducibility_fields():
    candidate = SourceRegistryRecord(
        source_id="SRC-TEST",
        source_class="official_institutional",
        organization="",
        geographic_scope="",
        status="CANDIDATE",
        canonical_url="https://example.org/guidelines",
        display_name="Example guidelines",
    )
    assert validate_source_record(candidate) == candidate

    frozen = SourceRegistryRecord(
        **{**candidate.__dict__, "status": "FROZEN"}
    )
    with pytest.raises(ValueError, match="lacks reproducibility fields"):
        validate_source_record(frozen)


def test_declared_guideline_repository_registry_is_candidate_only_until_verified():
    payload = _load("guideline_repository_registry.json")
    records = guideline_repository_records(payload)

    assert {row.repository_id for row in records} == {
        "GIN",
        "GIN_BIGG",
        "AWMF",
        "DUTCH_RICHTLIJNENDATABASE",
        "MINDS",
        "UKRAINE_REGISTRY",
    }
    assert all(row.formal_status == "NOT_AUTHORIZED" for row in records)


def test_formal_repository_requires_operational_search_evidence():
    record = GuidelineRepositoryRecord(
        repository_id="TEST",
        repository_name="Test repository",
        scope="guideline_repository",
        formal_status="AUTHORIZED",
    )
    with pytest.raises(ValueError, match="lacks reproducibility fields"):
        validate_guideline_repository_record(record)


def test_registry_freeze_blockers_are_explicit_for_candidate_state():
    sources = source_records_from_official_manifest(_load("official_sources_manifest.json"))
    repositories = guideline_repository_records(_load("guideline_repository_registry.json"))
    blockers = registry_freeze_blockers(sources, repositories)

    assert blockers
    assert any(item.endswith(":source_not_frozen") for item in blockers)
    assert "GIN:formal_not_authorized" in blockers
    assert "MINDS:formal_not_authorized" in blockers
