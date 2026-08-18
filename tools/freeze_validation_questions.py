from __future__ import annotations

import argparse
import csv
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any


VALID_SPLITS = ("development", "validation", "external_test")
DEFAULT_MIN_EXTERNAL_QUESTIONS = 12
DEFAULT_MIN_OUTSIDE_HISTORICAL_FOCUS = 2
QUESTION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
REQUIRED_COLUMNS = {
    "question_id",
    "question_text",
    "split",
    "sampling_stratum",
    "outside_historical_focus",
    "population_context",
    "intervention_exposure",
    "comparator",
    "outcome_construct",
    "time_window",
    "languages",
    "document_types",
    "freeze_date",
    "human_approved_by",
    "human_approval_date",
    "notes",
}


class QuestionFreezeError(RuntimeError):
    """Raised when a benchmark question set is not ready for an auditable freeze."""


def _clean(value: object) -> str:
    return str(value or "").strip()


def _parse_iso_date(value: object, *, context: str) -> str:
    raw = _clean(value)
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as exc:
        raise QuestionFreezeError(
            f"Invalid ISO date for {context}: {raw!r}; expected YYYY-MM-DD"
        ) from exc
    return parsed.isoformat()


def _parse_bool(value: object, *, context: str) -> bool:
    raw = _clean(value).casefold()
    if raw in {"1", "true", "yes", "y", "sim"}:
        return True
    if raw in {"0", "false", "no", "n", "nao", "não"}:
        return False
    raise QuestionFreezeError(
        f"Invalid boolean for {context}: {value!r}; use true or false"
    )


def _normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())


