from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "build_blinded_judgment_pool.py"
SPEC = importlib.util.spec_from_file_location("build_blinded_judgment_pool", MODULE_PATH)
assert SPEC and SPEC.loader
pool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pool)


def _metadata() -> dict[str, dict]:
    return {
        "doi:10.1000/a": {
            "title": "A",
            "abstract": "alpha",
            "doi": "10.1000/a",
            "reference_year": 2024,
        },
        "doi:10.1000/b": {
            "title": "B",
            "abstract": "beta",
            "doi": "10.1000/b",
            "reference_year": 2023,
        },
        "doi:10.1000/c": {
            "title": "C",
            "abstract": "gamma",
            "doi": "10.1000/c",
            "reference_year": 2022,
        },
    }


def test_pool_unions_systems_and_hides_membership() -> None:
    groups = {
        ("q1", "nutev_full"): [(1, "doi:10.1000/a"), (2, "doi:10.1000/b")],
        ("q1", "lexical_baseline"): [(1, "doi:10.1000/b"), (2, "doi:10.1000/c")],
    }
    blinded, audit = pool.build_pool(groups, _metadata(), seed="fixed")
    assert len(blinded) == 3
    assert len(audit) == 3
    assert all("system_membership" not in row for row in blinded)
    b_audit = next(row for row in audit if row["reference_id"] == "doi:10.1000/b")
    systems = json.loads(b_audit["system_membership"])
    assert systems == {"lexical_baseline": 1, "nutev_full": 2}


def test_blinded_order_is_deterministic() -> None:
    groups = {
        ("q1", "nutev_full"): [
            (1, "doi:10.1000/a"),
            (2, "doi:10.1000/b"),
            (3, "doi:10.1000/c"),
        ]
    }
    first, _ = pool.build_pool(groups, _metadata(), seed="same")
    second, _ = pool.build_pool(groups, _metadata(), seed="same")
    assert [row["reference_id"] for row in first] == [row["reference_id"] for row in second]


def test_missing_metadata_fails_closed() -> None:
    groups = {("q1", "nutev_full"): [(1, "doi:10.1000/missing")]}
    with pytest.raises(pool.PoolBuildError, match="no frozen metadata"):
        pool.build_pool(groups, _metadata())


def test_pool_depth_filters_rankings_on_load(tmp_path: Path) -> None:
    path = tmp_path / "rankings.csv"
    path.write_text(
        "question_id,system,rank,reference_id\n"
        "q1,nutev_full,1,doi:10.1000/a\n"
        "q1,nutev_full,2,doi:10.1000/b\n",
        encoding="utf-8",
    )
    groups = pool.load_rankings(path, depth=1)
    assert groups[("q1", "nutev_full")] == [(1, "doi:10.1000/a")]


def test_primary_system_filter_excludes_secondary_rankings(tmp_path: Path) -> None:
    path = tmp_path / "rankings.csv"
    path.write_text(
        "question_id,system,rank,reference_id\n"
        "q1,nutev_full,1,doi:10.1000/a\n"
        "q1,lexical_baseline,1,doi:10.1000/b\n"
        "q1,nutev_no_taxonomy,1,doi:10.1000/c\n",
        encoding="utf-8",
    )
    groups = pool.load_rankings(
        path,
        depth=100,
        systems=pool.DEFAULT_PRIMARY_SYSTEMS,
    )
    assert set(groups) == {
        ("q1", "nutev_full"),
        ("q1", "lexical_baseline"),
    }


def test_missing_requested_system_for_question_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "rankings.csv"
    path.write_text(
        "question_id,system,rank,reference_id\n"
        "q1,nutev_full,1,doi:10.1000/a\n"
        "q2,nutev_full,1,doi:10.1000/b\n"
        "q2,lexical_baseline,1,doi:10.1000/c\n",
        encoding="utf-8",
    )
    with pytest.raises(pool.PoolBuildError, match="q1/lexical_baseline"):
        pool.load_rankings(
            path,
            depth=100,
            systems=pool.DEFAULT_PRIMARY_SYSTEMS,
        )


def test_blinded_csv_has_no_system_or_rank_columns(tmp_path: Path) -> None:
    blinded, _ = pool.build_pool(
        {("q1", "nutev_full"): [(1, "doi:10.1000/a")]},
        _metadata(),
    )
    path = tmp_path / "blinded.csv"
    columns = [
        "question_id",
        "pool_item_id",
        "blinded_order",
        "reference_id",
        "title",
        "abstract",
        "journal",
        "year",
        "doi",
        "pmid",
        "pmcid",
        "url",
    ]
    pool._write_csv(path, blinded, columns)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        assert "system" not in (reader.fieldnames or [])
        assert "rank" not in (reader.fieldnames or [])
