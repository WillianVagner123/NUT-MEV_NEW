from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_dashboard_is_home_and_search_is_separate_workspace() -> None:
    home = read("index.html")
    search = read("search.html")

    assert "Scientific Overview" in home
    assert 'src="./dashboard.js"' in home
    assert 'src="./app.js"' not in home
    assert 'href="/search.html"' in home

    assert "Search Workspace" in search
    assert 'src="./app.js"' in search
    assert 'href="/"' in search


def test_dashboard_has_no_production_count_literals() -> None:
    script = read("dashboard.js")

    # Production counts must come from verified runtime/context inputs, never UI constants.
    for forbidden in ("33067", "33839", "41139", "662", "504", "316", "85"):
        assert forbidden not in script

    assert "/api/articles/status" in script
    assert "/agent-context/article1/SEARCH_STATE.json" in script
    assert "/agent-context/article1/ARTICLE_SUMMARIES.jsonl" in script
    assert "/api/radar" in script


def test_evidence_and_review_pages_use_rank_blind_agent_context() -> None:
    evidence = read("evidence.js")
    review = read("review-routes.js")

    for script in (evidence, review):
        assert "/agent-context/article1/ARTICLE_SUMMARIES.jsonl" in script
        assert "reference_rank" not in script
        assert "reference_score" not in script
        assert "machine_relevance_score" not in script
        assert "verbatim_excerpt" not in script
        assert "/api/articles/" not in script


def test_visible_guardrails_preserve_scientific_meaning() -> None:
    home = read("index.html")
    review = read("review-routes.html")
    evidence = read("evidence.html")

    assert "Discovery ≠ busca formal" in home
    assert "rota ≠ inclusão" in home
    assert "Não produzem inclusão" in review
    assert "Não equivalem a decisão de elegibilidade" in evidence


def test_context_is_refreshed_on_container_boot_without_blocking_web_start() -> None:
    dockerfile = (ROOT / "deploy" / "hetzner" / "Dockerfile").read_text(encoding="utf-8")

    assert "build_article1_agent_context.py" in dockerfile
    assert "dashboard will run in partial mode" in dockerfile
    assert "exec python apps/nutev-web/secure_server.py" in dockerfile