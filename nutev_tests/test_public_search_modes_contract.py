from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def test_public_search_has_three_clear_modes() -> None:
    search = (WEB / "search.html").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert 'name="searchMode"' in search
    assert 'value="quick" checked' in search
    assert 'value="advanced"' in search
    assert 'value="exact"' in search
    assert "Busca rápida" in search
    assert "Busca avançada" in search
    assert "Estratégia exata" in search
    assert "function toggleSearchMode()" in app
    assert "mode==='quick'" in app
    assert "mode==='advanced'" in app
    assert "mode==='exact'" in app


def test_public_search_does_not_expose_review_governance_run_classes() -> None:
    search = (WEB / "search.html").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert "revisão" not in search.casefold()
    assert 'id="runClassSelect"' not in search
    assert 'id="structuredReviewToggle"' not in search
    for token in ("PREFLIGHT", "PILOT", "FORMAL", "SUPPLEMENTARY", "PRISMA", "PRESS"):
        assert token not in search
    assert "plan.run_class" not in app
    assert "PUBLIC_EXACT_RUN_CLASS='DEVELOPMENT'" in app
    assert "run_class:PUBLIC_EXACT_RUN_CLASS" in app


def test_backend_internal_modes_remain_compatible_but_are_not_product_labels() -> None:
    compiler = (WEB / "query_compiler.py").read_text(encoding="utf-8")
    progressive = (WEB / "progress_search.py").read_text(encoding="utf-8")

    assert '"mode": "structured_review"' in compiler
    assert '"mode": "exact_review"' in compiler
    assert '"FORMAL"' in compiler
    assert 'search_mode = "structured_review_global_exhaustive"' in progressive
    assert 'search_mode = "exact_review_global_exhaustive"' in progressive
    assert "A classe técnica de execução é metadado de auditoria" in compiler
    assert "não concede autorização científica" in compiler
