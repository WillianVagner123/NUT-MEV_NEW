from __future__ import annotations

import json
from pathlib import Path

import pytest

from nutev.review.gf02_press_decision import (
    load_gf02_gate_status,
    record_gf02_press_decision,
)


def _gate(path: Path, *, evidence_complete: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "gate": "GF-02",
                "stage": "PRE_PRESS",
                "evidence_complete": evidence_complete,
                "decision": "EVIDENCE_COMPLETE_AWAITING_HUMAN_DECISION",
                "human_decision": None,
                "human_decision_by": None,
                "blockers": [] if evidence_complete else ["noise_sample_missing"],
                "press_approval_inferred": False,
                "formal_execution_authorized": False,
                "prisma_eligible": False,
                "keep_me": "preserved",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_ready_for_press_is_explicit_audited_and_not_press_approval(tmp_path: Path) -> None:
    path = tmp_path / "gate_status.json"
    _gate(path)

    saved = record_gf02_press_decision(
        path,
        decision="ready_for_press",
        decided_by="Willian Vagner",
        rationale="PILOT and rescue-only review are sufficient for PRESS review.",
        decided_at="2026-08-16T00:10:00+00:00",
    )

    assert saved["human_decision"] == "READY_FOR_PRESS"
    assert saved["decision"] == "READY_FOR_PRESS"
    assert saved["human_decision_by"] == "Willian Vagner"
    assert saved["human_decision_at"] == "2026-08-16T00:10:00+00:00"
    assert saved["keep_me"] == "preserved"
    assert saved["press_approval_inferred"] is False
    assert saved["formal_execution_authorized"] is False
    assert saved["prisma_eligible"] is False
    assert saved["human_decision_history"] == [
        {
            "decision": "READY_FOR_PRESS",
            "decided_by": "Willian Vagner",
            "rationale": "PILOT and rescue-only review are sufficient for PRESS review.",
            "decided_at": "2026-08-16T00:10:00+00:00",
        }
    ]
    assert load_gf02_gate_status(path)["human_decision"] == "READY_FOR_PRESS"


def test_ready_for_press_requires_complete_evidence(tmp_path: Path) -> None:
    path = tmp_path / "gate_status.json"
    _gate(path, evidence_complete=False)

    with pytest.raises(ValueError, match="evidence_complete=true"):
        record_gf02_press_decision(
            path,
            decision="READY_FOR_PRESS",
            decided_by="Reviewer",
            rationale="I want to proceed.",
        )

    assert load_gf02_gate_status(path)["human_decision"] is None


def test_not_ready_can_be_recorded_without_inventing_downstream_approval(tmp_path: Path) -> None:
    path = tmp_path / "gate_status.json"
    _gate(path, evidence_complete=False)

    saved = record_gf02_press_decision(
        path,
        decision="NOT_READY_FOR_PRESS",
        decided_by="Reviewer",
        rationale="Noise remains too high; revise the search before PRESS.",
        decided_at="2026-08-16T00:11:00+00:00",
    )

    assert saved["human_decision"] == "NOT_READY_FOR_PRESS"
    assert saved["press_approval_inferred"] is False
    assert saved["formal_execution_authorized"] is False
    assert saved["prisma_eligible"] is False


def test_press_decision_requires_identity_and_rationale(tmp_path: Path) -> None:
    path = tmp_path / "gate_status.json"
    _gate(path)

    with pytest.raises(ValueError, match="identity"):
        record_gf02_press_decision(
            path,
            decision="READY_FOR_PRESS",
            decided_by="",
            rationale="Sufficient evidence.",
        )
    with pytest.raises(ValueError, match="rationale"):
        record_gf02_press_decision(
            path,
            decision="READY_FOR_PRESS",
            decided_by="Reviewer",
            rationale="",
        )


def test_ready_for_press_ui_is_routed_and_explains_both_choices() -> None:
    play = (Path("src") / "nutev" / "ui" / "article1_play_panel.py").read_text(encoding="utf-8")
    ui = (Path("src") / "nutev" / "ui" / "gf02_press_decision_workbench.py").read_text(encoding="utf-8")

    assert 'phase == "GF02_HUMAN_DECISION"' in play
    assert "render_gf02_press_decision(project_root)" in play
    assert "READY_FOR_PRESS · seguir para PRESS" in ui
    assert "NOT_READY_FOR_PRESS · ainda não seguir" in ui
    assert "não aprova o PRESS" in ui
    assert "Registrar decisão" in ui
