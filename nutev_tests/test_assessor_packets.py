from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "build_assessor_packets.py"
SPEC = importlib.util.spec_from_file_location("build_assessor_packets", MODULE_PATH)
assert SPEC and SPEC.loader
packets = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = packets
SPEC.loader.exec_module(packets)


def _pool_rows() -> list[dict[str, str]]:
    return [
        {
            "question_id": "q1",
            "pool_item_id": "pool_a",
            "blinded_order": "1",
            "reference_id": "doi:10.1000/a",
            "title": "A",
            "abstract": "alpha",
            "journal": "J",
            "year": "2024",
            "doi": "10.1000/a",
            "pmid": "",
            "pmcid": "",
            "url": "https://example.org/a",
        },
        {
            "question_id": "q1",
            "pool_item_id": "pool_b",
            "blinded_order": "2",
            "reference_id": "doi:10.1000/b",
            "title": "B",
            "abstract": "beta",
            "journal": "J",
            "year": "2023",
            "doi": "10.1000/b",
            "pmid": "",
            "pmcid": "",
            "url": "https://example.org/b",
        },
        {
            "question_id": "q1",
            "pool_item_id": "pool_c",
            "blinded_order": "3",
            "reference_id": "doi:10.1000/c",
            "title": "C",
            "abstract": "gamma",
            "journal": "J",
            "year": "2022",
            "doi": "10.1000/c",
            "pmid": "",
            "pmcid": "",
            "url": "https://example.org/c",
        },
    ]


def test_packet_has_no_ranking_or_system_fields() -> None:
    rows = packets.build_packet(_pool_rows(), "assessor_A", seed="fixed")
    assert rows
    forbidden = packets.FORBIDDEN_LEAKAGE_COLUMNS | {"blinded_order"}
    assert not (forbidden & set(rows[0]))
    assert all(row["blind_to_nutev"] == "true" for row in rows)
    assert all(row["relevance_grade"] == "" for row in rows)


def test_packet_order_is_deterministic_for_same_assessor() -> None:
    first = packets.build_packet(_pool_rows(), "assessor_A", seed="fixed")
    second = packets.build_packet(_pool_rows(), "assessor_A", seed="fixed")
    assert [row["reference_id"] for row in first] == [
        row["reference_id"] for row in second
    ]


def test_assessors_receive_same_items_in_independent_order() -> None:
    first = packets.build_packet(_pool_rows(), "assessor_A", seed="fixed")
    second = packets.build_packet(_pool_rows(), "assessor_B", seed="fixed")
    assert {row["reference_id"] for row in first} == {
        row["reference_id"] for row in second
    }
    assert [row["reference_id"] for row in first] != [
        row["reference_id"] for row in second
    ]


def test_leakage_column_in_input_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "bad_pool.csv"
    path.write_text(
        "question_id,pool_item_id,reference_id,title,system_membership\n"
        "q1,pool_a,doi:10.1000/a,A,{nutev_full:1}\n",
        encoding="utf-8",
    )
    with pytest.raises(packets.AssessorPacketError, match="forbidden"):
        packets.load_blinded_pool(path)


def test_written_packet_has_expected_assessment_columns(tmp_path: Path) -> None:
    path = tmp_path / "packet.csv"
    packets.write_packet(path, packets.build_packet(_pool_rows(), "a1", seed="fixed"))
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
    assert {
        "assessor_id",
        "relevance_grade",
        "reason",
        "decision_timestamp",
        "blind_to_nutev",
    }.issubset(fields)
    assert "system" not in fields
    assert "rank" not in fields
