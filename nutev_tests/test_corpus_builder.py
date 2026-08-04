from __future__ import annotations

import json
from pathlib import Path

import pytest

from nutev.search.base import ProviderResult
from nutev.search.corpus_build_ledger import (
    export_decisions_json,
    list_corpus_builds,
)
from nutev.search.corpus_builder import build_corpus_from_search_run
from nutev.search.strategy_execution_ledger import list_execution_artifacts
from nutev.search.strategy_executor import execute_strategy_version
from nutev.search.strategy_registry import (
    default_registry_path,
    save_strategy_version,
)


def _payload() -> dict:
    return {
        "article_scope": "all_articles",
        "query": ["food competence"],
        "filters": {},
        "providers": {
            "pubmed": {"specific": "food competence[tiab]"},
            "europepmc": {"specific": '"food competence"'},
            "crossref": {"specific": 'query="food competence"'},
            "openalex": {"specific": 'query="food competence"'},
        },
    }


def _save_version(tmp_path: Path, search_type: str = "FORMAL"):
    return save_strategy_version(
        default_registry_path(tmp_path),
        title=f"Corpus {search_type}",
        query_text="food competence",
        strategy_payload=_payload(),
        search_type=search_type,
        created_by="Researcher",
        created_at="2026-08-04T19:00:00-03:00",
    )


def _execute(
    tmp_path: Path,
    version_id: str,
    rows_by_provider: dict,
    run_id: str,
):
    def fake_search(**kwargs):
        provider = kwargs["provider"]
        rows = list(rows_by_provider.get(provider, []))
        return ProviderResult(
            provider=provider,
            query=kwargs["query"],
            rows=rows,
            total_found=len(rows),
            total_returned=len(rows),
            status="completed",
        )

    return execute_strategy_version(
        tmp_path,
        registry_path=default_registry_path(tmp_path),
        version_id=version_id,
        breadth="specific",
        providers=list(rows_by_provider),
        limit=50,
        resume=False,
        search_fn=fake_search,
        run_id=run_id,
        started_at="2026-08-04T19:10:00-03:00",
    )


