from __future__ import annotations

import csv
import json
from pathlib import Path
import sqlite3
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "apps" / "nutev-web"
if str(WEB_ROOT) not in sys.path:
    sys.path.insert(0, str(WEB_ROOT))

from nutev_tests.test_validation_adjudication import _complete_initial_assessment, _root
from validation_adjudication import finalize_adjudication, save_adjudication
from validation_gold import build_and_validate_gold, gold_status
from validation_server import round_status


def _prepare_completed_adjudication(tmp_path: Path) -> tuple[Path, Path]:
    root = _root(tmp_path)
    tools_dir = root / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    (tools_dir / "validate_gold_standard.py").write_bytes(
        (REPO_ROOT / "tools" / "validate_gold_standard.py").read_bytes()
    )
    packet_manifest = root / "validation" / "data" / "validation_assessor_packets" / "VALIDATION_ASSESSOR_PACKETS_MANIFEST.json"
    manifest = json.loads(packet_manifest.read_text(encoding="utf-8"))
    manifest["pool_rows"] = 2
    packet_manifest.write_text(json.dumps(manifest), encoding="utf-8")

    db = tmp_path / "private" / "validation.sqlite3"
    _complete_initial_assessment(root, db)
    save_adjudication(
        {
            "question_id": "Q-V01",
            "reference_id": "ref-conflict",
            "relevance_grade": 1,
            "adjudicator_id": "human_adjudicator_01",
            "notes": "Synthetic explicit human resolution.",
        },
        repo_root=root,
        db_path=db,
    )
    finalize_adjudication(repo_root=root, db_path=db)
    return root, db


def test_gold_build_uses_locked_human_evidence_and_canonical_validator(tmp_path: Path) -> None:
    root, db = _prepare_completed_adjudication(tmp_path)

    result = build_and_validate_gold(repo_root=root, db_path=db)
    assert result["validated"] is True
    assert result["validator_status"] == "PASS"
    assert result["final_labels"] == 2
    assert result["unanimous_groups"] == 1
    assert result["conflict_groups"] == 1
    assert result["pool_assessment_coverage_fraction"] == 1.0
    assert result["pool_gold_coverage_fraction"] == 1.0
    assert round_status(repo_root=root, db_path=db)["status"] == "gold_validated"

    round_id = result["round_id"]
    output_dir = root / "project_output_reference" / "16_validation_server" / round_id
    with (output_dir / "ASSESSMENTS.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        assessments = list(csv.DictReader(handle))
    with (output_dir / "GOLD_STANDARD.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        gold = list(csv.DictReader(handle))
    assert len(assessments) == 4
    assert {row["blind_to_nutev"] for row in assessments} == {"true"}
    by_ref = {row["reference_id"]: row for row in gold}
    assert by_ref["ref-agreed"]["relevance_grade"] == "2"
    assert by_ref["ref-agreed"]["adjudication_status"] == "AGREED"
    assert by_ref["ref-conflict"]["relevance_grade"] == "1"
    assert by_ref["ref-conflict"]["adjudication_status"] == "RESOLVED"
    assert by_ref["ref-conflict"]["adjudicator_id"] == "human_adjudicator_01"

    build_manifest = json.loads((output_dir / "GOLD_BUILD_MANIFEST.json").read_text(encoding="utf-8"))
    assert build_manifest["external_test_consumed"] is False
    assert build_manifest["synthetic_labels_created"] is False
    assert build_manifest["metrics_calculated"] is False
    assert "reconstructed from the verified blinded assessor packets" in build_manifest["pool_key_provenance"]


def test_gold_build_is_blocked_before_adjudication_complete(tmp_path: Path) -> None:
    root = _root(tmp_path)
    tools_dir = root / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    (tools_dir / "validate_gold_standard.py").write_bytes(
        (REPO_ROOT / "tools" / "validate_gold_standard.py").read_bytes()
    )
    db = tmp_path / "private" / "validation.sqlite3"
    _complete_initial_assessment(root, db)
    with pytest.raises(ValueError, match="após a adjudicação completa"):
        build_and_validate_gold(repo_root=root, db_path=db)


def test_gold_build_fails_closed_if_blinding_state_is_tampered_after_lock(tmp_path: Path) -> None:
    root, db = _prepare_completed_adjudication(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE validation_assignments SET blind_to_nutev = 0 WHERE assessor_id = 'assessor_A' AND reference_id = 'ref-agreed'"
        )
        conn.commit()
    with pytest.raises(ValueError, match="cegamento"):
        build_and_validate_gold(repo_root=root, db_path=db)


def test_gold_build_fails_closed_on_manifest_pool_row_mismatch(tmp_path: Path) -> None:
    root, db = _prepare_completed_adjudication(tmp_path)
    manifest_path = root / "validation" / "data" / "validation_assessor_packets" / "VALIDATION_ASSESSOR_PACKETS_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["pool_rows"] = 999
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="manifesto declara"):
        build_and_validate_gold(repo_root=root, db_path=db)


def test_gold_status_does_not_claim_validation_before_build(tmp_path: Path) -> None:
    root, db = _prepare_completed_adjudication(tmp_path)
    status = gold_status(repo_root=root, db_path=db)
    assert status["gold_ready"] is True
    assert status["validated"] is False
    assert status["validator_status"] is None