def load_and_validate_questions(
    path: Path,
    *,
    min_external_questions: int = DEFAULT_MIN_EXTERNAL_QUESTIONS,
    min_outside_historical_focus: int = DEFAULT_MIN_OUTSIDE_HISTORICAL_FOCUS,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if min_external_questions < 1:
        raise QuestionFreezeError("min_external_questions must be >= 1")
    if min_outside_historical_focus < 0:
        raise QuestionFreezeError("min_outside_historical_focus must be >= 0")
    if not path.is_file():
        raise QuestionFreezeError(f"Question set not found: {path}")

    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_question_texts: set[str] = set()
    split_counts = {split: 0 for split in VALID_SPLITS}
    stratum_counts: dict[str, int] = {}
    approver_counts: dict[str, int] = {}
    outside_focus_count = 0

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - fields
        if missing:
            raise QuestionFreezeError(
                "QUESTIONS.csv missing columns: " + ", ".join(sorted(missing))
            )

        for line_number, raw in enumerate(reader, start=2):
            row = {key: _clean(value) for key, value in raw.items() if key is not None}
            question_id = row.get("question_id", "")
            question_text = row.get("question_text", "")
            split = row.get("split", "").casefold()
            sampling_stratum = row.get("sampling_stratum", "")
            approver = row.get("human_approved_by", "")

            if not QUESTION_ID_RE.fullmatch(question_id):
                raise QuestionFreezeError(
                    f"Invalid question_id at line {line_number}: {question_id!r}"
                )
            if question_id in seen_ids:
                raise QuestionFreezeError(f"Duplicate question_id: {question_id}")
            seen_ids.add(question_id)

            if not question_text:
                raise QuestionFreezeError(f"Blank question_text for {question_id}")
            normalized_text = _normalize_text(question_text)
            if normalized_text in seen_question_texts:
                raise QuestionFreezeError(
                    f"Duplicate normalized question_text detected at {question_id}"
                )
            seen_question_texts.add(normalized_text)

            if split not in VALID_SPLITS:
                raise QuestionFreezeError(
                    f"Invalid split for {question_id}: {row.get('split')!r}"
                )
            split_counts[split] += 1

            if not sampling_stratum:
                raise QuestionFreezeError(
                    f"Blank sampling_stratum for {question_id}"
                )
            stratum_counts[sampling_stratum] = stratum_counts.get(sampling_stratum, 0) + 1

            outside_focus = _parse_bool(
                row.get("outside_historical_focus"),
                context=f"{question_id}/outside_historical_focus",
            )
            if outside_focus:
                outside_focus_count += 1

            inclusion_context = any(
                row.get(field, "")
                for field in (
                    "population_context",
                    "intervention_exposure",
                    "outcome_construct",
                    "notes",
                )
            )
            if not inclusion_context:
                raise QuestionFreezeError(
                    f"No explicit inclusion context for {question_id}; fill population/exposure/outcome and/or notes"
                )

            freeze_date = _parse_iso_date(
                row.get("freeze_date"), context=f"{question_id}/freeze_date"
            )
            if not approver:
                raise QuestionFreezeError(
                    f"Missing human_approved_by declaration for {question_id}"
                )
            approval_date = _parse_iso_date(
                row.get("human_approval_date"),
                context=f"{question_id}/human_approval_date",
            )
            if approval_date > freeze_date:
                raise QuestionFreezeError(
                    f"human_approval_date occurs after freeze_date for {question_id}"
                )
            approver_counts[approver] = approver_counts.get(approver, 0) + 1

            row["split"] = split
            row["outside_historical_focus"] = outside_focus
            row["freeze_date"] = freeze_date
            row["human_approval_date"] = approval_date
            rows.append(row)

    if not rows:
        raise QuestionFreezeError("QUESTIONS.csv contains no questions")
    for required_split in VALID_SPLITS:
        if split_counts[required_split] < 1:
            raise QuestionFreezeError(
                f"Question set must contain at least one {required_split} question"
            )
    if split_counts["external_test"] < min_external_questions:
        raise QuestionFreezeError(
            "Insufficient external_test questions: "
            f"{split_counts['external_test']} < {min_external_questions}"
        )
    if outside_focus_count < min_outside_historical_focus:
        raise QuestionFreezeError(
            "Insufficient questions declared outside historical focus: "
            f"{outside_focus_count} < {min_outside_historical_focus}"
        )

    summary = {
        "question_count": len(rows),
        "split_counts": split_counts,
        "sampling_stratum_counts": dict(sorted(stratum_counts.items())),
        "outside_historical_focus_count": outside_focus_count,
        "declared_human_approver_counts": dict(sorted(approver_counts.items())),
    }
    return rows, summary


def build_manifest(
    path: Path,
    *,
    summary: dict[str, Any],
    min_external_questions: int,
    min_outside_historical_focus: int,
) -> dict[str, Any]:
    return {
        "status": "PASS",
        "artifact_type": "NUTEV_BENCHMARK_QUESTION_SET_FREEZE",
        "questions_path": str(path),
        "questions_sha256": sha256(path.read_bytes()).hexdigest(),
        "question_count": summary["question_count"],
        "split_counts": summary["split_counts"],
        "sampling_stratum_counts": summary["sampling_stratum_counts"],
        "outside_historical_focus_count": summary[
            "outside_historical_focus_count"
        ],
        "declared_human_approver_counts": summary[
            "declared_human_approver_counts"
        ],
        "minimum_external_questions_required": min_external_questions,
        "minimum_outside_historical_focus_required": min_outside_historical_focus,
        "human_approval_required": True,
        "semantic_independence_verified_by_software": False,
        "scientific_boundary": (
            "PASS proves schema, declared approval, split/sample floors and file integrity only. "
            "Software cannot verify that a human-approved question is scientifically well-formed, "
            "independent of NutEV performance, or representative of the target domain."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a human-approved NutEV benchmark question set and write an immutable SHA-256 freeze manifest."
        )
    )
    parser.add_argument("--questions", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument(
        "--min-external-questions",
        type=int,
        default=DEFAULT_MIN_EXTERNAL_QUESTIONS,
    )
    parser.add_argument(
        "--min-outside-historical-focus",
        type=int,
        default=DEFAULT_MIN_OUTSIDE_HISTORICAL_FOCUS,
    )
    args = parser.parse_args()

    try:
        _, summary = load_and_validate_questions(
            args.questions,
            min_external_questions=args.min_external_questions,
            min_outside_historical_focus=args.min_outside_historical_focus,
        )
        manifest = build_manifest(
            args.questions,
            summary=summary,
            min_external_questions=args.min_external_questions,
            min_outside_historical_focus=args.min_outside_historical_focus,
        )
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except QuestionFreezeError as exc:
        print(f"Question freeze failure: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
