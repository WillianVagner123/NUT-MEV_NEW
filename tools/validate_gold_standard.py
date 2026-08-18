from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


class GoldStandardError(RuntimeError):
    """Raised when assessor or adjudication evidence is incomplete/inconsistent."""


@dataclass(frozen=True)
class Assessment:
    question_id: str
    reference_id: str
    assessor_id: str
    relevance_grade: int
    blind_to_nutev: bool


def _clean(value: object) -> str:
    return str(value or "").strip()


def _grade(value: object, *, context: str) -> int:
    raw = _clean(value)
    try:
        grade = int(raw)
    except ValueError as exc:
        raise GoldStandardError(f"Invalid relevance_grade {raw!r} for {context}") from exc
    if grade not in {0, 1, 2}:
        raise GoldStandardError(f"relevance_grade must be 0, 1 or 2 for {context}")
    return grade


def _truthy(value: object) -> bool:
    return _clean(value).casefold() in {"1", "true", "yes", "y", "sim"}


def load_pool(path: Path) -> set[tuple[str, str]]:
    if not path.is_file():
        raise GoldStandardError(f"Blinded pool file not found: {path}")
    keys: set[tuple[str, str]] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"question_id", "reference_id"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise GoldStandardError(
                f"Blinded pool CSV missing columns: {', '.join(sorted(missing))}"
            )
        for line_number, row in enumerate(reader, start=2):
            question_id = _clean(row.get("question_id"))
            reference_id = _clean(row.get("reference_id"))
            if not question_id or not reference_id:
                raise GoldStandardError(f"Blank pool identity at line {line_number}")
            key = (question_id, reference_id)
            if key in keys:
                raise GoldStandardError(
                    f"Duplicate blinded-pool row for {question_id}/{reference_id}"
                )
            keys.add(key)
    if not keys:
        raise GoldStandardError("Blinded pool CSV contains no records")
    return keys


def load_assessments(path: Path) -> dict[tuple[str, str], list[Assessment]]:
    if not path.is_file():
        raise GoldStandardError(f"Assessments file not found: {path}")
    groups: dict[tuple[str, str], list[Assessment]] = {}
    seen: set[tuple[str, str, str]] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "question_id",
            "reference_id",
            "assessor_id",
            "relevance_grade",
            "blind_to_nutev",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise GoldStandardError(
                f"Assessments CSV missing columns: {', '.join(sorted(missing))}"
            )
        for line_number, row in enumerate(reader, start=2):
            question_id = _clean(row.get("question_id"))
            reference_id = _clean(row.get("reference_id"))
            assessor_id = _clean(row.get("assessor_id"))
            if not question_id or not reference_id or not assessor_id:
                raise GoldStandardError(f"Blank assessment identity at line {line_number}")
            key = (question_id, reference_id, assessor_id)
            if key in seen:
                raise GoldStandardError(
                    f"Duplicate assessor decision for {question_id}/{reference_id}/{assessor_id}"
                )
            seen.add(key)
            blind = _truthy(row.get("blind_to_nutev"))
            if not blind:
                raise GoldStandardError(
                    f"Assessment is not declared blind to NutEV for {question_id}/{reference_id}/{assessor_id}"
                )
            assessment = Assessment(
                question_id=question_id,
                reference_id=reference_id,
                assessor_id=assessor_id,
                relevance_grade=_grade(
                    row.get("relevance_grade"),
                    context=f"{question_id}/{reference_id}/{assessor_id}",
                ),
                blind_to_nutev=True,
            )
            groups.setdefault((question_id, reference_id), []).append(assessment)
    if not groups:
        raise GoldStandardError("Assessments CSV contains no decisions")
    return groups


