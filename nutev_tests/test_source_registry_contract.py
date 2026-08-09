from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEARCH_PROVIDER_TYPES = {"search", "bibliographic", "official_source"}


def _load_config(name: str) -> dict:
    return json.loads((ROOT / "config" / name).read_text(encoding="utf-8"))


def test_source_registry_crosswalks_every_search_evidence_provider():
    source_registry = _load_config("source_registry.json")
    provider_registry = _load_config("provider_registry.json")

    source_entries = source_registry["providers"]
    crosswalk_ids = {
        entry.get("provider_registry_id", source_id)
        for source_id, entry in source_entries.items()
    }
    expected_ids = {
        provider["provider_id"]
        for provider in provider_registry["providers"]
        if provider.get("provider_type") in SEARCH_PROVIDER_TYPES
    }

    assert crosswalk_ids == expected_ids


def test_source_registry_method_tracks_are_explicit_and_valid():
    source_registry = _load_config("source_registry.json")
    allowed_tracks = {
        "indexed_database",
        "official_institutional",
        "supplementary_discovery",
    }

    for source_id, entry in source_registry["providers"].items():
        assert entry["method_track"] in allowed_tracks, source_id
        assert isinstance(entry["default_enabled"], bool), source_id
        assert isinstance(entry["priority"], int), source_id


def test_scielo_registry_does_not_claim_comprehensive_native_platform_search():
    scielo = _load_config("source_registry.json")["providers"]["scielo"]
    note = scielo["coverage_note"].lower()

    assert scielo["type"] == "crossref_prefix_connector"
    assert "10.1590" in note
    assert "not a comprehensive native scielo platform search" in note
