from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "apps" / "nutev-web"
if str(WEB_ROOT) not in sys.path:
    sys.path.insert(0, str(WEB_ROOT))

from nutev_tests.test_validation_metrics_service import (
    _gold_validated_root,
    _write_rankings,
)
from validation_decision import decision_status, lock_validation_decision
from validation_metrics import run_validation_metrics
from validation_server import round_status


def _write_fail_rankings(root: Path) -> None:
    audit_dir = root / "validation" / "data" / "validation_coordinator_audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    rankings = audit_dir / "BENCHMARK_RANKINGS.csv"
    fields = ["question_id", "split", "system", "rank", "reference_id", "system_score"]
    rows = [
        {"question_id":"Q-V01", "split":"validation", "system":"nutev_full", "rank":1, "reference_id":"ref-conflict", "system_score":"2"},
        {"question_id":"Q-V01", "split":"validation", "system":"nutev_full", "rank":2, "reference_id":"ref-agreed", "system_score":"1"},
        {"question_id":"Q-V01", "split":"validation", "system":"lexical_baseline", "rank":1, "reference_id":"ref-agreed", "system_score":"2"},
        {"question_id":"Q-V01", "split":"validation", "system":"lexical_baseline", "rank":2, "reference_id":"ref-conflict", "system_score":"1"},
    ]
    with rankings.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    questions = root / "validation" / "data" / "QUESTIONS.csv"
    manifest = {
        "benchmark_type": "COMMON_POOL_PRIORITIZATION",
        "candidate_runtime_sha": "6aa7a5fe6009776e611ca3e1506486606b05f4f6",
        "frozen_runtime_sha_required": "6aa7a5fe6009776e611ca3e1506486606b05f4f6",
        "label_blind_build": True,
        "gold_standard_consumed": False,
        "questions_sha256": sha256(questions.read_bytes()).hexdigest(),
        "ranking_sha256": sha256(rankings.read_bytes()).hexdigest(),
    }
    (audit_dir / "BENCHMARK_RANKINGS_MANIFEST.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )


def _metrics_complete(tmp_path: Path, *, passing: bool) -> tuple[Path, Path, dict[str, object]]:
    root, db = _gold_validated_root(tmp_path)
    if passing:
        _write_rankings(root)
    else:
        _write_fail_rankings(root)
    metrics = run_validation_metrics(repo_root=root, db_path=db)
    assert metrics["round_status"] == "validation_metrics_complete"
    return root, db, metrics


def test_pass_gate_locks_continue_without_releasing_external(tmp_path: Path) -> None:
    root, db, metrics = _metrics_complete(tmp_path, passing=True)
    assert metrics["validation_continuation_pass"] is True

    locked = lock_validation_decision(repo_root=root, db_path=db)
    assert locked["locked"] is True
    assert locked["decision"] == "CONTINUE_TO_EXTERNAL"
    assert locked["validation_evidence_status"] == "CONTINUATION_CRITERIA_PASS"
    assert locked["external_test_released"] is False
    assert round_status(repo_root=root, db_path=db)["status"] == "validation_decision_continue"

    decision_path = root / "project_output_reference" / "16_validation_server" / locked["round_id"] / "VALIDATION_DECISION.json"
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    assert decision["external_test_released"] is False
    assert decision["external_test_labels_consumed"] is False
    assert decision["external_test_metrics_calculated"] is False
    assert decision["automatic_external_release"] is False
    assert decision["candidate_runtime_sha"] == "6aa7a5fe6009776e611ca3e1506486606b05f4f6"


def test_fail_gate_locks_stop_at_b_without_external_release(tmp_path: Path) -> None:
    root, db, metrics = _metrics_complete(tmp_path, passing=False)
    assert metrics["validation_continuation_pass"] is False
    assert metrics["validation_evidence_status"] == "CONTINUATION_CRITERIA_FAIL"

    locked = lock_validation_decision(repo_root=root, db_path=db)
    assert locked["decision"] == "STOP_AT_B"
    assert locked["external_test_released"] is False
    assert round_status(repo_root=root, db_path=db)["status"] == "validation_decision_stop"


def test_decision_lock_is_blocked_before_metrics_complete(tmp_path: Path) -> None:
    root, db = _gold_validated_root(tmp_path)
    with pytest.raises(ValueError, match="validation_metrics_complete"):
        lock_validation_decision(repo_root=root, db_path=db)


def test_decision_lock_detects_post_metric_comparison_tampering(tmp_path: Path) -> None:
    root, db, metrics = _metrics_complete(tmp_path, passing=True)
    output_dir = root / "project_output_reference" / "16_validation_server" / metrics["round_id"]
    comparison_path = output_dir / "VALIDATION_COMPARISON.json"
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    comparison["wins"] = 999
    comparison_path.write_text(json.dumps(comparison), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 de VALIDATION_COMPARISON.json"):
        lock_validation_decision(repo_root=root, db_path=db)


def test_decision_lock_is_idempotent_after_lock(tmp_path: Path) -> None:
    root, db, _ = _metrics_complete(tmp_path, passing=True)
    first = lock_validation_decision(repo_root=root, db_path=db)
    second = lock_validation_decision(repo_root=root, db_path=db)
    assert second["decision"] == first["decision"]
    assert second["locked_at"] == first["locked_at"]
    status = decision_status(repo_root=root, db_path=db)
    assert status["locked"] is True
