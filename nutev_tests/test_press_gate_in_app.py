from __future__ import annotations

import json
from pathlib import Path

import pytest

from nutev.review.press_gate import load_press_gate, record_press_gate


def test_press_gate_requires_real_human_evidence(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="reviewer"):
        record_press_gate(
            tmp_path,
            review_status="APPROVED",
            reviewer="",
            review_date="2026-08-15",
            evidence_reference="archive/press.pdf",
        )
    with pytest.raises(ValueError, match="evidence"):
        record_press_gate(
            tmp_path,
            review_status="APPROVED",
            reviewer="Human Reviewer",
            review_date="2026-08-15",
            evidence_reference="",
        )


def test_press_gate_is_human_only_append_only_and_does_not_authorize_downstream(tmp_path: Path) -> None:
    first = record_press_gate(
        tmp_path,
        review_status="CHANGES_REQUIRED",
        reviewer="Human Reviewer",
        review_date="2026-08-14",
        evidence_reference="archive/press-v1.pdf",
        requested_changes="Revise wording.",
        incorporated_changes="",
        notes="Round 1",
    )
    assert first["review_status"] == "CHANGES_REQUIRED"
    assert first["decision_source"] == "HUMAN"
    assert first["human_validated"] is True
    assert first["freeze_authorized"] is False
    assert first["formal_execution_authorized"] is False
    assert first["prisma_eligible"] is False
    assert len(first["history"]) == 1

    second = record_press_gate(
        tmp_path,
        review_status="APPROVED",
        reviewer="Human Reviewer",
        review_date="2026-08-15",
        evidence_reference="archive/press-v2.pdf",
        requested_changes="Revise wording.",
        incorporated_changes="Wording revised and archived.",
        notes="Round 2",
    )
    assert second["review_status"] == "APPROVED"
    assert len(second["history"]) == 2
    assert second["history"][0]["review_status"] == "CHANGES_REQUIRED"
    assert second["history"][1]["review_status"] == "APPROVED"
    assert second["formal_execution_authorized"] is False
    assert second["prisma_eligible"] is False

    path = tmp_path / "07_logs" / "scientific_gates" / "press.json"
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == second
    assert load_press_gate(tmp_path) == second


def test_press_gate_requires_incorporated_changes_when_approved(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="incorporated_changes"):
        record_press_gate(
            tmp_path,
            review_status="APPROVED",
            reviewer="Human Reviewer",
            review_date="2026-08-15",
            evidence_reference="archive/press.pdf",
            requested_changes="Revise wording.",
            incorporated_changes="",
        )


def test_press_ui_routes_real_collection_before_press_form() -> None:
    source = Path("src/nutev/ui/article1_play_panel.py").read_text(encoding="utf-8")
    workbench = Path("src/nutev/ui/press_gate_workbench.py").read_text(encoding="utf-8")

    assert 'elif phase == "GF03_PRESS"' in source
    assert 'press_pending = phase == "GF03_PRESS"' in source
    assert "▶ BUSCAR E ORGANIZAR DADOS REAIS AGORA" in source
    assert "run_pre_review_collection" in source
    assert 'phase == "GF03_PRESS" and not bool(pre_review_collection_status(project_root).get("complete"))' in source
    assert "render_press_gate_workbench(project_root)" in source
    assert "record_press_gate(" in workbench
    assert "software não inventa aprovação" in workbench
