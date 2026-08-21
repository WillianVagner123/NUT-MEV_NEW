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

from nutev_tests.test_validation_gold import _prepare_completed_adjudication
from validation_gold import build_and_validate_gold
from validation_metrics import metrics_status, run_validation_metrics
from validation_server import round_status


def _copy_tools(root: Path) -> None:
    tools = root / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    for name in (
        "validate_gold_standard.py",
        "evaluate_scientific_validation.py",
        "compare_scientific_benchmark.py",
    ):
        (tools / name).write_bytes((REPO_ROOT / "tools" / name).read_bytes())


def _write_rankings(root: Path, *, gold_consumed: bool = False) -> None:
    audit_dir = root / "validation" / "data" / "validation_coordinator_audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    rankings = audit_dir / "BENCHMARK_RANKINGS.csv"
    fields = ["question_id", "split", "system", "rank", "reference_id", "system_score"]
    rows = [
        {"question_id":"Q-V01", "split":"validation", "system":"nutev_full", "rank":1, "reference_id":"ref-agreed", "system_score":"2"},
        {"question_id":"Q-V01", "split":"validation", "system":"nutev_full", "rank":2, "reference_id":"ref-conflict", "system_score":"1"},
        {"question_id":"Q-V01", "split":"validation", "system":"lexical_baseline", "rank":1, "reference_id":"ref-conflict", "system_score":"2"},
        {"question_id":"Q-V01", "split":"validation", "system":"lexical_baseline", "rank":2, "reference_id":"ref-agreed", "system_score":"1"},
        {"question_id":"Q-E01", "split":"external_test", "system":"nutev_full", "rank":1, "reference_id":"sealed-ref", "system_score":"9"},
        {"question_id":"Q-E01", "split":"external_test", "system":"lexical_baseline", "rank":1, "reference_id":"sealed-ref", "system_score":"9"},
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
        "gold_standard_consumed": gold_consumed,
        "questions_sha256": sha256(questions.read_bytes()).hexdigest(),
        "ranking_sha256": sha256(rankings.read_bytes()).hexdigest(),
    }
    (audit_dir / "BENCHMARK_RANKINGS_MANIFEST.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )


def _gold_validated_root(tmp_path: Path) -> tuple[Path, Path]:
    root, db = _prepare_completed_adjudication(tmp_path)
    _copy_tools(root)
    build_and_validate_gold(repo_root=root, db_path=db)
    assert round_status(repo_root=root, db_path=db)["status"] == "gold_validated"
    return root, db


def test_validation_metrics_run_only_after_gold_and_use_preregistered_pair(tmp_path: Path) -> None:
    root, db = _gold_validated_root(tmp_path)
    _write_rankings(root)

    result = run_validation_metrics(repo_root=root, db_path=db)
    assert result["completed"] is True
    assert result["round_status"] == "validation_metrics_complete"
    assert result["validation_evidence_status"] == "CONTINUATION_CRITERIA_PASS"
    assert result["validation_continuation_pass"] is True
    assert result["wins"] == 1
    assert result["losses"] == 0
    assert result["external_test_released"] is False

    output_dir = root / "project_output_reference" / "16_validation_server" / result["round_id"]
    manifest = json.loads((output_dir / "VALIDATION_METRICS_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["split_evaluated"] == "validation"
    assert manifest["systems"] == ["nutev_full", "lexical_baseline"]
    assert manifest["required_judged_through"] == 100
    assert manifest["external_test_labels_consumed"] is False
    assert manifest["external_test_metrics_calculated"] is False
    assert manifest["external_test_released"] is False
    assert manifest["decision_locked"] is False


def test_metrics_status_waits_for_private_rankings_source(tmp_path: Path) -> None:
    root, db = _gold_validated_root(tmp_path)
    status = metrics_status(repo_root=root, db_path=db)
    assert status["ready"] is False
    assert status["completed"] is False
    assert status["source_ready"] is False
    assert "Rankings label-blind" in status["source_message"]


def test_metrics_reject_rankings_that_consumed_gold(tmp_path: Path) -> None:
    root, db = _gold_validated_root(tmp_path)
    _write_rankings(root, gold_consumed=True)
    with pytest.raises(ValueError, match="consumiu gold standard"):
        run_validation_metrics(repo_root=root, db_path=db)


def test_metrics_are_blocked_before_gold_validated(tmp_path: Path) -> None:
    root, db = _prepare_completed_adjudication(tmp_path)
    _copy_tools(root)
    _write_rankings(root)
    with pytest.raises(ValueError, match="gold_validated"):
        run_validation_metrics(repo_root=root, db_path=db)
