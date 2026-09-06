from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def test_search_loads_facets_before_main_renderer_and_keeps_library_bridge() -> None:
    html = (WEB / "search.html").read_text(encoding="utf-8")

    assert "search-facets.css" in html
    assert "search-facets-ui.js" in html
    assert html.index("search-library-ui.js") < html.index("search-facets-ui.js") < html.index("app.js")


def test_facets_cover_reliable_returned_result_dimensions() -> None:
    facets = (WEB / "search-facets-ui.js").read_text(encoding="utf-8")

    for control in ("facetYear", "facetClass", "facetProvider", "facetTaxonomy", "facetSort"):
        assert control in facets
    for sort_key in ("query_relevance", "final_score", "newest", "nutev_priority"):
        assert sort_key in facets
    assert "resultados retornados nesta busca" in facets
    assert "Texto completo não é oferecido como faceta" in facets
    assert "status verificável por resultado" in facets
    assert "data-result-index" in facets


def test_facet_sorting_does_not_break_saved_article_identity() -> None:
    facets = (WEB / "search-facets-ui.js").read_text(encoding="utf-8")
    library = (WEB / "search-library-ui.js").read_text(encoding="utf-8")

    assert 'data-result-index="${entry.index}"' in facets
    assert "card.dataset.resultIndex" in library
    assert "results[resultIndex]" in library
    assert "canonicalSavedKey(record)" in library


def test_facets_hide_while_new_search_is_loading() -> None:
    facets = (WEB / "search-facets-ui.js").read_text(encoding="utf-8")

    assert "summary.classList.contains('hidden')" in facets
    assert "existingWorkspace?.classList.add('hidden')" in facets
    assert "workspace.classList.remove('hidden')" in facets


def test_facets_are_client_side_refinement_not_new_scientific_authority() -> None:
    facets = (WEB / "search-facets-ui.js").read_text(encoding="utf-8")
    server = (WEB / "server.py").read_text(encoding="utf-8")

    assert "sem refazer a busca nas fontes" in facets
    assert "reference_score" in facets
    assert "query_relevance_score" in facets
    assert "nutev_priority_score" in facets
    assert "/api/facets" not in server
