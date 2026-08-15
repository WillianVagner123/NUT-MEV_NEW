"""Smoke tests for the canonical Article 1 execution page."""
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


def test_execution_page_has_no_legacy_free_search_layout():
    at = _execution_app()
    assert not at.exception
    assert len(at.text_area) == 0
    assert all("O que você deseja pesquisar?" not in item.value for item in at.markdown)
    assert any("RODAR PILOT GF-02" in button.label for button in at.button)


def test_execution_page_surfaces_canonical_strategy_read_only():
    at = _execution_app()
    assert not at.exception
    metric_values = [metric.value for metric in at.metric]
    assert any("v0.5" in str(value) for value in metric_values)
    assert "PILOT" in metric_values
    assert "Não" in metric_values
