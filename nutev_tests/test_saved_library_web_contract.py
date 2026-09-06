from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def test_saved_library_is_browser_local_deduplicated_and_separate_from_scientific_workbench() -> None:
    store = (WEB / "saved-library.js").read_text(encoding="utf-8")
    workbench = (WEB / "article_workbench_data.py").read_text(encoding="utf-8")
    server = (WEB / "server.py").read_text(encoding="utf-8")

    assert "indexedDB.open" in store
    assert "canonicalSavedKey" in store
    assert "doi:" in store
    assert "pmid:" in store
    assert "url:" in store
    assert "browser_saved_search_result_not_scientific_inclusion" in store
    assert "mode=ro" in workbench
    assert 'path == "/api/articles"' in server
    assert '"/api/library"' not in server


def test_search_can_save_single_open_dossier_and_save_all() -> None:
    html = (WEB / "search.html").read_text(encoding="utf-8")
    ui = (WEB / "search-library-ui.js").read_text(encoding="utf-8")

    assert html.index("search-library-ui.js") < html.index("app.js")
    assert "Cobertura máxima disponível" in html
    assert "Guardar na Biblioteca" in ui
    assert "Guardar todos os resultados retornados" in ui
    assert "Abrir dossiê" in ui
    assert "saveArticle(" in ui
    assert "saveArticles(" in ui
    assert "/articles.html?saved=" in ui
    assert "existing?.dataset.savedLibraryKey===key" in ui
    assert "existing?.remove()" in ui


def test_biblioteca_surfaces_saved_core_without_replacing_verified_corpus() -> None:
    html = (WEB / "articles.html").read_text(encoding="utf-8")
    ui = (WEB / "saved-library-ui.js").read_text(encoding="utf-8")
    css = (WEB / "saved-library.css").read_text(encoding="utf-8")

    assert "saved-library.css" in html
    assert "saved-library-ui.js" in html
    assert "corpus científico verificado" in html
    assert "Meus salvos" in ui
    assert "Persistem neste navegador" in ui
    assert "Proveniência das buscas" in ui
    assert "Não equivale a inclusão em revisão" in ui
    assert ".saved-core" in css
