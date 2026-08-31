from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_dashboard_wires_interactive_filter_layer() -> None:
    home = read("index.html")
    script = read("dashboard-interactive.js")

    assert 'href="./dashboard-interactive.css"' in home
    assert 'src="./dashboard-interactive.js"' in home
    assert "ARTICLE_SUMMARIES.jsonl" in script
    assert "Filtros analíticos locais" in script
    assert "não alteram elegibilidade" in script


def test_interactive_dashboard_does_not_hardcode_production_counts() -> None:
    script = read("dashboard-interactive.js")

    for forbidden in ("33067", "33839", "41139", "662", "504", "316", "85"):
        assert forbidden not in script

    assert "filterArticles" in script
    assert "syncUrl" in script
    assert "history.replaceState" in script


def test_drilldown_targets_use_url_state() -> None:
    dashboard = read("dashboard-interactive.js")
    corpus = read("corpus-url-state.js")
    evidence = read("evidence.js")
    review = read("review-routes.js")
    articles_html = read("articles.html")

    assert "/articles.html" in dashboard
    assert "/evidence.html?domain=" in dashboard
    assert "/review-routes.html?route=B-NORM" in dashboard
    assert "document_class" in corpus
    assert "source_provider" in corpus
    assert "full_text_status" in corpus
    assert articles_html.index('src="./corpus-url-state.js"') < articles_html.index('src="./articles.js"')
    assert "get('domain')" in evidence
    assert "params.set('domain'" in evidence
    assert "get('route')" in review
    assert "params.set('route'" in review


def test_timeline_filter_is_dashboard_only_not_false_corpus_query() -> None:
    script = read("dashboard-interactive.js")

    assert "data-filter-year" in script
    assert "setFilter('year'" in script
    assert "params.set('year'" not in script.split("function corpusHref", 1)[1].split("function renderClickableBars", 1)[0]


def test_route_and_fulltext_drilldowns_keep_scientific_guardrails() -> None:
    script = read("dashboard-interactive.js")

    assert "Rota não equivale a inclusão" in script
    assert "Full-text retrieval não equivale a elegibilidade" in script
    assert "volume não representa força de evidência" in script
