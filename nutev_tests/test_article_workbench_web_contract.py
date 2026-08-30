from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def test_articles_is_first_class_navigation_and_detail_panel() -> None:
    index = (WEB / "index.html").read_text(encoding="utf-8")
    radar = (WEB / "radar.html").read_text(encoding="utf-8")
    page = (WEB / "articles.html").read_text(encoding="utf-8")
    assert 'href="/articles.html"' in index
    assert 'href="/articles.html"' in radar
    assert 'id="articleList"' in page
    assert 'id="articleDetail"' in page
    assert 'id="articleQuery"' in page
    assert 'id="providerFilter"' in page
    assert 'id="classFilter"' in page
    assert 'id="fullTextFilter"' in page
    assert 'id="loadMore"' in page


def test_articles_frontend_uses_paged_api_not_jsonl_corpus() -> None:
    app = (WEB / "articles.js").read_text(encoding="utf-8")
    css = (WEB / "articles.css").read_text(encoding="utf-8")
    assert "params.set('limit','50')" in app
    assert "fetch(`/api/articles?" in app
    assert "fetch(`/api/articles/${encodeURIComponent(documentId)}`" in app
    assert "next_cursor" in app
    assert "result_bundles" in app
    assert "evidence_excerpts" in app
    assert "verbatim_excerpt" in app
    assert "full_text" not in app.split("fetch(`/api/articles?", 1)[0].casefold()
    assert "article_evidence_cards.jsonl" not in app
    assert "evidence_excerpts.jsonl" not in app
    assert ".workbench-layout" in css
    assert ".article-detail" in css
    assert "position:sticky" in css


def test_articles_api_is_read_only_hash_verified_and_page_capped() -> None:
    server = (WEB / "server.py").read_text(encoding="utf-8")
    data = (WEB / "article_workbench_data.py").read_text(encoding="utf-8")
    assert 'if path == "/api/articles/status"' in server
    assert 'if path == "/api/articles"' in server
    assert 'path.startswith("/api/articles/")' in server
    assert '"article_workbench": True' in server
    assert 'path == "/api/articles"' not in server.split("def do_POST", 1)[1]
    assert "mode=ro" in data
    assert "max(1, min(int(limit), 100))" in data
    assert '"full_corpus_sent_to_browser": False' in data
    assert '"full_text_in_response": False' in data
    assert "SHA-256 mismatch" in data
