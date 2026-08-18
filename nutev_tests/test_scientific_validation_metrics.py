from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "evaluate_scientific_validation.py"
SPEC = importlib.util.spec_from_file_location("evaluate_scientific_validation", MODULE_PATH)
assert SPEC and SPEC.loader
validation = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validation
SPEC.loader.exec_module(validation)


def _items(question: str, system: str, reference_ids: list[str], split: str = ""):
    return [
        validation.RankingItem(question, system, index, reference_id, split)
        for index, reference_id in enumerate(reference_ids, start=1)
    ]


def test_perfect_ranking_has_perfect_core_metrics() -> None:
    gold = {"a": 2, "b": 1, "c": 0}
    row = validation.evaluate_group(
        "q1",
        "nutev",
        _items("q1", "nutev", ["a", "b", "c"]),
        gold,
    )
    assert row["reciprocal_rank"] == 1.0
    assert row["average_precision"] == 1.0
    assert row["average_precision_at_100"] == 1.0
    assert row["recall_at_10"] == 1.0
    assert row["ndcg_at_10"] == 1.0
    assert row["judgment_coverage_at_100"] == 1.0


def test_irrelevant_first_reduces_priority_metrics() -> None:
    gold = {"a": 2, "b": 1, "c": 0}
    row = validation.evaluate_group(
        "q1",
        "baseline",
        _items("q1", "baseline", ["c", "a", "b"]),
        gold,
    )
    assert row["reciprocal_rank"] == 0.5
    assert row["average_precision"] < 1.0
    assert row["ndcg_at_10"] < 1.0
    assert row["recall_at_10"] == 1.0


def test_unretrieved_relevant_record_reduces_recall_and_ap() -> None:
    gold = {"a": 2, "b": 1, "c": 1}
    row = validation.evaluate_group(
        "q1",
        "nutev",
        _items("q1", "nutev", ["a", "b"]),
        gold,
    )
    assert row["recall_at_100"] == pytest.approx(2 / 3, abs=1e-6)
    assert row["average_precision"] == pytest.approx(2 / 3, abs=1e-6)
    assert row["records_to_80_recall"] == ""


def test_unjudged_reference_inside_required_depth_fails_closed() -> None:
    gold = {"a": 2, "b": 0}
    with pytest.raises(validation.ValidationDataError, match="Incomplete judgment coverage"):
        validation.evaluate_group(
            "q1",
            "nutev",
            _items("q1", "nutev", ["a", "missing", "b"]),
            gold,
            required_judged_depth=3,
        )


def test_unjudged_after_required_depth_does_not_become_irrelevant() -> None:
    gold = {"a": 2, "b": 0}
    row = validation.evaluate_group(
        "q1",
        "nutev",
        _items("q1", "nutev", ["a", "b", "unjudged"]),
        gold,
        required_judged_depth=2,
    )
    assert row["judged_prefix_length"] == 2
    assert row["retrieved_all_judged"] is False
    assert row["average_precision"] == ""
    assert row["average_precision_at_100"] == 1.0
    assert row["reciprocal_rank"] == 1.0


def test_split_is_preserved_in_question_level_result() -> None:
    gold = {"a": 1}
    row = validation.evaluate_group(
        "q1",
        "nutev",
        _items("q1", "nutev", ["a"], split="external_test"),
        gold,
    )
    assert row["split"] == "external_test"


def test_duplicate_reference_in_ranking_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "rankings.csv"
    path.write_text(
        "question_id,system,rank,reference_id\n"
        "q1,nutev,1,a\n"
        "q1,nutev,2,a\n",
        encoding="utf-8",
    )
    with pytest.raises(validation.ValidationDataError, match="Duplicate reference"):
        validation.load_rankings(path)


def test_question_cannot_appear_in_multiple_splits(tmp_path: Path) -> None:
    path = tmp_path / "rankings.csv"
    path.write_text(
        "question_id,split,system,rank,reference_id\n"
        "q1,validation,nutev,1,a\n"
        "q1,external_test,baseline,1,a\n",
        encoding="utf-8",
    )
    with pytest.raises(validation.ValidationDataError, match="multiple splits"):
        validation.load_rankings(path)


def test_split_specific_loading_excludes_external_test(tmp_path: Path) -> None:
    path = tmp_path / "rankings.csv"
    path.write_text(
        "question_id,split,system,rank,reference_id\n"
        "qv,validation,nutev,1,a\n"
        "qe,external_test,nutev,1,b\n",
        encoding="utf-8",
    )
    rankings = validation.load_rankings(path, split="validation")
    assert set(rankings) == {("qv", "nutev")}
    assert rankings[("qv", "nutev")][0].split == "validation"


def test_split_specific_loading_requires_split_column(tmp_path: Path) -> None:
    path = tmp_path / "rankings.csv"
    path.write_text(
        "question_id,system,rank,reference_id\nq1,nutev,1,a\n",
        encoding="utf-8",
    )
    with pytest.raises(validation.ValidationDataError, match="split column"):
        validation.load_rankings(path, split="validation")


def test_system_filter_excludes_unjudged_secondary_systems(tmp_path: Path) -> None:
    path = tmp_path / "rankings.csv"
    path.write_text(
        "question_id,split,system,rank,reference_id\n"
        "q1,validation,nutev_full,1,a\n"
        "q1,validation,lexical_baseline,1,b\n"
        "q1,validation,nutev_no_taxonomy,1,c\n",
        encoding="utf-8",
    )
    rankings = validation.load_rankings(
        path,
        split="validation",
        systems=validation.DEFAULT_PRIMARY_SYSTEMS,
    )
    assert set(rankings) == {
        ("q1", "nutev_full"),
        ("q1", "lexical_baseline"),
    }


def test_missing_requested_evaluation_system_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "rankings.csv"
    path.write_text(
        "question_id,split,system,rank,reference_id\n"
        "q1,validation,nutev_full,1,a\n",
        encoding="utf-8",
    )
    with pytest.raises(validation.ValidationDataError, match="lexical_baseline"):
        validation.load_rankings(
            path,
            split="validation",
            systems=validation.DEFAULT_PRIMARY_SYSTEMS,
        )


def test_conflicting_gold_labels_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "gold.csv"
    path.write_text(
        "question_id,reference_id,relevance_grade\n"
        "q1,a,1\n"
        "q1,a,2\n",
        encoding="utf-8",
    )
    with pytest.raises(validation.ValidationDataError, match="Conflicting gold labels"):
        validation.load_gold(path)


def test_evaluate_adds_macro_row_per_system() -> None:
    gold = {
        "q1": {"a": 2, "b": 0},
        "q2": {"x": 1, "y": 0},
    }
    rankings = {
        ("q1", "nutev"): _items("q1", "nutev", ["a", "b"], "validation"),
        ("q2", "nutev"): _items("q2", "nutev", ["x", "y"], "external_test"),
    }
    rows = validation.evaluate(gold, rankings)
    macro = [row for row in rows if row["question_id"] == "__MACRO__"]
    assert len(macro) == 1
    assert macro[0]["system"] == "nutev"
    assert macro[0]["split"] == "__ALL__"
    assert macro[0]["reciprocal_rank"] == 1.0
