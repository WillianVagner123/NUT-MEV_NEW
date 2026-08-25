from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "apps" / "nutev-web"
VALIDATION_ROOT = REPO_ROOT / "apps" / "nutev-validation"


def test_web_app_exposes_search_and_validation_without_csv_ui() -> None:
    index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert "Buscar evidências" in index
    assert "/validation/" in index
    assert "/api/search/jobs" in app
    for forbidden in (".csv", "upload csv", "importar csv"):
        assert forbidden not in index.casefold()


def test_global_search_is_a_first_class_exhaustive_action() -> None:
    index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    css = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
    progressive = (WEB_ROOT / "progress_search.py").read_text(encoding="utf-8")
    assert 'id="globalSearchBtn"' in index
    assert "Busca global" in index
    assert "sem teto interno" in index
    assert "Não há corte interno de 100, 300 ou outro número" in index
    assert "GLOBAL_EXHAUSTIVE_SENTINEL=0" in app
    assert "state.providers.map(p=>p.id)" in app
    assert "runSearch({global:true})" in app
    assert "RESULT_BATCH=100" in app
    assert "Todos os resultados foram coletados" in app
    assert "EXHAUSTIVE_SENTINEL = 2_147_483_647" in progressive
    assert "raw_per_provider == 0 and raw_max_results == 0" in progressive
    assert 'search_mode = "global_exhaustive"' in progressive
    assert "returned = ranked if result_limit is None" in progressive
    assert '"non_exhaustive_providers"' in progressive
    assert ".global-search" in css


def test_structured_review_builder_is_first_class_and_auditable() -> None:
    index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    server = (WEB_ROOT / "server.py").read_text(encoding="utf-8")
    progressive = (WEB_ROOT / "progress_search.py").read_text(encoding="utf-8")
    compiler = (WEB_ROOT / "query_compiler.py").read_text(encoding="utf-8")
    assert 'id="structuredReviewToggle"' in index
    assert 'id="frameworkSelect"' in index
    assert "PCC" in index and "PICO" in index and "PECO" in index
    assert "mesh:Termo" in index
    assert "decs:Termo" in index
    assert "/api/query/compile" in app
    assert 'path == "/api/query/compile"' in server
    assert "compile_query_plan" in server
    assert "provider_queries=_query_strings(query_plan)" in server
    assert "provider_query=effective_query" in progressive
    assert '"query_plan": query_plan' in progressive
    assert 'search_mode = "structured_review_global_exhaustive"' in progressive
    assert '"pubmed_mesh_title_abstract"' in compiler
    assert '"bvs_decs_mesh_tw"' in compiler
    assert "não inventa MeSH/DeCS" in compiler


def test_web_search_reuses_canonical_engine_primitives_and_latin_pipeline() -> None:
    adapter = (WEB_ROOT / "search_adapter.py").read_text(encoding="utf-8")
    progressive = (WEB_ROOT / "progress_search.py").read_text(encoding="utf-8")
    assert "dedupe_records" in adapter
    assert "score_record" in adapter
    assert "load_canonical_taxonomy" in adapter
    assert "run_latin_sources" in adapter
    assert "_provider_call" in progressive
    assert "_latin_rows_and_status" in progressive
    assert "_score_rows" in progressive
    assert "_persist_search" in progressive
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
    progressive = (WEB_ROOT / "progress_search.py").read_text(encoding="utf-8")
    assert 'status = "failed"' in adapter
    assert '"network_disabled"' in adapter
    assert "COMPLETE_WITH_PROVIDER_GAPS" in adapter
    assert '"unavailable_providers"' in adapter
    assert '"network_disabled"' in progressive
    assert "COMPLETE_WITH_PROVIDER_GAPS" in progressive


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
    assert "params.get('view')==='history'" in app
    assert "localStorage" not in app
    assert "Runs persistidos pelo NutEV Evidence Engine" in index


def test_validation_entry_uses_same_product_navigation_and_hides_technical_first_step() -> None:
    launcher = (VALIDATION_ROOT / "launcher.js").read_text(encoding="utf-8")
    index = (VALIDATION_ROOT / "index.html").read_text(encoding="utf-8")
    shell_css = (VALIDATION_ROOT / "unified-shell.css").read_text(encoding="utf-8")
    assert "Buscar evidências" in launcher
    assert "Minhas buscas" in launcher
    assert "Validação científica" in launcher
    assert "Avaliação A/B" in launcher
    assert "Adjudicar" in launcher
    assert "Resultado" in launcher
    assert "Preparar rodada científica" in launcher
    assert "Configuração avançada" in launcher
    assert "CSV" not in launcher
    assert "MVP" not in launcher
    assert "unified-shell.css" in index
    assert ".unified-shell" in shell_css


def test_validation_readiness_is_server_verified_and_visible_without_file_ui() -> None:
    server = (WEB_ROOT / "server.py").read_text(encoding="utf-8")
    readiness = (WEB_ROOT / "validation_readiness.py").read_text(encoding="utf-8")
    launcher = (VALIDATION_ROOT / "launcher.js").read_text(encoding="utf-8")
    assert 'path == "/api/validation/readiness"' in server
    assert "get_validation_readiness" in server
    assert "EXPECTED_QUESTIONS_SHA256" in readiness
    assert "PROHIBITED_PACKET_COLUMNS" in readiness
    assert "pre-existing grade" in readiness
    assert "fetch('/api/validation/readiness'" in launcher
    assert "rodada científica verificada" in launcher
    assert "aguardando materiais privados" in launcher


def test_progressive_job_api_keeps_synchronous_search_compatibility() -> None:
    server = (WEB_ROOT / "server.py").read_text(encoding="utf-8")
    app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert '"/api/search/jobs"' in server
    assert 'path.startswith("/api/search/jobs/")' in server
    assert "threading.Thread" in server
    assert "search_evidence_progressive" in server
    assert '"/api/search"' in server
    assert "search_evidence(" in server
    assert "pollSearchJob" in app
    assert "setTimeout" in app
    assert "completed_providers" in app


def test_server_adds_basic_security_headers() -> None:
    server = (WEB_ROOT / "server.py").read_text(encoding="utf-8")
    for header in (
        "X-Content-Type-Options",
        "Referrer-Policy",
        "X-Frame-Options",
        "Permissions-Policy",
    ):
        assert header in server