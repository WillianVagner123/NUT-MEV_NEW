from __future__ import annotations

import json
from pathlib import Path

import pytest

from nutev.search.base import ProviderResult
from nutev.search.formal_execution_guard import default_freeze_path, default_gate_path
from nutev.search.scientific_gates import FreezeRecord, GateRecord, save_freeze_record, save_gate_records
from nutev.search.strategy_execution_ledger import list_execution_artifacts, list_search_runs
from nutev.search.strategy_executor import execute_strategy_version, parse_provider_expression
from nutev.search.strategy_registry import default_registry_path, list_search_executions, save_strategy_version

GIT_SHA = "a" * 40
CONFIG_DIGEST = "b" * 64


def _payload() -> dict:
    return {
        "article_scope": "all_articles",
        "query": ["food literacy", "food competence"],
        "filters": {"year_from": 2015, "year_to": 2026, "languages": ["eng"], "publication_types": []},
        "providers": {
            "pubmed": {"specific": '("food literacy"[tiab] OR "food competence"[tiab]) AND ("2015"[dp] : "2026"[dp])'},
            "crossref": {"specific": 'query="food literacy" "food competence" | filter=from-pub-date:2015-01-01,until-pub-date:2026-12-31'},
            "openalex": {"specific": 'query="food literacy" "food competence" | filter=from_publication_date:2015-01-01,language:eng'},
        },
    }


def _save_version(tmp_path: Path, *, search_type: str = "formal"):
    return save_strategy_version(default_registry_path(tmp_path), title=f"Executable {search_type}", query_text="food literacy; food competence", strategy_payload=_payload(), search_type=search_type, created_by="Researcher", created_at="2026-08-04T19:00:00-03:00")


def _authorize_formal(tmp_path: Path, version_id: str) -> None:
    gates = [GateRecord(gate_id=gate_id, requirement=f"Requirement for {gate_id}", evidence=(f"evidence:{gate_id}",), status="COMPLETED", owner="human-reviewer", completion_date="2026-08-13") for gate_id in ("GF-02", "GF-03", "GF-04", "GF-05", "GF-06", "GF-07", "GF-08", "GF-09")]
    gates.append(GateRecord(gate_id="GF-10", requirement="Global search freeze", evidence=("FREEZE-A1-001",), status="AUTHORIZED", owner="human-reviewer", completion_date="2026-08-13"))
    save_gate_records(default_gate_path(tmp_path), gates, registry_version="gates-v1")
    save_freeze_record(default_freeze_path(tmp_path), FreezeRecord(freeze_id="FREEZE-A1-001", date="2026-08-13", software_version="0.3.0.dev1", git_commit_sha=GIT_SHA, strategy_versions=(version_id,), source_registry_version="sources-v1", repository_registry_version="repositories-v1", sentinel_suite_version="sentinels-v1", press_evidence_id="PRESS-001", filters=(("language", "eng"),), final_search_date_rule="real execution date", config_digest=CONFIG_DIGEST, reviewers=("human-reviewer",)))


def _execute_formal(tmp_path: Path, version_id: str, **kwargs):
    return execute_strategy_version(tmp_path, version_id=version_id, authorization_git_sha=GIT_SHA, authorization_config_digest=CONFIG_DIGEST, **kwargs)


def test_parse_provider_expression_preserves_boolean_and_extracts_api_filter():
    pubmed = '(diet[tiab]) AND ("2020"[dp] : "2026"[dp])'
    assert parse_provider_expression("pubmed", pubmed) == (pubmed, "")
    assert parse_provider_expression("crossref", "query=food literacy | filter=from-pub-date:2020-01-01") == ("food literacy", "from-pub-date:2020-01-01")
    assert parse_provider_expression("openalex", "query=food competence") == ("food competence", "")


def test_formal_execution_is_blocked_before_any_run_without_gate_and_freeze_evidence(tmp_path):
    version = _save_version(tmp_path)
    with pytest.raises(RuntimeError, match="FORMAL execution blocked"):
        execute_strategy_version(tmp_path, version_id=version.version_id, providers=["pubmed"], search_fn=lambda **kwargs: ProviderResult(provider=kwargs["provider"], query=kwargs["query"], status="empty"))
    assert list_search_runs(default_registry_path(tmp_path), version_id=version.version_id) == []


