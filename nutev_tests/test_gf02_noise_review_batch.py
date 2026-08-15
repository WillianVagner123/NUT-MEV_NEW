from __future__ import annotations

import csv
from pathlib import Path

import pytest

from nutev.review.gf02_noise_review import (
    read_rescue_only_sample,
    review_progress,
    save_rescue_only_batch,
)


def _sample(path: Path) -> None:
    fields = [
        "sample_id",
        "record_id",
        "pmid",
        "doi",
        "title",
        "provider",
        "strategy_version",
        "sampling_rule",
        "classification",
        "reviewer",
        "note",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(
            {
                "sample_id": "GF02-RESCUE-001",
                "record_id": "1",
                "pmid": "1",
                "doi": "10.1/a",
                "title": "First",
                "provider": "PUBMED",
                "strategy_version": "v0.5",
                "sampling_rule": "fixed",
                "classification": "",
                "reviewer": "",
                "note": "",
            }
        )
        writer.writerow(
            {
                "sample_id": "GF02-RESCUE-002",
                "record_id": "2",
                "pmid": "2",
                "doi": "10.1/b",
                "title": "Second",
                "provider": "PUBMED",
                "strategy_version": "v0.5",
                "sampling_rule": "fixed",
                "classification": "",
                "reviewer": "",
                "note": "",
            }
        )


def test_batch_review_writes_all_rows_atomically_and_preserves_metadata(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    _sample(path)

    result = save_rescue_only_batch(
        path,
        reviewer="Willian",
        decisions=[
            {"sample_id": "GF02-RESCUE-001", "classification": "IRRELEVANT", "note": "off scope"},
            {"sample_id": "GF02-RESCUE-002", "classification": "DOUBT", "note": "needs checking"},
        ],
    )

    assert result["updated"] == 2
    rows = read_rescue_only_sample(path)
    assert [row["sample_id"] for row in rows] == ["GF02-RESCUE-001", "GF02-RESCUE-002"]
    assert rows[0]["pmid"] == "1"
    assert rows[0]["classification"] == "IRRELEVANT"
    assert rows[0]["reviewer"] == "Willian"
    assert rows[1]["classification"] == "DOUBT"
    assert rows[1]["reviewer"] == "Willian"
    assert review_progress(path)["complete"] is True


def test_batch_review_requires_one_real_reviewer_and_complete_decisions(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    _sample(path)

    with pytest.raises(ValueError, match="reviewer"):
        save_rescue_only_batch(
            path,
            reviewer="",
            decisions=[
                {"sample_id": "GF02-RESCUE-001", "classification": "RELEVANT", "note": ""},
                {"sample_id": "GF02-RESCUE-002", "classification": "IRRELEVANT", "note": ""},
            ],
        )

    with pytest.raises(ValueError, match="classification"):
        save_rescue_only_batch(
            path,
            reviewer="Willian",
            decisions=[
                {"sample_id": "GF02-RESCUE-001", "classification": "RELEVANT", "note": ""},
                {"sample_id": "GF02-RESCUE-002", "classification": "", "note": ""},
            ],
        )

    assert review_progress(path)["resolved"] == 0