def test_builds_master_corpus_and_keeps_title_year_candidates_for_review(
    tmp_path,
):
    version = _save_version(tmp_path)
    _execute(
        tmp_path,
        version.version_id,
        {
            "pubmed": [
                {
                    "title": "Same paper",
                    "doi": "10.1000/ABC",
                    "pmid": "123",
                    "url": "https://pubmed.ncbi.nlm.nih.gov/123/",
                    "year": 2020,
                    "abstract": "short",
                }
            ],
            "crossref": [
                {
                    "title": "Same paper",
                    "doi": "https://doi.org/10.1000/abc",
                    "url": "https://doi.org/10.1000/abc",
                    "year": "2020",
                    "abstract": "a much longer abstract",
                }
            ],
            "openalex": [
                {
                    "title": "Possible title duplicate",
                    "url": "https://example.org/one",
                    "year": 2021,
                },
                {
                    "title": "Possible title duplicate",
                    "url": "https://example.org/two",
                    "year": 2021,
                },
            ],
        },
        "run_corpus_1",
    )

    result = build_corpus_from_search_run(
        tmp_path,
        registry_path=default_registry_path(tmp_path),
        run_id="run_corpus_1",
        build_id="build_corpus_1",
        started_at="2026-08-04T19:20:00-03:00",
    )

    assert result["status"] == "SUCCEEDED"
    assert result["metrics"] == {
        "input_records": 4,
        "unique_records": 3,
        "duplicates_removed": 1,
        "possible_duplicates": 1,
        "prisma_records_identified": 4,
        "prisma_duplicates_removed": 1,
        "prisma_records_after_deduplication": 3,
    }

    master_rows = [
        json.loads(line)
        for line in Path(result["master_jsonl_path"])
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(master_rows) == 3
    same_paper = next(
        row for row in master_rows if row["doi"] == "10.1000/abc"
    )
    assert same_paper["source_record_count"] == 2
    assert set(same_paper["matched_providers"].split("|")) == {
        "pubmed",
        "crossref",
    }
    assert same_paper["abstract"] == "a much longer abstract"

    possible = [
        row
        for row in master_rows
        if row["title"] == "Possible title duplicate"
    ]
    assert len(possible) == 2
    assert all(row["dedup_review_required"] is True for row in possible)
    assert (
        possible[0]["possible_duplicate_group_id"]
        == possible[1]["possible_duplicate_group_id"]
    )

    audit = export_decisions_json(
        default_registry_path(tmp_path),
        build_id="build_corpus_1",
    )
    assert len(audit["decisions"]) == 4
    assert (
        sum(
            row["decision_status"] == "AUTO_DUPLICATE"
            for row in audit["decisions"]
        )
        == 1
    )
    assert len(audit["candidates"]) == 1
    assert audit["candidates"][0]["review_status"] == "PENDING_HUMAN_REVIEW"
    assert Path(result["metadata_csv_path"]).exists()
    assert Path(result["manifest_path"]).exists()


def test_transitive_strong_identifiers_form_one_master_document(tmp_path):
    version = _save_version(tmp_path)
    _execute(
        tmp_path,
        version.version_id,
        {
            "pubmed": [
                {
                    "title": "A",
                    "doi": "10.1/a",
                    "pmid": "1",
                    "year": 2020,
                }
            ],
            "europepmc": [
                {
                    "title": "A",
                    "pmid": "1",
                    "pmcid": "PMC2",
                    "year": 2020,
                }
            ],
            "openalex": [
                {
                    "title": "A",
                    "pmcid": "PMC2",
                    "year": 2020,
                }
            ],
        },
        "run_transitive",
    )
    result = build_corpus_from_search_run(
        tmp_path,
        registry_path=default_registry_path(tmp_path),
        run_id="run_transitive",
        build_id="build_transitive",
    )
    assert result["metrics"]["input_records"] == 3
    assert result["metrics"]["unique_records"] == 1
    assert result["metrics"]["duplicates_removed"] == 2


def test_pilot_build_is_auditable_but_does_not_count_for_prisma(tmp_path):
    version = _save_version(tmp_path, search_type="PILOT")
    _execute(
        tmp_path,
        version.version_id,
        {
            "pubmed": [
                {
                    "title": "Pilot",
                    "pmid": "99",
                    "year": 2024,
                }
            ]
        },
        "run_pilot",
    )
    result = build_corpus_from_search_run(
        tmp_path,
        registry_path=default_registry_path(tmp_path),
        run_id="run_pilot",
        build_id="build_pilot",
    )
    assert result["metrics"]["input_records"] == 1
    assert result["metrics"]["unique_records"] == 1
    assert result["metrics"]["prisma_records_identified"] == 0
    assert result["metrics"]["prisma_records_after_deduplication"] == 0
    assert result["prisma"]["prisma_eligible"] is False


def test_tampered_snapshot_fails_build_and_is_recorded(tmp_path):
    version = _save_version(tmp_path)
    _execute(
        tmp_path,
        version.version_id,
        {
            "pubmed": [
                {
                    "title": "Integrity",
                    "pmid": "7",
                    "year": 2022,
                }
            ]
        },
        "run_tampered",
    )
    artifact = list_execution_artifacts(
        default_registry_path(tmp_path),
        run_id="run_tampered",
    )[0]
    snapshot = Path(artifact["snapshot_path"])
    snapshot.write_text(
        snapshot.read_text(encoding="utf-8") + "{}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="checksum mismatch"):
        build_corpus_from_search_run(
            tmp_path,
            registry_path=default_registry_path(tmp_path),
            run_id="run_tampered",
            build_id="build_tampered",
        )

    builds = list_corpus_builds(
        default_registry_path(tmp_path),
        run_id="run_tampered",
    )
    assert builds[0]["status"] == "FAILED"
    assert "checksum mismatch" in builds[0]["error_message"]
