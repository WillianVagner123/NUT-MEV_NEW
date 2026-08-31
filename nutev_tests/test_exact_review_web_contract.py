from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def test_exact_strategy_ui_is_first_class() -> None:
    search = (WEB / "search.html").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'value="exact"' in search
    assert 'id="strategyId"' in search
    assert 'id="strategyVersion"' in search
    assert 'id="runClassSelect"' in search
    assert 'id="exactQueryBuilder"' in search
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


def test_pubmed_review_runs_preserve_search_details_and_fail_audit_closed() -> None:
    progressive = (WEB / "progress_search.py").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")
    details = (WEB / "pubmed_search_details.py").read_text(encoding="utf-8")
    assert "collect_pubmed_search_details" in progressive
    assert 'status_item["search_details"]' in progressive
    assert '"COMPLETE_WITH_AUDIT_GAPS"' in progressive
    assert '"audit_gaps": audit_gaps' in progressive
    assert "querytranslation" in details
    assert "warninglist" in details
    assert "errorlist" in details
    assert "PubMed Search Details" in app
    assert "WARNINGS PRESENTES" in app
    assert "GATE DE AUDITORIA NÃO FECHOU" in app


def test_exact_strategy_styles_are_loaded() -> None:
    search = (WEB / "search.html").read_text(encoding="utf-8")
    css = (WEB / "exact-strategy.css").read_text(encoding="utf-8")
    assert "exact-strategy.css" in search
    assert ".exact-query-card" in css
    assert ".exact-meta-grid" in css
