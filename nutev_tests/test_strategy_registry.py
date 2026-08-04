from __future__ import annotations

import sqlite3

import pytest

from nutev.search.strategy_registry import (
    default_registry_path,
    get_strategy_version,
    list_search_executions,
    list_strategies,
    list_strategy_versions,
    record_search_execution,
    save_strategy_version,
)


def _payload() -> dict:
    return {
        "article_scope": "all_articles",
        "query": ["food literacy", "food competence"],
        "filters": {
            "year_from": 2015,
            "year_to": 2026,
            "languages": ["eng", "por"],
            "publication_types": [],
        },
        "providers": {
            "pubmed": {"balanced": '("food literacy"[tiab] OR "food competence"[tiab])'},
            "openalex": {"balanced": 'query="food literacy" "food competence"'},
        },
    }


def test_default_registry_path_uses_querypacks_directory(tmp_path):
    assert default_registry_path(tmp_path) == tmp_path / "01_querypacks" / "search_registry.sqlite3"


def test_save_new_strategy_and_append_immutable_version(tmp_path):
    db_path = default_registry_path(tmp_path)
    first = save_strategy_version(
        db_path,
        title="NutEV global search",
        query_text="food literacy; food competence",
        strategy_payload=_payload(),
        search_type="pilot",
        created_by="Researcher A",
        created_at="2026-08-04T18:00:00-03:00",
    )
    second = save_strategy_version(
        db_path,
        strategy_id=first.strategy_id,
        title="NutEV global search",
        query_text="food literacy; food competence",
        strategy_payload=_payload(),
        search_type="formal",
        created_by="Researcher A",
        notes="Protocol-approved version",
        created_at="2026-08-04T18:10:00-03:00",
    )

    assert first.version == 1
    assert first.prisma_eligible is False
    assert second.version == 2
    assert second.prisma_eligible is True
    assert first.version_id != second.version_id
    assert first.checksum_sha256 != second.checksum_sha256

    strategies = list_strategies(db_path)
    assert len(strategies) == 1
    assert strategies[0]["latest_version"] == 2

    versions = list_strategy_versions(db_path, strategy_id=first.strategy_id)
    assert [item["version"] for item in versions] == [2, 1]
    assert get_strategy_version(db_path, first.version_id)["search_type"] == "PILOT"


def test_same_content_has_stable_checksum(tmp_path):
    db_path = default_registry_path(tmp_path)
    first = save_strategy_version(
        db_path,
        title="Stable checksum",
        query_text="food literacy",
        strategy_payload=_payload(),
        search_type="formal",
        created_by="Researcher",
    )
    second = save_strategy_version(
        db_path,
        strategy_id=first.strategy_id,
        title="Stable checksum",
        query_text="food literacy",
        strategy_payload=_payload(),
        search_type="formal",
        created_by="Researcher",
    )
    assert first.checksum_sha256 == second.checksum_sha256


def test_existing_strategy_identity_cannot_be_renamed(tmp_path):
    db_path = default_registry_path(tmp_path)
    first = save_strategy_version(
        db_path,
        title="Original title",
        query_text="food literacy",
        strategy_payload=_payload(),
        search_type="pilot",
        created_by="Researcher",
    )
    with pytest.raises(ValueError, match="title cannot change"):
        save_strategy_version(
            db_path,
            strategy_id=first.strategy_id,
            title="Changed title",
            query_text="food literacy",
            strategy_payload=_payload(),
            search_type="formal",
            created_by="Researcher",
        )


def test_invalid_or_incomplete_strategy_is_rejected(tmp_path):
    db_path = default_registry_path(tmp_path)
    with pytest.raises(ValueError, match="search_type"):
        save_strategy_version(
            db_path,
            title="Invalid",
            query_text="food literacy",
            strategy_payload=_payload(),
            search_type="exploratory",
            created_by="Researcher",
        )
    bad_payload = _payload()
    bad_payload["query"] = []
    with pytest.raises(ValueError, match="at least one term"):
        save_strategy_version(
            db_path,
            title="Invalid",
            query_text="food literacy",
            strategy_payload=bad_payload,
            search_type="pilot",
            created_by="Researcher",
        )


def test_execution_is_linked_to_frozen_version(tmp_path):
    db_path = default_registry_path(tmp_path)
    version = save_strategy_version(
        db_path,
        title="Executable strategy",
        query_text="food literacy",
        strategy_payload=_payload(),
        search_type="formal",
        created_by="Researcher",
    )
    execution = record_search_execution(
        db_path,
        version_id=version.version_id,
        provider="pubmed",
        breadth="balanced",
        expression='("food literacy"[tiab])',
        status="succeeded",
        records_found=42,
    )
    assert execution["status"] == "SUCCEEDED"
    assert execution["finished_at"] is not None

    rows = list_search_executions(db_path, version_id=version.version_id)
    assert len(rows) == 1
    assert rows[0]["records_found"] == 42


def test_execution_rejects_unknown_version(tmp_path):
    db_path = default_registry_path(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        record_search_execution(
            db_path,
            version_id="missing",
            provider="pubmed",
            breadth="balanced",
            expression="food literacy",
        )
