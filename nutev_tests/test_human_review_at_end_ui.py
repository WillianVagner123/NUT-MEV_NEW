from __future__ import annotations

from pathlib import Path


def test_one_button_surface_places_human_review_after_run_controls() -> None:
    source = (Path("src") / "nutev" / "ui" / "article1_play_panel.py").read_text(encoding="utf-8")

    button_position = source.index("clicked = st.button(")
    review_center_position = source.index("_render_human_review_center(project_root, scientific)")

    assert button_position < review_center_position
    assert "Primeiro a automação. Depois, somente a revisão humana necessária." in source
    assert "REVISÃO HUMANA · DEPOIS DA AUTOMAÇÃO" in source


def test_gf02_human_review_uses_batch_editor() -> None:
    source = (Path("src") / "nutev" / "ui" / "article1_human_workbench.py").read_text(encoding="utf-8")

    assert "Revisão rescue-only · em lote" in source
    assert "st.data_editor(" in source
    assert "Salvar revisão humana completa" in source
    assert "save_rescue_only_batch(" in source
