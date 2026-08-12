from __future__ import annotations

import json
from pathlib import Path

from nutev.export.logs import assess_scientific_readiness, write_run_summary


def test_scientific_readiness_does_not_infer_manuscript_approval():
    result = assess_scientific_readiness(
        {
            "run_status": "completed",
            "providers_failed": 0,
            "providers_unsupported_by_workstream": {},
            "coverage_loss": {"unrecoverable": 0},
        }
    )
    assert result["execution_status"] == "completed"
    assert result["scientific_readiness"] == "computationally_ready_for_human_review"
    assert result["scientific_readiness_blockers"] == []
    assert result["human_review_complete"] is False


def test_scientific_readiness_blocks_downstream_errors_and_provider_failures():
    result = assess_scientific_readiness(
        {
            "run_status": "partial",
            "providers_failed": 1,
            "providers_unsupported_by_workstream": {"legacy_label": ["provider_x"]},
            "coverage_loss": {"unrecoverable": 2},
            "article1_report_error": "simulated failure",
        }
    )
    assert result["scientific_readiness"] == "blocked"
    assert "execution_status=partial" in result["scientific_readiness_blockers"]
    assert "provider_failures_present" in result["scientific_readiness_blockers"]
    assert "declared_providers_not_executed" in result["scientific_readiness_blockers"]
    assert "unrecoverable_coverage_loss" in result["scientific_readiness_blockers"]
    assert "article1_report_error" in result["scientific_readiness_blockers"]


def test_manuscript_ready_requires_explicit_human_and_manuscript_gates():
    result = assess_scientific_readiness(
        {
            "run_status": "completed",
            "providers_failed": 0,
            "providers_unsupported_by_workstream": {},
            "coverage_loss": {"unrecoverable": 0},
            "human_review_complete": True,
            "manuscript_gates_complete": True,
        }
    )
    assert result["scientific_readiness"] == "manuscript_ready"


def test_write_run_summary_mutates_returned_summary_contract(tmp_path: Path):
    summary = {"run_status": "completed"}
    path = tmp_path / "run_summary.json"
    write_run_summary(path, summary)
    assert summary["execution_status"] == "completed"
    assert summary["scientific_readiness"] == "computationally_ready_for_human_review"
    assert json.loads(path.read_text(encoding="utf-8"))["scientific_readiness"] == (
        "computationally_ready_for_human_review"
    )
