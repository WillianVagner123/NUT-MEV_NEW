from __future__ import annotations

import json
from pathlib import Path

import nutev.pipelines.article1_pre_review_collection as collection
from nutev.search.strategy_registry import default_registry_path, save_strategy_version


def _save_pilot(project: Path, *, strategy_id: str | None = None, query: str = "nutrition"):
    return save_strategy_version(
        default_registry_path(project),
        title="Article 1 discovery",
        query_text=query,
        strategy_payload={
            "query": [query],
            "filters": {},
            "providers": {
                "pubmed": {"specific": query},
                "openalex": {"specific": f"query={query}"},
                "scielo_native": {"specific": f"query={query} | export=missing-scielo.csv"},
            },
        },
        search_type="PILOT",
        prisma_eligible=False,
        created_by="test",
        strategy_id=strategy_id,
    )


def _play_summary(project: Path) -> dict:
    summary_path = project / "12_play" / "play_x" / "play_summary.json"
    master = project / "03_corpus" / "master.jsonl"
    return {
        "play_id": "play_x",
        "status": {"execution_status": "COMPLETE"},
        "search": {
            "records_returned": 12,
            "provider_reported_total_found": 14,
            "any_truncated": False,
        },
        "corpus": {
            "unique_records": 9,
            "duplicates_removed": 3,
            "possible_duplicates": 1,
            "master_jsonl_path": str(master),
        },
        "artifacts": {"summary_path": str(summary_path)},
    }


def test_real_collection_runs_existing_pilot_without_promoting_formal_or_prisma(
    tmp_path: Path, monkeypatch
) -> None:
    project = tmp_path / "project"
    version = _save_pilot(project)
    called: dict = {}

    def fake_run_play(root: Path, **kwargs):
        called.update(kwargs)
        return _play_summary(root)

    monkeypatch.setattr(collection, "run_play", fake_run_play)

    result = collection.run_pre_review_collection(project)

    assert called["version_id"] == version.version_id
    assert called["providers"] == ["pubmed", "openalex"]
    assert called["metadata_only"] is True
    assert called["resume"] is True
    assert result["status"] == "COMPLETE"
    assert result["records_returned"] == 12
    assert result["unique_records"] == 9
    assert result["prisma_eligible"] is False
    assert result["formal_execution_authorized"] is False
    assert result["scientific_gate_effect"] == "NONE"
    assert result["human_decision_inferred"] is False
    deferred = {item["provider"]: item["reason"] for item in result["providers_deferred"]}
    assert deferred["scielo_native"] == "official_export_required_or_missing"
    assert deferred["scopus"] == "licensed_execution_required"
    assert deferred["web_of_science"] == "licensed_execution_required"

    persisted = json.loads(
        (project / "07_logs" / "pre_review_collection" / "latest.json").read_text(encoding="utf-8")
    )
    assert persisted["collection_type"] == "REAL_PRE_REVIEW_COLLECTION"
    assert persisted["prisma_eligible"] is False


def test_collection_is_invalidated_by_a_new_pilot_strategy_version(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    first = _save_pilot(project)
    monkeypatch.setattr(collection, "run_play", lambda root, **kwargs: _play_summary(root))
    collection.run_pre_review_collection(project)
    assert collection.pre_review_collection_status(project)["complete"] is True

    _save_pilot(project, strategy_id=first.strategy_id, query="nutrition guideline")
    status = collection.pre_review_collection_status(project)
    assert status["complete"] is False
    assert status["can_run"] is True


def test_collection_refuses_to_invent_strategy(tmp_path: Path) -> None:
    result = collection.run_pre_review_collection(tmp_path)
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "no_nonformal_pilot_strategy_registered"
    assert result["prisma_eligible"] is False
    assert result["formal_execution_authorized"] is False
