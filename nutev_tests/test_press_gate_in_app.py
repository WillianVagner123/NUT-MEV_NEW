from __future__ import annotations

import json
from pathlib import Path

import pytest

from nutev.review.press_gate import load_press_gate, press_gate_path, record_press_gate


def test_press_gate_requires_real_human_evidence(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="real reviewer identity"):
        record_press_gate(
            tmp_path,
            review_status="APPROVED",
            reviewer="",
            review_date="2026-08-15",
            evidence_reference="press-review.pdf",
        )

    with pytest.raises(ValueError, match="real evidence reference"):
        record_press_gate(
            tmp_path,
            review_status="APPROVED",
            reviewer="Human Reviewer",
            review_date="2026-08-15",
            evidence_reference="",
        )


def test_approved_press_is_human_and_does_not_authorize_downstream_science(tmp_path: Path) -> None:
    saved = record_press_gate(
        tmp_path,
        review_status="APPROVED",
        reviewer="Human Reviewer",
        review_date="2026-08-15",
        evidence_reference="archive/press-review.pdf",
        notes="PRESS completed outside the Engine.",
    )

    assert saved["review_status"] == "APPROVED"
    assert saved["decision_source"] == "HUMAN"
    assert saved["human_validated"] is True
    assert saved["press_approval_inferred"] is False
    assert saved["freeze_authorized"] is False
    assert saved["formal_execution_authorized"] is False
    assert saved["prisma_eligible"] is False
    assert press_gate_path(tmp_path).is_file()
    assert load_press_gate(tmp_path)["reviewer"] == "Human Reviewer"


def test_press_history_is_append_only(tmp_path: Path) -> None:
    record_press_gate(
        tmp_path,
        review_status="CHANGES_REQUIRED",
        reviewer="Human Reviewer",
        review_date="2026-08-14",
        evidence_reference="archive/press-v1.pdf",
        requested_changes="Clarify the proximity operator translation.",
    )
    saved = record_press_gate(
        tmp_path,
        review_status="APPROVED",
        reviewer="Human Reviewer",
        review_date="2026-08-15",
        evidence_reference="archive/press-v2.pdf",
        requested_changes="Clarify the proximity operator translation.",
        incorporated_changes="Translation wording corrected and archived.",
    )

    assert [item["review_status"] for item in saved["history"]] == ["CHANGES_REQUIRED", "APPROVED"]
    on_disk = json.loads(press_gate_path(tmp_path).read_text(encoding="utf-8"))
    assert len(on_disk["history"]) == 2


def test_approved_press_with_requested_changes_requires_incorporation_record(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires a record"):
        record_press_gate(
            tmp_path,
            review_status="APPROVED",
            reviewer="Human Reviewer",
            review_date="2026-08-15",
            evidence_reference="archive/press.pdf",
            requested_changes="Revise wording.",
            incorporated_changes="",
        )


def test_press_ui_routes_gate_to_form_and_disables_fake_continue() -> None:
    source = Path("src/nutev/ui/article1_play_panel.py").read_text(encoding="utf-8")
    workbench = Path("src/nutev/ui/press_gate_workbench.py").read_text(encoding="utf-8")

    assert 'elif phase == "GF03_PRESS"' in source
    assert "render_press_gate_workbench(project_root)" in source
    assert 'press_pending = phase == "GF03_PRESS"' in source
    assert '"PRESS PENDENTE — PREENCHA ABAIXO"' in source
    assert 'disabled=phase == "COMPLETE" or press_pending' in source
    assert "record_press_gate(" in workbench
    assert "software não inventa aprovação" in workbench
