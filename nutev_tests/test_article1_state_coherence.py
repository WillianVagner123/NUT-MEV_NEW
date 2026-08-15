from __future__ import annotations

import csv
import json
from pathlib import Path

from nutev.search.article1_scientific_status import (
    derive_article1_scientific_status,
    scientific_execution_card,
)
from nutev.search.gf02_prepress_gate import evaluate_gf02_prepress_gate


def _strategy() -> dict:
    return {"search_type": "PILOT", "prisma_eligible": False}


def test_d096_scopus_wos_are_not_prepress_blockers() -> None:
    status = evaluate_gf02_prepress_gate(
        strategy_version=_strategy(),
        pubmed_recall={
            "unresolved_sentinel_ids": [],
            "recovered_sentinel_ids": ["NORM-035", "NORM-063"],
            "missing_resolved_sentinel_ids": [],
        },
        noise_summary={"sample_size": 20, "estimated_precision": 0.5},
        human_decision="READY_FOR_PRESS",
        human_decision_by="reviewer",
    )
    assert status["evidence_complete"] is True
    assert status["decision"] == "READY_FOR_PRESS"
    assert status["scopus_wos_pre_press_blocker"] is False
    assert status["methodology_decision"] == "D-096"
    assert status["formal_execution_authorized"] is False
    assert status["prisma_eligible"] is False


def test_scientific_status_reports_current_phase_not_all_downstream_gates(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    project = tmp_path / "project"
    (repo / "config").mkdir(parents=True)
    (repo / "config" / "gf02_pubmed_candidates.json").write_text(
        json.dumps(
            {
                "current_candidate": "v0.5",
                "candidate_status": "PROVISIONAL_PILOT_PENDING_NOISE_REVIEW",
                "search_type": "PILOT",
                "prisma_eligible": False,
                "formal_execution_authorized": False,
            }
        ),
        encoding="utf-8",
    )
    status = derive_article1_scientific_status(repo, project)
    assert status["article1_current_phase"] == "GF02_PUBMED_PILOT"
    assert status["scopus_wos"]["pre_press_blocker"] is False
    assert status["freeze"]["downstream"] is True
    assert "v0.5" in scientific_execution_card(status)["body"]


def test_status_advances_to_human_decision_after_pilot_and_noise_review(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    project = tmp_path / "project"
    (repo / "config").mkdir(parents=True)
    (repo / "config" / "gf02_pubmed_candidates.json").write_text(
        json.dumps(
            {
                "current_candidate": "v0.5",
                "candidate_status": "PROVISIONAL_PILOT_PENDING_NOISE_REVIEW",
                "search_type": "PILOT",
                "prisma_eligible": False,
                "formal_execution_authorized": False,
            }
        ),
        encoding="utf-8",
    )
    run_dir = project / "07_logs" / "gf02" / "pubmed" / "run1"
    run_dir.mkdir(parents=True)
    sample = run_dir / "rescue_only_sample_v0_5.csv"
    with sample.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["classification", "reviewer"])
        writer.writeheader()
        writer.writerow({"classification": "irrelevant", "reviewer": "R1"})
    (run_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "candidate_version": "v0.5",
                "status": "SUCCEEDED",
                "search_type": "PILOT",
                "prisma_eligible": False,
                "rescue_only_sample": str(sample),
            }
        ),
        encoding="utf-8",
    )
    status = derive_article1_scientific_status(repo, project)
    assert status["article1_current_phase"] == "GF02_HUMAN_DECISION"
    assert status["blockers_to_press"] == ["gf02_human_ready_for_press_decision_missing"]
