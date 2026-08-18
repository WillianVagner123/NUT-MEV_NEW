from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "compare_scientific_benchmark.py"
SPEC = importlib.util.spec_from_file_location("compare_scientific_benchmark", MODULE_PATH)
assert SPEC and SPEC.loader
comparison = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = comparison
SPEC.loader.exec_module(comparison)


def _row(ndcg: float, recall: float, *, coverage: float = 1.0) -> dict[str, str]:
    return {
        "ndcg_at_20": str(ndcg),
        "recall_at_100": str(recall),
        "judgment_coverage_at_20": str(coverage),
        "judgment_coverage_at_100": str(coverage),
    }


def _paired_rows(
    candidate_values: list[tuple[float, float]],
    baseline_values: list[tuple[float, float]],
) -> dict[tuple[str, str], dict[str, str]]:
    rows: dict[tuple[str, str], dict[str, str]] = {}
    for index, (candidate_value, baseline_value) in enumerate(
        zip(candidate_values, baseline_values, strict=True), start=1
    ):
        question = f"q{index}"
        rows[(question, "nutev_full")] = _row(*candidate_value)
        rows[(question, "lexical_baseline")] = _row(*baseline_value)
    return rows


def test_validation_continuation_passes_when_preregistered_rules_pass() -> None:
    rows = _paired_rows(
        [(0.8, 0.9), (0.7, 0.8), (0.6, 0.75)],
        [(0.5, 0.9), (0.6, 0.8), (0.55, 0.76)],
    )
    summary, paired = comparison.compare(
        rows,
        split="validation",
        bootstrap_iterations=500,
        bootstrap_seed="fixed",
    )
    assert summary["validation_continuation_pass"] is True
    assert summary["wins"] == 3
    assert summary["losses"] == 0
    assert len(paired) == 3


def test_validation_fails_when_recall_guard_is_breached() -> None:
    rows = _paired_rows(
        [(0.8, 0.70), (0.8, 0.70), (0.8, 0.70)],
        [(0.5, 0.80), (0.5, 0.80), (0.5, 0.80)],
    )
    summary, _ = comparison.compare(
        rows,
        split="validation",
        bootstrap_iterations=500,
        bootstrap_seed="fixed",
    )
    assert summary["median_delta_ndcg_at_20"] > 0
    assert summary["median_delta_recall_at_100"] < -0.05
    assert summary["validation_continuation_pass"] is False


def test_external_test_cannot_pass_with_too_few_questions() -> None:
    rows = _paired_rows(
        [(0.9, 0.9)] * 5,
        [(0.5, 0.9)] * 5,
    )
    summary, _ = comparison.compare(
        rows,
        split="external_test",
        bootstrap_iterations=500,
        bootstrap_seed="fixed",
    )
    assert summary["external_defined_use_pass"] is False
    assert summary["external_evidence_status"] == "INSUFFICIENT_EVIDENCE_SAMPLE_SIZE"


def test_external_test_can_pass_when_all_preregistered_rules_pass() -> None:
    count = comparison.MIN_EXTERNAL_QUESTIONS_FOR_DEFINED_USE
    rows = _paired_rows(
        [(0.85, 0.90)] * count,
        [(0.55, 0.90)] * count,
    )
    summary, _ = comparison.compare(
        rows,
        split="external_test",
        bootstrap_iterations=500,
        bootstrap_seed="fixed",
    )
    assert summary["wins"] == count
    assert summary["bootstrap_mean_delta_ndcg_at_20_ci95"]["lower"] > 0
    assert summary["external_defined_use_pass"] is True


def test_incomplete_judgment_coverage_fails_closed() -> None:
    rows = {
        ("q1", "nutev_full"): _row(0.8, 0.9, coverage=0.99),
        ("q1", "lexical_baseline"): _row(0.5, 0.9),
    }
    with pytest.raises(comparison.ComparisonError, match="complete judgment coverage"):
        comparison.compare(
            rows,
            split="validation",
            bootstrap_iterations=500,
        )


def test_missing_preregistered_baseline_fails_closed() -> None:
    rows = {( "q1", "nutev_full"): _row(0.8, 0.9)}
    with pytest.raises(comparison.ComparisonError, match="Missing preregistered system"):
        comparison.compare(
            rows,
            split="validation",
            bootstrap_iterations=500,
        )


def test_bootstrap_is_deterministic_for_fixed_seed() -> None:
    values = [0.1, 0.2, 0.3, 0.4]
    first = comparison.bootstrap_mean_ci(values, iterations=500, seed="fixed")
    second = comparison.bootstrap_mean_ci(values, iterations=500, seed="fixed")
    assert first == second