def load_gold(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    if not path.is_file():
        raise GoldStandardError(f"Gold-standard file not found: {path}")
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "question_id",
            "reference_id",
            "relevance_grade",
            "adjudication_status",
            "adjudicator_id",
            "adjudication_timestamp",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise GoldStandardError(
                f"Gold-standard CSV missing columns: {', '.join(sorted(missing))}"
            )
        for line_number, row in enumerate(reader, start=2):
            question_id = _clean(row.get("question_id"))
            reference_id = _clean(row.get("reference_id"))
            if not question_id or not reference_id:
                raise GoldStandardError(f"Blank gold identity at line {line_number}")
            key = (question_id, reference_id)
            if key in rows:
                raise GoldStandardError(
                    f"Duplicate final gold row for {question_id}/{reference_id}"
                )
            item = dict(row)
            item["relevance_grade"] = _grade(
                row.get("relevance_grade"), context=f"gold {question_id}/{reference_id}"
            )
            rows[key] = item
    if not rows:
        raise GoldStandardError("Gold-standard CSV contains no final labels")
    return rows


def _sample(keys: set[tuple[str, str]]) -> list[tuple[str, str]]:
    return sorted(keys)[:5]


def validate(
    assessments: dict[tuple[str, str], list[Assessment]],
    gold: dict[tuple[str, str], dict[str, Any]],
    pool_keys: set[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    assessment_keys = set(assessments)
    gold_keys = set(gold)

    if pool_keys is not None:
        missing_assessments = pool_keys - assessment_keys
        extra_assessments = assessment_keys - pool_keys
        missing_gold = pool_keys - gold_keys
        extra_gold = gold_keys - pool_keys
        if missing_assessments:
            raise GoldStandardError(
                f"Blinded pool records missing raw assessments: {_sample(missing_assessments)}"
            )
        if extra_assessments:
            raise GoldStandardError(
                f"Raw assessments contain records outside blinded pool: {_sample(extra_assessments)}"
            )
        if missing_gold:
            raise GoldStandardError(
                f"Blinded pool records missing final gold rows: {_sample(missing_gold)}"
            )
        if extra_gold:
            raise GoldStandardError(
                f"Final gold contains records outside blinded pool: {_sample(extra_gold)}"
            )

    missing_final = assessment_keys - gold_keys
    missing_raw = gold_keys - assessment_keys
    if missing_final:
        raise GoldStandardError(
            f"Assessed records missing final gold rows: {_sample(missing_final)}"
        )
    if missing_raw:
        raise GoldStandardError(
            f"Final gold rows missing raw assessments: {_sample(missing_raw)}"
        )

    conflicts = 0
    agreements = 0
    assessor_counts: list[int] = []
    for key in sorted(gold_keys):
        decisions = assessments[key]
        unique_assessors = {item.assessor_id for item in decisions}
        if len(unique_assessors) < 2:
            raise GoldStandardError(
                f"Benchmark-grade gold requires at least two independent assessors for {key[0]}/{key[1]}"
            )
        assessor_counts.append(len(unique_assessors))
        grades = {item.relevance_grade for item in decisions}
        final = gold[key]
        final_grade = int(final["relevance_grade"])
        status = _clean(final.get("adjudication_status")).upper()

        if len(grades) == 1:
            agreed_grade = next(iter(grades))
            if final_grade != agreed_grade:
                raise GoldStandardError(
                    f"Final grade contradicts unanimous assessors for {key[0]}/{key[1]}"
                )
            if status not in {"AGREED", "RESOLVED"}:
                raise GoldStandardError(
                    f"Unanimous decision must be AGREED or RESOLVED for {key[0]}/{key[1]}"
                )
            agreements += 1
        else:
            conflicts += 1
            if status != "RESOLVED":
                raise GoldStandardError(
                    f"Conflicting assessors require RESOLVED status for {key[0]}/{key[1]}"
                )
            if not _clean(final.get("adjudicator_id")):
                raise GoldStandardError(
                    f"Conflicting assessors require adjudicator_id for {key[0]}/{key[1]}"
                )
            if not _clean(final.get("adjudication_timestamp")):
                raise GoldStandardError(
                    f"Conflicting assessors require adjudication_timestamp for {key[0]}/{key[1]}"
                )

    total = len(gold_keys)
    result: dict[str, Any] = {
        "status": "PASS",
        "final_labels": total,
        "raw_assessment_groups": len(assessment_keys),
        "unanimous_groups": agreements,
        "conflict_groups": conflicts,
        "raw_exact_agreement_fraction": round(agreements / total, 6) if total else None,
        "minimum_assessors_per_reference": min(assessor_counts) if assessor_counts else 0,
        "scientific_boundary": (
            "PASS validates pool coverage, completeness, blinding and adjudication consistency only. "
            "It does not validate the scientific correctness of human relevance judgments."
        ),
    }
    if pool_keys is not None:
        result["blinded_pool_rows"] = len(pool_keys)
        result["pool_assessment_coverage_fraction"] = 1.0
        result["pool_gold_coverage_fraction"] = 1.0
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate blinded assessor evidence and finalized NutEV gold-standard labels."
    )
    parser.add_argument("--pool", required=True)
    parser.add_argument("--assessments", required=True)
    parser.add_argument("--gold", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        result = validate(
            load_assessments(Path(args.assessments)),
            load_gold(Path(args.gold)),
            load_pool(Path(args.pool)),
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except GoldStandardError as exc:
        print(f"Gold-standard validation failure: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
