"""Smoke tests for the one-button canonical Article 1 execution page."""
from __future__ import annotations

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

_DASHBOARD = "src/nutev/ui/dashboard.py"


def _execution_app() -> AppTest:
    at = AppTest.from_file(_DASHBOARD, default_timeout=30)
    at.run()
    at.sidebar.radio[0].set_value("Execução científica").run()
    return at


def test_execution_page_has_only_one_operational_button_and_no_legacy_search():
    at = _execution_app()
    assert not at.exception
    assert len(at.text_area) == 0
    assert all("O que você deseja pesquisar?" not in item.value for item in at.markdown)
    operational = [button for button in at.button if button.label in {"▶ RODAR TUDO", "▶ CONTINUAR"}]
    assert len(operational) == 1


def test_execution_page_explains_checkpoint_resume_without_strategy_metrics():
    at = _execution_app()
    assert not at.exception
    rendered = "\n".join(item.value for item in at.markdown)
    assert "Um botão. O Engine cuida do resto." in rendered
    assert "checkpoints" in rendered.lower()
    assert len(at.metric) == 0
