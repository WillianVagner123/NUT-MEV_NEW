from __future__ import annotations

import json
from pathlib import Path

from nutev.search.base import ProviderResult
from nutev.search.strategy_execution_ledger import (
    list_execution_artifacts,
    list_search_runs,
)
from nutev.search.strategy_executor import (
    execute_strategy_version,
    parse_provider_expression,
)
from nutev.search.strategy_registry import (
    default_registry_path,
    list_search_executions,
    save_strategy_version,
)


def _payload() -> dict:
    return {
        "article_scope": "all_articles",
        "query": ["food literacy", "food competence"],
        "filters": {
            "year_from": 2015,
            "year_to": 2026,
            "languages": ["eng"],
            "publication_types": [],
        },
        "providers": {
            "pubmed": {
                "specific": '("food literacy"[tiab] OR "food competence"[tiab]) '
                'AND ("2015"[dp] : "2026"[dp])',
            },
            "crossref": {
                "specific": 'query="food literacy" "food competence" '
                "| filter=from-pub-date:2015-01-01,until-pub-date:2026-12-31",
            },
            "openalex": {
                "specific": 'query="food literacy" "food competence" '
                "| filter=from_publication_date:2015-01-01,language:eng",
            },
        },
    }


def _save_version(tmp_path: Path, *, search_type: str = "formal"):
    return save_strategy_version(
        default_registry_path(tmp_path),
        title=f"Executable {search_type}",
        query_text="food literacy; food competence",
        strategy_payload=_payload(),
        search_type=search_type,
        created_by="Researcher",
        created_at="2026-08-04T19:00:00-03:00",
    )


def test_parse_provider_expression_preserves_boolean_and_extracts_api_filter():
    pubmed = '(diet[tiab]) AND ("2020"[dp] : "2026"[dp])'
    assert parse_provider_expression("pubmed", pubmed) == (pubmed, "")
    assert parse_provider_expression(
        "crossref",
        "query=food literacy | filter=from-pub-date:2020-01-01",
    ) == ("food literacy", "from-pub-date:2020-01-01")
    assert parse_provider_expression("openalex", "query=food competence") == (
        "food competence",
        "",
    )


def test_execute_frozen_version_writes_snapshots_and_prisma_counts(tmp_path):
    version = _save_version(tmp_path)
    calls: list[dict] = []

    def fake_search(**kwargs):
        calls.append(kwargs)
        provider = kwargs["provider"]
        return ProviderResult(
            provider=provider,
            query=kwargs["query"],
            rows=[{"title": f"Result from {provider}", "source_provider": provider}],
            total_found=7,
            total_returned=1,
            status="completed",
            meta={"fake": True},
        )

    summary = execute_strategy_version(
        tmp_path,
        version_id=version.version_id,
        breadth="specific",
        providers=["pubmed", "crossref"],
        limit=25,
        resume=True,
        search_fn=fake_search,
        run_id="search_run_test_formal",
        started_at="2026-08-04T19:05:00-03:00",
    )

    assert summary["status"] == "SUCCEEDED"
    assert summary["records_identified_before_deduplication"] == 2
    assert summary["provider_reported_total_found"] == 14
    assert summary["prisma_records_identified"] == 2
    assert Path(summary["manifest_path"]).exists()
    assert summary["manifest_sha256"]

    crossref_call = next(call for call in calls if call["provider"] == "crossref")
    assert crossref_call["query"] == '"food literacy" "food competence"'
    assert crossref_call["context"]["provider_filter"] == (
        "from-pub-date:2015-01-01,until-pub-date:2026-12-31"
    )

    db_path = default_registry_path(tmp_path)
    runs = list_search_runs(db_path, version_id=version.version_id)
    assert len(runs) == 1
    assert runs[0]["run_id"] == "search_run_test_formal"
    assert runs[0]["records_identified"] == 2

    artifacts = list_execution_artifacts(db_path, run_id=runs[0]["run_id"])
    assert {row["provider"] for row in artifacts} == {"pubmed", "crossref"}
    for artifact in artifacts:
        snapshot = Path(artifact["snapshot_path"])
        assert snapshot.exists()
        assert artifact["snapshot_sha256"]
        rows = [json.loads(line) for line in snapshot.read_text(encoding="utf-8").splitlines()]
        assert len(rows) == 1

    executions = list_search_executions(db_path, version_id=version.version_id)
    assert len(executions) == 2
    assert {row["status"] for row in executions} == {"SUCCEEDED"}


def test_pilot_execution_is_audited_but_does_not_feed_prisma(tmp_path):
    version = _save_version(tmp_path, search_type="pilot")

    def fake_search(**kwargs):
        return ProviderResult(
            provider=kwargs["provider"],
            query=kwargs["query"],
            rows=[{"title": "Pilot result"}],
            total_returned=1,
            status="completed",
        )

    summary = execute_strategy_version(
        tmp_path,
        version_id=version.version_id,
        providers=["pubmed"],
        search_fn=fake_search,
        run_id="search_run_test_pilot",
    )
    assert summary["records_identified_before_deduplication"] == 1
    assert summary["prisma_eligible"] is False
    assert summary["prisma_records_identified"] == 0


def test_provider_failure_is_recorded_without_losing_successful_snapshot(tmp_path):
    version = _save_version(tmp_path)

    def fake_search(**kwargs):
        if kwargs["provider"] == "crossref":
            raise RuntimeError("simulated provider failure")
        return ProviderResult(
            provider=kwargs["provider"],
            query=kwargs["query"],
            rows=[{"title": "PubMed result"}],
            total_returned=1,
            status="completed",
        )

    summary = execute_strategy_version(
        tmp_path,
        version_id=version.version_id,
        providers=["pubmed", "crossref"],
        search_fn=fake_search,
        run_id="search_run_test_partial",
    )
    assert summary["status"] == "PARTIAL"
    assert summary["records_identified_before_deduplication"] == 1
    statuses = {item["provider"]: item["provider_status"] for item in summary["providers"]}
    assert statuses == {"pubmed": "completed", "crossref": "failed"}
    assert all(Path(item["snapshot_path"]).exists() for item in summary["providers"])
