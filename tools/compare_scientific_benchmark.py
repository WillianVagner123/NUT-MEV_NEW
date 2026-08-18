from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import random
from statistics import mean, median
from typing import Any


PRIMARY_METRIC = "ndcg_at_20"
RECALL_GUARD_METRIC = "recall_at_100"
PRIMARY_COVERAGE_FIELD = "judgment_coverage_at_20"
RECALL_COVERAGE_FIELD = "judgment_coverage_at_100"
DEFAULT_CANDIDATE = "nutev_full"
DEFAULT_BASELINE = "lexical_baseline"
DEFAULT_BOOTSTRAP_ITERATIONS = 10_000
DEFAULT_BOOTSTRAP_SEED = "nutev-paired-bootstrap-v1"
MIN_EXTERNAL_QUESTIONS_FOR_DEFINED_USE = 12
RECALL_NONINFERIORITY_FLOOR = -0.05


class ComparisonError(RuntimeError):
    """Raised when paired benchmark results cannot support the preregistered comparison."""


def _clean(value: object) -> str:
    return str(value or "").strip()


def _number(row: dict[str, str], field: str, *, context: str) -> float:
    raw = _clean(row.get(field))
    if raw == "":
        raise ComparisonError(f"Missing numeric metric {field} for {context}")
    try:
        return float(raw)
    except ValueError as exc:
        raise ComparisonError(
            f"Invalid numeric metric {field}={raw!r} for {context}"
        ) from exc


