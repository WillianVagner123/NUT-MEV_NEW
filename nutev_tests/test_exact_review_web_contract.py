from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def test_exact_strategy_ui_is_first_class() -> None:
    index = (WEB / "index.html").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'value="exact"' in index
    assert 'id="strategyId"' in index
    assert 'id="strategyVersion"' in index
    assert 'id="runClassSelect"' in index
    assert 'id="exactQueryBuilder"' in index
    assert "strategy?.mode==='exact'" in app
    assert "provider_queries" in app
    assert "Somente bases selecionadas" in app


def test_exact_strategy_backend_preserves_literal_queries() -> None:
    compiler = (WEB / "query_compiler.py").read_text(encoding="utf-8")
    progressive = (WEB / "progress_search.py").read_text(encoding="utf-8")
    assert '"mode": "exact_review"' in compiler
    assert '"dialect": "exact_provider_syntax"' in compiler
    assert "FORMAL é apenas uma classificação de execução" in compiler
    assert 'search_mode = "exact_review_global_exhaustive"' in progressive
    assert 'search_mode = "exact_review_bounded"' in progressive
    assert "provider_query=effective_query" in progressive
    assert '"query_plan": query_plan' in progressive


def test_exact_strategy_styles_are_loaded() -> None:
    index = (WEB / "index.html").read_text(encoding="utf-8")
    css = (WEB / "exact-strategy.css").read_text(encoding="utf-8")
    assert "exact-strategy.css" in index
    assert ".exact-query-card" in css
    assert ".exact-meta-grid" in css
