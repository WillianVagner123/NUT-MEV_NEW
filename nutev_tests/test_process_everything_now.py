from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from tools.process_everything_now import normalize_record, possible_duplicate_groups, run


def _write_jsonl(path: Path, rows: list[dict]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return sha256(path.read_bytes()).hexdigest()


def test_normalize_record_preserves_raw_and_never_decides_screening() -> None:
    row = normalize_record(
        {
            "title": "  Dietary   Guideline  ",
            "doi": "https://doi.org/10.1000/ABC.1",
            "pmid": "12345",
            "url": "https://example.org/doc",
            "source_provider": "pubmed",
        }
    )
    assert row["title"] == "Dietary Guideline"
    assert row["doi_normalized"].lower() == "10.1000/abc.1"
    assert row["pmid_normalized"] == "12345"
    assert row["raw_identity"]["doi"] == "https://doi.org/10.1000/ABC.1"
    assert row["human_screening_decision"] is None
    assert row["prisma_eligible"] is False
    assert row["formal_execution_authorized"] is False


def test_possible_duplicate_groups_are_flagged_not_auto_merged() -> None:
    a = normalize_record(
        {
            "title": "Nutrition recommendations for healthy adults in clinical practice",
            "pmid": "100",
            "source_provider": "pubmed",
        }
    )
    b = normalize_record(
        {
            "title": "Nutrition recommendations for healthy adults in clinical practice",
            "doi": "10.1000/different",
            "source_provider": "crossref",
        }
    )
    groups = possible_duplicate_groups([a, b])
    assert len(groups) == 1
    assert groups[0]["status"] == "POSSIBLE_DUPLICATE_HUMAN_REVIEW"
    assert groups[0]["auto_merged"] is False


def test_run_builds_clean_and_screening_outputs_without_scientific_promotion(tmp_path: Path) -> None:
    project_root = tmp_path / "project_output_scientific"
    run_dir = project_root / "13_collect_everything" / "everything_test"
    master_path = run_dir / "master_records.jsonl"
    master_sha = _write_jsonl(
        master_path,
        [
            {
                "title": "Guideline one",
                "abstract": "Nutrition guidance.",
                "pmid": "1",
                "source_provider": "pubmed",
            },
            {
                "title": "Guideline two",
                "abstract": "Dietary recommendation.",
                "doi": "10.1000/two",
                "source_provider": "crossref",
            },
        ],
    )
    state_path = project_root / "07_logs" / "collect_everything" / "latest.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "collection_type": "REAL_DISCOVERY_NONFORMAL",
                "run_id": "everything_test",
                "run_dir": str(run_dir),
                "master_records_path": str(master_path),
                "master_records_sha256": master_sha,
                "prisma_eligible": False,
                "formal_execution_authorized": False,
            }
        ),
        encoding="utf-8",
    )

    result = run(project_root)

    assert result["raw_preserved"] is True
    assert result["human_decision_inferred"] is False
    assert result["prisma_eligible"] is False
    assert result["formal_execution_authorized"] is False
    assert result["screening"]["automatic_include_exclude_decisions"] == 0
    assert result["technical_cleaning"]["records"] == 2
    assert Path(result["technical_cleaning"]["clean_records_path"]).is_file()
    assert Path(result["screening"]["queue_path"]).is_file()
    assert Path(result["fulltext"]["queue_path"]).is_file()
