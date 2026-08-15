from __future__ import annotations

import csv
from pathlib import Path

import pytest

from nutev.review.gf02_noise_review import (
    read_rescue_only_sample,
    review_progress,
    save_rescue_only_classification,
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
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(
            {
                "sample_id": "GF02-RESCUE-001",
                "record_id": "111",
                "pmid": "111",
                "doi": "10.1/a",
                "title": "First record",
                "provider": "PUBMED",
                "strategy_version": "B-NORM-PUBMED-v0.5-rescue-only",
                "sampling_rule": "fixed",
                "classification": "",
                "reviewer": "",
                "note": "",
            }
        )
        writer.writerow(
            {
                "sample_id": "GF02-RESCUE-002",
                "record_id": "222",
                "pmid": "222",
                "doi": "10.1/b",
                "title": "Second record",
                "provider": "PUBMED",
                "strategy_version": "B-NORM-PUBMED-v0.5-rescue-only",
                "sampling_rule": "fixed",
                "classification": "",
                "reviewer": "",
                "note": "",
            }
        )


def test_noise_review_updates_only_selected_row_and_preserves_metadata(tmp_path: Path) -> None:
    path = tmp_path / "rescue_only_sample_v0_5.csv"
    _sample(path)

    assert review_progress(path) == {
        "total": 2,
        "resolved": 0,
        "pending": 2,
        "complete": False,
        "precision_estimated": False,
    }

    saved = save_rescue_only_classification(
        path,
        sample_id="GF02-RESCUE-001",
        classification="irrelevant",
        reviewer="Willian Vagner",
        note="off-target",
    )
    assert saved["classification"] == "IRRELEVANT"

    rows = read_rescue_only_sample(path)
    assert [row["sample_id"] for row in rows] == ["GF02-RESCUE-001", "GF02-RESCUE-002"]
    assert rows[0]["record_id"] == "111"
    assert rows[0]["title"] == "First record"
    assert rows[0]["classification"] == "IRRELEVANT"
    assert rows[0]["reviewer"] == "Willian Vagner"
    assert rows[0]["note"] == "off-target"
    assert rows[1]["classification"] == ""
    assert review_progress(path)["pending"] == 1


def test_noise_review_requires_real_reviewer_and_explicit_classification(tmp_path: Path) -> None:
    path = tmp_path / "rescue_only_sample_v0_5.csv"
    _sample(path)

    with pytest.raises(ValueError, match="reviewer identity"):
        save_rescue_only_classification(
            path,
            sample_id="GF02-RESCUE-001",
            classification="RELEVANT",
            reviewer="",
        )
    with pytest.raises(ValueError, match="classification must be one of"):
        save_rescue_only_classification(
            path,
            sample_id="GF02-RESCUE-001",
            classification="",
            reviewer="R1",
        )


def test_noise_review_complete_only_after_every_row_has_human_fields(tmp_path: Path) -> None:
    path = tmp_path / "rescue_only_sample_v0_5.csv"
    _sample(path)
    save_rescue_only_classification(
        path,
        sample_id="GF02-RESCUE-001",
        classification="RELEVANT",
        reviewer="R1",
    )
    save_rescue_only_classification(
        path,
        sample_id="GF02-RESCUE-002",
        classification="DOUBT",
        reviewer="R1",
        note="insufficient metadata",
    )
    assert review_progress(path) == {
        "total": 2,
        "resolved": 2,
        "pending": 0,
        "complete": True,
        "precision_estimated": False,
    }