def load_question_results(
    path: Path,
    *,
    split: str,
) -> dict[tuple[str, str], dict[str, str]]:
    if not path.is_file():
        raise ComparisonError(f"Benchmark results file not found: {path}")
    rows: dict[tuple[str, str], dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "question_id",
            "split",
            "system",
            PRIMARY_METRIC,
            RECALL_GUARD_METRIC,
            PRIMARY_COVERAGE_FIELD,
            RECALL_COVERAGE_FIELD,
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ComparisonError(
                f"Benchmark results CSV missing columns: {', '.join(sorted(missing))}"
            )
        for line_number, raw_row in enumerate(reader, start=2):
            question_id = _clean(raw_row.get("question_id"))
            row_split = _clean(raw_row.get("split"))
            system = _clean(raw_row.get("system"))
            if question_id == "__MACRO__":
                continue
            if not question_id or not system:
                raise ComparisonError(f"Blank question_id/system at line {line_number}")
            if row_split != split:
                continue
            key = (question_id, system)
            if key in rows:
                raise ComparisonError(
                    f"Duplicate question/system result: {question_id}/{system}"
                )
            rows[key] = dict(raw_row)
    if not rows:
        raise ComparisonError(f"No question-level benchmark rows found for split={split}")
    return rows


def _percentile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        raise ComparisonError("Cannot calculate percentile of empty sample")
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return sorted_values[lower] * (1.0 - fraction) + sorted_values[upper] * fraction


def bootstrap_mean_ci(
    values: list[float],
    *,
    iterations: int = DEFAULT_BOOTSTRAP_ITERATIONS,
    seed: str = DEFAULT_BOOTSTRAP_SEED,
    alpha: float = 0.05,
) -> tuple[float, float]:
    if not values:
        raise ComparisonError("Cannot bootstrap an empty paired-delta sample")
    if iterations < 100:
        raise ComparisonError("bootstrap iterations must be >= 100")
    if not 0.0 < alpha < 1.0:
        raise ComparisonError("alpha must be between 0 and 1")
    rng = random.Random(seed)
    n = len(values)
    estimates = [
        mean(values[rng.randrange(n)] for _ in range(n))
        for _ in range(iterations)
    ]
    estimates.sort()
    return (
        _percentile(estimates, alpha / 2.0),
        _percentile(estimates, 1.0 - alpha / 2.0),
    )


def compare(
    rows: dict[tuple[str, str], dict[str, str]],
    *,
    split: str,
    candidate: str = DEFAULT_CANDIDATE,
    baseline: str = DEFAULT_BASELINE,
    bootstrap_iterations: int = DEFAULT_BOOTSTRAP_ITERATIONS,
    bootstrap_seed: str = DEFAULT_BOOTSTRAP_SEED,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    questions = sorted({question_id for question_id, _ in rows})
    paired: list[dict[str, Any]] = []
    for question_id in questions:
        candidate_row = rows.get((question_id, candidate))
        baseline_row = rows.get((question_id, baseline))
        if candidate_row is None or baseline_row is None:
            missing = candidate if candidate_row is None else baseline
            raise ComparisonError(
                f"Missing preregistered system {missing} for question {question_id}"
            )
        context_candidate = f"{question_id}/{candidate}"
        context_baseline = f"{question_id}/{baseline}"
        for coverage_field in (PRIMARY_COVERAGE_FIELD, RECALL_COVERAGE_FIELD):
            candidate_coverage = _number(
                candidate_row, coverage_field, context=context_candidate
            )
            baseline_coverage = _number(
                baseline_row, coverage_field, context=context_baseline
            )
            if candidate_coverage < 1.0 or baseline_coverage < 1.0:
                raise ComparisonError(
                    "Preregistered comparison requires complete judgment coverage through "
                    f"the endpoint depth: {question_id}/{coverage_field} "
                    f"candidate={candidate_coverage}, baseline={baseline_coverage}"
                )

        candidate_primary = _number(
            candidate_row, PRIMARY_METRIC, context=context_candidate
        )
        baseline_primary = _number(
            baseline_row, PRIMARY_METRIC, context=context_baseline
        )
        candidate_recall = _number(
            candidate_row, RECALL_GUARD_METRIC, context=context_candidate
        )
        baseline_recall = _number(
            baseline_row, RECALL_GUARD_METRIC, context=context_baseline
        )
        primary_delta = candidate_primary - baseline_primary
        recall_delta = candidate_recall - baseline_recall
        paired.append(
            {
                "question_id": question_id,
                "split": split,
                "candidate": candidate,
                "baseline": baseline,
                "candidate_ndcg_at_20": round(candidate_primary, 6),
                "baseline_ndcg_at_20": round(baseline_primary, 6),
                "delta_ndcg_at_20": round(primary_delta, 6),
                "candidate_recall_at_100": round(candidate_recall, 6),
                "baseline_recall_at_100": round(baseline_recall, 6),
                "delta_recall_at_100": round(recall_delta, 6),
                "outcome": (
                    "WIN" if primary_delta > 0 else "LOSS" if primary_delta < 0 else "TIE"
                ),
            }
        )

    deltas = [float(row["delta_ndcg_at_20"]) for row in paired]
    recall_deltas = [float(row["delta_recall_at_100"]) for row in paired]
    wins = sum(row["outcome"] == "WIN" for row in paired)
    losses = sum(row["outcome"] == "LOSS" for row in paired)
    ties = sum(row["outcome"] == "TIE" for row in paired)
    ci_low, ci_high = bootstrap_mean_ci(
        deltas,
        iterations=bootstrap_iterations,
        seed=bootstrap_seed,
    )
    median_primary = median(deltas)
    median_recall = median(recall_deltas)
    n_questions = len(paired)

    validation_continuation_pass = (
        split == "validation"
        and median_primary > 0
        and wins > losses
        and median_recall >= RECALL_NONINFERIORITY_FLOOR
    )
    external_defined_use_pass = (
        split == "external_test"
        and n_questions >= MIN_EXTERNAL_QUESTIONS_FOR_DEFINED_USE
        and median_primary > 0
        and wins > losses
        and ci_low > 0
        and median_recall >= RECALL_NONINFERIORITY_FLOOR
    )

    summary: dict[str, Any] = {
        "analysis_type": "PREREGISTERED_PAIRED_COMMON_POOL_COMPARISON",
        "split": split,
        "candidate": candidate,
        "baseline": baseline,
        "primary_endpoint": PRIMARY_METRIC,
        "recall_guard_endpoint": RECALL_GUARD_METRIC,
        "questions": n_questions,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mean_delta_ndcg_at_20": round(mean(deltas), 6),
        "median_delta_ndcg_at_20": round(median_primary, 6),
        "bootstrap_mean_delta_ndcg_at_20_ci95": {
            "lower": round(ci_low, 6),
            "upper": round(ci_high, 6),
            "iterations": bootstrap_iterations,
            "seed": bootstrap_seed,
        },
        "mean_delta_recall_at_100": round(mean(recall_deltas), 6),
        "median_delta_recall_at_100": round(median_recall, 6),
        "recall_noninferiority_floor": RECALL_NONINFERIORITY_FLOOR,
        "minimum_external_questions_for_defined_use": (
            MIN_EXTERNAL_QUESTIONS_FOR_DEFINED_USE
        ),
        "validation_continuation_pass": validation_continuation_pass,
        "external_defined_use_pass": external_defined_use_pass,
        "verdict_boundary": (
            "A pass flag applies only to the preregistered common-pool prioritization claim. "
            "It does not establish discovery recall, evidence quality, or clinical validity."
        ),
    }
    if split == "external_test" and n_questions < MIN_EXTERNAL_QUESTIONS_FOR_DEFINED_USE:
        summary["external_evidence_status"] = "INSUFFICIENT_EVIDENCE_SAMPLE_SIZE"
    elif split == "external_test":
        summary["external_evidence_status"] = (
            "DEFINED_USE_CRITERIA_PASS"
            if external_defined_use_pass
            else "DEFINED_USE_CRITERIA_FAIL"
        )
    elif split == "validation":
        summary["validation_evidence_status"] = (
            "CONTINUATION_CRITERIA_PASS"
            if validation_continuation_pass
            else "CONTINUATION_CRITERIA_FAIL"
        )
    else:
        summary["evidence_status"] = "DEVELOPMENT_ONLY_NO_SCIENTIFIC_PROMOTION"
    return summary, paired


def write_paired(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ComparisonError("No paired question rows to write")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply the preregistered paired NutEV common-pool comparison."
    )
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument(
        "--split",
        required=True,
        choices=("development", "validation", "external_test"),
    )
    parser.add_argument("--candidate", default=DEFAULT_CANDIDATE)
    parser.add_argument("--baseline", default=DEFAULT_BASELINE)
    parser.add_argument("--summary-output", required=True, type=Path)
    parser.add_argument("--paired-output", required=True, type=Path)
    parser.add_argument(
        "--bootstrap-iterations",
        type=int,
        default=DEFAULT_BOOTSTRAP_ITERATIONS,
    )
    parser.add_argument("--bootstrap-seed", default=DEFAULT_BOOTSTRAP_SEED)
    args = parser.parse_args()

    try:
        rows = load_question_results(args.results, split=args.split)
        summary, paired = compare(
            rows,
            split=args.split,
            candidate=args.candidate,
            baseline=args.baseline,
            bootstrap_iterations=args.bootstrap_iterations,
            bootstrap_seed=args.bootstrap_seed,
        )
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        write_paired(args.paired_output, paired)
    except ComparisonError as exc:
        print(f"Benchmark comparison failure: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
