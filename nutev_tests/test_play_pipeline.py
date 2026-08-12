from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from nutev.pipelines import play_pipeline
from nutev.search.strategy_registry import default_registry_path, save_strategy_version


def _payload() -> dict:
    return {
        "article_scope": "all_articles",
        "query": ["lifestyle nutrition"],
        "filters": {},
        "providers": {
            "pubmed": {
                "specific": '"lifestyle nutrition"[tiab]',
            }
        },
    }


def _save_version(tmp_path: Path, *, search_type: str):
    return save_strategy_version(
        default_registry_path(tmp_path),
        title=f"PLAY {search_type}",
        query_text="lifestyle nutrition",
        strategy_payload=_payload(),
        search_type=search_type,
        created_by="Researcher",
        created_at="2026-08-11T21:30:00-03:00",
    )


def test_provider_report_flags_truncation():
    rows = play_pipeline._provider_report(
        {
            "providers": [
                {
                    "provider": "pubmed",
                    "provider_status": "completed",
                    "records_returned": 10,
                    "total_found": 25,
                    "snapshot_path": "x.jsonl",
                    "snapshot_sha256": "abc",
                }
            ]
        }
    )
    assert rows[0]["truncated"] is True
    assert rows[0]["coverage_pct"] == 40.0


def test_play_refuses_prisma_eligible_formal_version(tmp_path):
    version = _save_version(tmp_path, search_type="formal")

    with pytest.raises(RuntimeError, match="refuses PRISMA-eligible/FORMAL"):
        play_pipeline.run_play(
            tmp_path,
            version_id=version.version_id,
            metadata_only=True,
        )


def test_play_metadata_only_executes_search_and_corpus_without_prisma(
    tmp_path,
    monkeypatch,
):
    version = _save_version(tmp_path, search_type="pilot")
    master_path = tmp_path / "master_records.jsonl"
    master_path.write_text(
        json.dumps(
            {
                "document_id": "doc_1",
                "title": "Pilot record",
                "doi": "10.1000/test",
                "url": "https://example.org/test",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    def fake_execute(*args, **kwargs):
        assert kwargs["version_id"] == version.version_id
        return {
            "run_id": "search_run_play_test",
            "status": "SUCCEEDED",
            "records_identified_before_deduplication": 1,
            "provider_reported_total_found": 3,
            "providers": [
                {
                    "provider": "pubmed",
                    "provider_status": "completed",
                    "records_returned": 1,
                    "total_found": 3,
                    "snapshot_path": str(tmp_path / "pubmed.jsonl"),
                    "snapshot_sha256": "abc",
                }
            ],
            "manifest_path": str(tmp_path / "search_manifest.json"),
        }

    def fake_build(*args, **kwargs):
        assert kwargs["run_id"] == "search_run_play_test"
        return {
            "build_id": "corpus_build_play_test",
            "status": "SUCCEEDED",
            "input_records": 1,
            "unique_records": 1,
            "duplicates_removed": 0,
            "possible_duplicates": 0,
            "master_jsonl_path": str(master_path),
            "manifest_path": str(tmp_path / "corpus_manifest.json"),
        }

    monkeypatch.setattr(play_pipeline, "execute_strategy_version", fake_execute)
    monkeypatch.setattr(play_pipeline, "build_corpus_from_search_run", fake_build)

    summary = play_pipeline.run_play(
        tmp_path,
        version_id=version.version_id,
        metadata_only=True,
    )

    assert summary["scientific_state"]["search_type"] == "PILOT"
    assert summary["status"]["prisma_eligible"] is False
    assert summary["status"]["formal_freeze_authorized"] is False
    assert summary["human_review"]["automatic_include_exclude_decisions"] == 0
    assert summary["search"]["any_truncated"] is True
    assert summary["corpus"]["unique_records"] == 1
    assert summary["fulltext"]["metadata_only_mode"] is True

    summary_path = Path(summary["artifacts"]["summary_path"])
    hash_path = Path(summary["artifacts"]["summary_sha256_path"])
    assert summary_path.is_file()
    assert hash_path.is_file()
    actual_sha256 = sha256(summary_path.read_bytes()).hexdigest()
    assert summary["artifacts"]["summary_sha256"] == actual_sha256
    assert hash_path.read_text(encoding="utf-8").split()[0] == actual_sha256
    persisted = json.loads(summary_path.read_text(encoding="utf-8"))
    assert "summary_sha256" not in persisted["artifacts"]
    assert persisted["artifacts"]["summary_sha256_path"] == str(hash_path)
    assert (tmp_path / "12_play" / "latest_summary.json").is_file()


def test_play_defaults_to_latest_registered_version(tmp_path, monkeypatch):
    older = _save_version(tmp_path, search_type="pilot")
    newer = save_strategy_version(
        default_registry_path(tmp_path),
        title="Newer PLAY strategy",
        query_text="nutrition guidelines",
        strategy_payload={
            **_payload(),
            "query": ["nutrition guidelines"],
        },
        search_type="pilot",
        created_by="Researcher",
        created_at="2026-08-11T21:31:00-03:00",
    )
    master_path = tmp_path / "latest_master.jsonl"
    master_path.write_text("{}\n", encoding="utf-8")

    seen: dict[str, str] = {}

    def fake_execute(*args, **kwargs):
        seen["version_id"] = kwargs["version_id"]
        return {
            "run_id": "latest_run",
            "status": "SUCCEEDED",
            "records_identified_before_deduplication": 1,
            "provider_reported_total_found": 1,
            "providers": [],
            "manifest_path": "",
        }

    def fake_build(*args, **kwargs):
        return {
            "build_id": "latest_build",
            "status": "SUCCEEDED",
            "input_records": 1,
            "unique_records": 1,
            "duplicates_removed": 0,
            "possible_duplicates": 0,
            "master_jsonl_path": str(master_path),
            "manifest_path": "",
        }

    monkeypatch.setattr(play_pipeline, "execute_strategy_version", fake_execute)
    monkeypatch.setattr(play_pipeline, "build_corpus_from_search_run", fake_build)

    summary = play_pipeline.run_play(tmp_path, metadata_only=True)

    assert older.version_id != newer.version_id
    assert seen["version_id"] == newer.version_id
    assert summary["scientific_state"]["version_id"] == newer.version_id
