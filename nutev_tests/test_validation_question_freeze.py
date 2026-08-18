from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "freeze_validation_questions.py"
SPEC = importlib.util.spec_from_file_location("freeze_validation_questions", MODULE_PATH)
assert SPEC and SPEC.loader
freeze = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = freeze
SPEC.loader.exec_module(freeze)


HEADER = (
    "question_id,question_text,split,sampling_stratum,outside_historical_focus,"
    "population_context,intervention_exposure,comparator,outcome_construct,time_window,"
    "languages,document_types,freeze_date,human_approved_by,human_approval_date,notes\n"
)


def _row(
    question_id: str,
    split: str,
    *,
    outside: str = "false",
    text: str | None = None,
    approver: str = "editor_1",
    approval_date: str = "2026-08-17",
    freeze_date: str = "2026-08-18",
) -> str:
    question_text = text or f"Question about {question_id}?"
    return (
        f"{question_id},{question_text},{split},stratum_{question_id},{outside},"
        "adults,dietary exposure,,health outcome,,en|pt|es,article|guideline,"
        f"{freeze_date},{approver},{approval_date},predefined eligibility criteria\n"
    )


def _valid_csv() -> str:
    return (
        HEADER
        + _row("dev_1", "development")
        + _row("val_1", "validation")
        + _row("ext_1", "external_test", outside="true")
        + _row("ext_2", "external_test", outside="true")
    )


def test_valid_human_approved_question_set_freezes(tmp_path: Path) -> None:
    questions = tmp_path / "QUESTIONS.csv"
    questions.write_text(_valid_csv(), encoding="utf-8")
    _, summary = freeze.load_and_validate_questions(
        questions,
        min_external_questions=2,
        min_outside_historical_focus=2,
    )
    manifest = freeze.build_manifest(
        questions,
        summary=summary,
        min_external_questions=2,
        min_outside_historical_focus=2,
    )
    assert manifest["status"] == "PASS"
    assert manifest["split_counts"] == {
        "development": 1,
        "validation": 1,
        "external_test": 2,
    }
    assert manifest["outside_historical_focus_count"] == 2
    assert manifest["semantic_independence_verified_by_software"] is False
    assert len(manifest["questions_sha256"]) == 64


def test_external_sample_floor_fails_closed(tmp_path: Path) -> None:
    questions = tmp_path / "QUESTIONS.csv"
    questions.write_text(_valid_csv(), encoding="utf-8")
    with pytest.raises(freeze.QuestionFreezeError, match="Insufficient external_test"):
        freeze.load_and_validate_questions(
            questions,
            min_external_questions=3,
            min_outside_historical_focus=2,
        )


def test_two_outside_focus_questions_are_required(tmp_path: Path) -> None:
    questions = tmp_path / "QUESTIONS.csv"
    questions.write_text(
        HEADER
        + _row("dev_1", "development")
        + _row("val_1", "validation")
        + _row("ext_1", "external_test", outside="true")
        + _row("ext_2", "external_test", outside="false"),
        encoding="utf-8",
    )
    with pytest.raises(freeze.QuestionFreezeError, match="outside historical focus"):
        freeze.load_and_validate_questions(
            questions,
            min_external_questions=2,
            min_outside_historical_focus=2,
        )


def test_duplicate_normalized_question_text_fails_closed(tmp_path: Path) -> None:
    questions = tmp_path / "QUESTIONS.csv"
    questions.write_text(
        HEADER
        + _row("dev_1", "development", text="Same scientific question?")
        + _row("val_1", "validation", text="  SAME   scientific question? ")
        + _row("ext_1", "external_test", outside="true")
        + _row("ext_2", "external_test", outside="true"),
        encoding="utf-8",
    )
    with pytest.raises(freeze.QuestionFreezeError, match="Duplicate normalized"):
        freeze.load_and_validate_questions(
            questions,
            min_external_questions=2,
            min_outside_historical_focus=2,
        )


def test_missing_human_approver_fails_closed(tmp_path: Path) -> None:
    questions = tmp_path / "QUESTIONS.csv"
    questions.write_text(
        HEADER
        + _row("dev_1", "development", approver="")
        + _row("val_1", "validation")
        + _row("ext_1", "external_test", outside="true")
        + _row("ext_2", "external_test", outside="true"),
        encoding="utf-8",
    )
    with pytest.raises(freeze.QuestionFreezeError, match="human_approved_by"):
        freeze.load_and_validate_questions(
            questions,
            min_external_questions=2,
            min_outside_historical_focus=2,
        )


def test_approval_cannot_be_after_freeze_date(tmp_path: Path) -> None:
    questions = tmp_path / "QUESTIONS.csv"
    questions.write_text(
        HEADER
        + _row(
            "dev_1",
            "development",
            approval_date="2026-08-19",
            freeze_date="2026-08-18",
        )
        + _row("val_1", "validation")
        + _row("ext_1", "external_test", outside="true")
        + _row("ext_2", "external_test", outside="true"),
        encoding="utf-8",
    )
    with pytest.raises(freeze.QuestionFreezeError, match="after freeze_date"):
        freeze.load_and_validate_questions(
            questions,
            min_external_questions=2,
            min_outside_historical_focus=2,
        )
