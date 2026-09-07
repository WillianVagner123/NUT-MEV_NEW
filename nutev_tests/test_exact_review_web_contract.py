from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def test_exact_strategy_ui_is_first_class_without_public_governance_controls() -> None:
    search = (WEB / "search.html").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'name="searchMode"' in search
    assert 'value="quick"' in search
    assert 'value="advanced"' in search
    assert 'value="exact"' in search
    assert "Busca rápida" in search
    assert "Busca avançada" in search
    assert "Estratégia exata" in search
    assert 'id="strategyId"' in search
    assert 'id="strategyVersion"' in search
    assert 'id="exactQueryBuilder"' in search
    assert 'id="runClassSelect"' not in search
    for governance_label in ("PREFLIGHT", "PILOT", "FORMAL", "SUPPLEMENTARY", "DEVELOPMENT"):
        assert f">{governance_label}<" not in search
    assert 'href="/advanced.html"' in search
    assert "PUBLIC_EXACT_RUN_CLASS='DEVELOPMENT'" in app
    assert "run_class:PUBLIC_EXACT_RUN_CLASS" in app
    assert "provider_queries" in app
    assert "Somente bases selecionadas" in app


def test_exact_strategy_backend_preserves_literal_queries_and_internal_compatibility() -> None:
    compiler = (WEB / "query_compiler.py").read_text(encoding="utf-8")
    progressive = (WEB / "progress_search.py").read_text(encoding="utf-8")
    assert '"mode": "exact_review"' in compiler
    assert '"dialect": "exact_provider_syntax"' in compiler
    assert '"FORMAL"' in compiler
    assert "A classe técnica de execução é metadado de auditoria" in compiler
    assert "não concede autorização científica" in compiler
    assert 'search_mode = "exact_review_global_exhaustive"' in progressive
    assert 'search_mode = "exact_review_bounded"' in progressive
    assert "provider_query=effective_query" in progressive
    assert '"query_plan": query_plan' in progressive


def test_pubmed_exact_runs_preserve_search_details_and_fail_audit_closed() -> None:
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
    assert ".search-mode-switch" in css
    assert ".exact-query-card" in css
    assert ".exact-meta-grid" in css
    assert ".expert-governance-note" in css