def test_execute_frozen_version_writes_snapshots_and_prisma_counts(tmp_path):
    version = _save_version(tmp_path)
    _authorize_formal(tmp_path, version.version_id)
    calls: list[dict] = []

    def fake_search(**kwargs):
        calls.append(kwargs)
        provider = kwargs["provider"]
        return ProviderResult(provider=provider, query=kwargs["query"], rows=[{"title": f"Result from {provider}", "source_provider": provider}], total_found=7, total_returned=1, status="completed", meta={"fake": True})

    summary = _execute_formal(tmp_path, version.version_id, breadth="specific", providers=["pubmed", "crossref"], limit=25, resume=True, search_fn=fake_search, run_id="search_run_test_formal", started_at="2026-08-04T19:05:00-03:00")
    assert summary["status"] == "SUCCEEDED"
    assert summary["formal_authorization"]["authorized"] is True
    assert summary["records_identified_before_deduplication"] == 2
    assert summary["provider_reported_total_found"] == 14
    assert summary["prisma_records_identified"] == 2
    assert Path(summary["manifest_path"]).exists()
    assert summary["manifest_sha256"]
    crossref_call = next(call for call in calls if call["provider"] == "crossref")
    assert crossref_call["query"] == '"food literacy" "food competence"'
    assert crossref_call["context"]["provider_filter"] == "from-pub-date:2015-01-01,until-pub-date:2026-12-31"
    db_path = default_registry_path(tmp_path)
    runs = list_search_runs(db_path, version_id=version.version_id)
    assert len(runs) == 1 and runs[0]["records_identified"] == 2
    artifacts = list_execution_artifacts(db_path, run_id=runs[0]["run_id"])
    assert {row["provider"] for row in artifacts} == {"pubmed", "crossref"}
    for artifact in artifacts:
        snapshot = Path(artifact["snapshot_path"])
        assert snapshot.exists() and artifact["snapshot_sha256"]
        assert len([json.loads(line) for line in snapshot.read_text(encoding="utf-8").splitlines()]) == 1
    executions = list_search_executions(db_path, version_id=version.version_id)
    assert len(executions) == 2 and {row["status"] for row in executions} == {"SUCCEEDED"}


def test_pilot_execution_is_audited_but_does_not_feed_prisma(tmp_path):
    version = _save_version(tmp_path, search_type="pilot")
    def fake_search(**kwargs):
        return ProviderResult(provider=kwargs["provider"], query=kwargs["query"], rows=[{"title": "Pilot result"}], total_returned=1, status="completed")
    summary = execute_strategy_version(tmp_path, version_id=version.version_id, providers=["pubmed"], search_fn=fake_search, run_id="search_run_test_pilot")
    assert summary["records_identified_before_deduplication"] == 1
    assert summary["formal_authorization"]["required"] is False
    assert summary["prisma_eligible"] is False
    assert summary["prisma_records_identified"] == 0


def test_provider_failure_is_recorded_without_losing_successful_snapshot(tmp_path):
    version = _save_version(tmp_path)
    _authorize_formal(tmp_path, version.version_id)
    def fake_search(**kwargs):
        if kwargs["provider"] == "crossref":
            raise RuntimeError("simulated provider failure")
        return ProviderResult(provider=kwargs["provider"], query=kwargs["query"], rows=[{"title": "PubMed result"}], total_returned=1, status="completed")
    summary = _execute_formal(tmp_path, version.version_id, providers=["pubmed", "crossref"], search_fn=fake_search, run_id="search_run_test_partial")
    assert summary["status"] == "PARTIAL"
    assert summary["records_identified_before_deduplication"] == 1
    assert {item["provider"]: item["provider_status"] for item in summary["providers"]} == {"pubmed": "completed", "crossref": "failed"}
    assert all(Path(item["snapshot_path"]).exists() for item in summary["providers"])
