from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "validate_gold_standard.py"
SPEC = importlib.util.spec_from_file_location("validate_gold_standard", MODULE_PATH)
assert SPEC and SPEC.loader
gold_validation = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = gold_validation
SPEC.loader.exec_module(gold_validation)


def _assessment(assessor: str, grade: int):
    return gold_validation.Assessment("q1", "doi:10.1000/x", assessor, grade, True)


def test_unanimous_two_assessor_gold_passes() -> None:
    assessments = {
        ("q1", "doi:10.1000/x"): [_assessment("a1", 2), _assessment("a2", 2)]
    }
    gold = {
        ("q1", "doi:10.1000/x"): {
            "relevance_grade": 2,
            "adjudication_status": "AGREED",
            "adjudicator_id": "",
            "adjudication_timestamp": "",
        }
    }
    result = gold_validation.validate(assessments, gold)
    assert result["status"] == "PASS"
    assert result["raw_exact_agreement_fraction"] == 1.0


def test_conflict_requires_human_adjudication_metadata() -> None:
    assessments = {
        ("q1", "doi:10.1000/x"): [_assessment("a1", 2), _assessment("a2", 0)]
    }
    gold = {
        ("q1", "doi:10.1000/x"): {
            "relevance_grade": 1,
            "adjudication_status": "RESOLVED",
            "adjudicator_id": "",
            "adjudication_timestamp": "",
        }
    }
    with pytest.raises(gold_validation.GoldStandardError, match="adjudicator_id"):
        gold_validation.validate(assessments, gold)


def test_conflict_with_adjudication_passes() -> None:
    assessments = {
        ("q1", "doi:10.1000/x"): [_assessment("a1", 2), _assessment("a2", 0)]
    }
    gold = {
        ("q1", "doi:10.1000/x"): {
            "relevance_grade": 1,
            "adjudication_status": "RESOLVED",
            "adjudicator_id": "adj1",
            "adjudication_timestamp": "2026-08-18T12:00:00-03:00",
        }
    }
    result = gold_validation.validate(assessments, gold)
    assert result["conflict_groups"] == 1
    assert result["raw_exact_agreement_fraction"] == 0.0


def test_single_assessor_is_not_benchmark_grade() -> None:
    assessments = {("q1", "doi:10.1000/x"): [_assessment("a1", 2)]}
    gold = {
        ("q1", "doi:10.1000/x"): {
            "relevance_grade": 2,
            "adjudication_status": "AGREED",
            "adjudicator_id": "",
            "adjudication_timestamp": "",
        }
    }
    with pytest.raises(gold_validation.GoldStandardError, match="at least two"):
        gold_validation.validate(assessments, gold)


def test_nonblind_assessment_fails_on_load(tmp_path: Path) -> None:
    path = tmp_path / "assessments.csv"
    path.write_text(
        "question_id,reference_id,assessor_id,relevance_grade,blind_to_nutev\n"
        "q1,doi:10.1000/x,a1,2,false\n",
        encoding="utf-8",
    )
    with pytest.raises(gold_validation.GoldStandardError, match="not declared blind"):
        gold_validation.load_assessments(path)


def test_gold_and_assessment_sets_must_match() -> None:
    assessments = {
        ("q1", "doi:10.1000/x"): [_assessment("a1", 2), _assessment("a2", 2)]
    }
    gold = {
        ("q2", "doi:10.1000/y"): {
            "relevance_grade": 1,
            "adjudication_status": "AGREED",
            "adjudicator_id": "",
            "adjudication_timestamp": "",
        }
    }
    with pytest.raises(gold_validation.GoldStandardError, match="missing final gold rows"):
        gold_validation.validate(assessments, gold)
