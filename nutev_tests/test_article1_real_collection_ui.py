from __future__ import annotations

from pathlib import Path


def test_press_ui_runs_real_collection_before_showing_human_press_form() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "nutev"
        / "ui"
        / "article1_play_panel.py"
    ).read_text(encoding="utf-8")

    assert "▶ BUSCAR E ORGANIZAR DADOS REAIS AGORA" in source
    assert "run_pre_review_collection" in source
    assert "REAL" in source
    assert "NÃO-FORMAL" in source
    assert "não entram no PRISMA até FREEZE/FORMAL" in source
    assert 'phase == "GF03_PRESS" and not bool(pre_review_collection_status(project_root).get("complete"))' in source
    assert "render_press_gate_workbench(project_root)" in source
    assert "COLETA REAL CONCLUÍDA — PRESS ABAIXO" in source
