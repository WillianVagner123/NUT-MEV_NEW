from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "apps" / "nutev-web"


def test_web_app_exposes_search_and_validation_without_csv_ui() -> None:
    index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert "Buscar evidências" in index
    assert "/validation/" in index
    assert "/api/search" in app
    for forbidden in (".csv", "upload csv", "importar csv"):
        assert forbidden not in index.casefold()


def test_web_search_reuses_canonical_engine_primitives_and_latin_pipeline() -> None:
    adapter = (WEB_ROOT / "search_adapter.py").read_text(encoding="utf-8")
    assert "dedupe_records" in adapter
    assert "score_record" in adapter
    assert "load_canonical_taxonomy" in adapter
    assert "run_latin_sources" in adapter
    for provider in (
        "pubmed",
        "europepmc",
        "openalex",
        "crossref",
        "doaj",
        "semantic_scholar",
        "lilacs_bvs_native",
        "scielo_native",
    ):
        assert f'"{provider}"' in adapter
    assert "Scopus" in adapter
    assert "Web of Science" in adapter


def test_provider_failures_are_explicit_and_network_disable_is_fail_closed() -> None:
    adapter = (WEB_ROOT / "search_adapter.py").read_text(encoding="utf-8")
    assert 'status = "failed"' in adapter
    assert '"network_disabled"' in adapter
    assert "COMPLETE_WITH_PROVIDER_GAPS" in adapter
    assert '"unavailable_providers"' in adapter


def test_web_history_uses_persisted_engine_runs() -> None:
    adapter = (WEB_ROOT / "search_adapter.py").read_text(encoding="utf-8")
    server = (WEB_ROOT / "server.py").read_text(encoding="utf-8")
    app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    assert "15_web_searches" in adapter
    assert "list_search_runs" in adapter
    assert "load_search_run" in adapter
    assert 'path == "/api/searches"' in server
    assert 'path.startswith("/api/searches/")' in server
    assert "fetch('/api/searches?limit=50')" in app
    assert "localStorage" not in app
    assert "Runs persistidos pelo NutEV Evidence Engine" in index


def test_server_adds_basic_security_headers() -> None:
    server = (WEB_ROOT / "server.py").read_text(encoding="utf-8")
    for header in (
        "X-Content-Type-Options",
        "Referrer-Policy",
        "X-Frame-Options",
        "Permissions-Policy",
    ):
        assert header in server
