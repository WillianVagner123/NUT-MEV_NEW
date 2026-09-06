from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from tools.build_article1_press_human_review_packets import build_packets
from tools.validate_article1_press_human_review import validate


def _sample(tmp_path: Path) -> Path:
    records = []
    for delta, route in (("D02", "B-NORM"), ("D03", "C1-CARE-PROCESS")):
        for i in range(1, 3):
            records.append(
                {
                    "record_id": f"{delta}-PUBMED-{i:02d}-{1000+i}",
                    "delta_id": delta,
                    "route": route,
                    "route_purpose": "test purpose",
                    "sample_index": i,
                    "pmid": str(1000 + i),
                    "doi": None,
                    "title": f"Title {delta} {i}",
                    "year": "2026",
                    "journal": "Test Journal",
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{1000+i}/",
                }
            )
    data = {
        "schema_version": 1,
        "record_type": "NUTEV_ARTICLE1_PRESS_HUMAN_REVIEW_SAMPLE",
        "run_id": "test_run",
        "provider": "pubmed",
        "source_run_sha256": "0123456789abcdef" * 4,
        "records": records,
    }
    path = tmp_path / "sample.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _fill(path: Path, reviewer: str, decisions: dict[str, str]) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    assert fields is not None
    for row in rows:
        decision = decisions.get(row["record_id"], "Y")
        row["decision_Y_N_U"] = decision
        row["reason"] = "human reason"
        row["reviewer_id"] = reviewer
        row["reviewed_at"] = "2026-09-06T17:45:00-03:00"
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_packets_are_deterministic_independent_and_blank(tmp_path: Path) -> None:
    sample = _sample(tmp_path)
    out1 = tmp_path / "one"
    out2 = tmp_path / "two"
    m1 = build_packets(sample, out1)
    m2 = build_packets(sample, out2)
    assert m1["record_count"] == 4
    assert m1["record_ids_sha256"] == m2["record_ids_sha256"]
    assert (out1 / "REVIEWER_A.csv").read_bytes() == (out2 / "REVIEWER_A.csv").read_bytes()
    assert (out1 / "REVIEWER_B.csv").read_bytes() == (out2 / "REVIEWER_B.csv").read_bytes()
    assert (out1 / "REVIEWER_A.csv").read_bytes() != (out1 / "REVIEWER_B.csv").read_bytes()
    result = validate(out1 / "REVIEW_PACKET_MANIFEST.json", out1 / "REVIEWER_A.csv", out1 / "REVIEWER_B.csv")
    assert result["status"] == "PENDING_REVIEW"
    assert all(v["precision"] is None for v in result["final_per_delta"].values())
    assert result["guardrails"]["press_pass_created"] is False


def test_same_reviewer_identity_is_blocked(tmp_path: Path) -> None:
    sample = _sample(tmp_path)
    out = tmp_path / "packets"
    build_packets(sample, out)
    _fill(out / "REVIEWER_A.csv", "same-human", {})
    _fill(out / "REVIEWER_B.csv", "same-human", {})
    result = validate(out / "REVIEW_PACKET_MANIFEST.json", out / "REVIEWER_A.csv", out / "REVIEWER_B.csv")
    assert result["status"] == "REVIEWER_INDEPENDENCE_VIOLATION"
    assert result["final_per_delta"]["D02"]["precision"] is None


def test_u_blocks_precision(tmp_path: Path) -> None:
    sample = _sample(tmp_path)
    out = tmp_path / "packets"
    build_packets(sample, out)
    first_id = "D02-PUBMED-01-1001"
    _fill(out / "REVIEWER_A.csv", "human-a", {first_id: "U"})
    _fill(out / "REVIEWER_B.csv", "human-b", {})
    result = validate(out / "REVIEW_PACKET_MANIFEST.json", out / "REVIEWER_A.csv", out / "REVIEWER_B.csv")
    assert result["status"] == "HUMAN_REVIEW_HAS_UNRESOLVED_U"
    assert result["reviewer_A"]["per_delta"]["D02"]["precision"] is None


def test_conflict_requires_adjudication_and_then_completes(tmp_path: Path) -> None:
    sample = _sample(tmp_path)
    out = tmp_path / "packets"
    build_packets(sample, out)
    conflict_id = "D02-PUBMED-01-1001"
    _fill(out / "REVIEWER_A.csv", "human-a", {})
    _fill(out / "REVIEWER_B.csv", "human-b", {conflict_id: "N"})
    result = validate(out / "REVIEW_PACKET_MANIFEST.json", out / "REVIEWER_A.csv", out / "REVIEWER_B.csv")
    assert result["status"] == "READY_FOR_ADJUDICATION"
    assert result["conflict_count"] == 1
    assert result["final_per_delta"]["D02"]["precision"] is None

    adjudication = out / "ADJUDICATION.csv"
    with adjudication.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["record_id", "adjudicated_decision", "adjudication_reason", "adjudicator", "adjudicated_at"])
        writer.writerow([conflict_id, "N", "consensus", "human-c", "2026-09-06T18:00:00-03:00"])
    result = validate(
        out / "REVIEW_PACKET_MANIFEST.json",
        out / "REVIEWER_A.csv",
        out / "REVIEWER_B.csv",
        adjudication,
    )
    assert result["status"] == "HUMAN_DELTA_REVIEW_COMPLETE"
    assert result["final_per_delta"]["D02"]["Y"] == 1
    assert result["final_per_delta"]["D02"]["N"] == 1
    assert result["final_per_delta"]["D02"]["precision"] == 0.5
    assert result["guardrails"]["c4_decision_created"] is False


def test_invalid_label_fails_closed(tmp_path: Path) -> None:
    sample = _sample(tmp_path)
    out = tmp_path / "packets"
    build_packets(sample, out)
    _fill(out / "REVIEWER_A.csv", "human-a", {"D02-PUBMED-01-1001": "MAYBE"})
    _fill(out / "REVIEWER_B.csv", "human-b", {})
    with pytest.raises(ValueError, match="invalid decision"):
        validate(out / "REVIEW_PACKET_MANIFEST.json", out / "REVIEWER_A.csv", out / "REVIEWER_B.csv")
