from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "apps" / "nutev-web"
VALIDATION_ROOT = REPO_ROOT / "apps" / "nutev-validation"
DEPLOY_ROOT = REPO_ROOT / "deploy" / "hetzner"


def test_production_gateway_is_session_scoped_and_rate_limited() -> None:
    secure = (WEB_ROOT / "secure_server.py").read_text(encoding="utf-8")
    access = (WEB_ROOT / "search_access.py").read_text(encoding="utf-8")
    dockerfile = (DEPLOY_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert 'SESSION_COOKIE = "nutev_session"' in secure
    assert "HttpOnly" in secure and "SameSite=Lax" in secure
    assert "SESSION_START_LIMIT" in secure and "IP_START_LIMIT" in secure
    assert "SESSION_ACTIVE_LIMIT" in secure
    assert "filter_owned_runs" in secure
    assert "search_owned_by" in secure
    assert "record_search_owner" in secure
    assert '"legacy_search_disabled"' in secure
    assert 'exec python apps/nutev-web/secure_server.py' in dockerfile
    assert ".ownership.json" in access


def test_production_exposes_build_identity_without_secrets() -> None:
    secure = (WEB_ROOT / "secure_server.py").read_text(encoding="utf-8")
    dockerfile = (DEPLOY_ROOT / "Dockerfile").read_text(encoding="utf-8")
    compose = (DEPLOY_ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert 'path == "/api/version"' in secure
    for field in ("version", "commit", "branch", "build_time", "environment"):
        assert f'"{field}"' in secure
    for name in ("NUTEV_BUILD_COMMIT", "NUTEV_BUILD_BRANCH", "NUTEV_BUILD_TIME", "NUTEV_VERSION"):
        assert name in dockerfile
        assert name in compose
    for forbidden in ("NCBI_API_KEY", "S2_API_KEY", "PASSWORD"):
        assert forbidden not in secure


def test_production_adds_csp_and_preserves_existing_security_headers() -> None:
    secure = (WEB_ROOT / "secure_server.py").read_text(encoding="utf-8")
    caddy = (DEPLOY_ROOT / "Caddyfile").read_text(encoding="utf-8")
    assert "Content-Security-Policy" in secure
    assert "object-src 'none'" in secure
    assert "frame-ancestors 'self'" in secure
    assert "Strict-Transport-Security" in caddy
    for header in (
        "X-Content-Type-Options",
        "Referrer-Policy",
        "X-Frame-Options",
        "Permissions-Policy",
    ):
        assert header in caddy


def test_radar_empty_state_never_exposes_cli_or_internal_paths() -> None:
    radar = (WEB_ROOT / "radar_data.py").read_text(encoding="utf-8")
    function_start = radar.index("def load_radar_state(")
    missing_start = radar.index("if not manifest_path.is_file():", function_start)
    manifest_read = radar.index("manifest = _read_json", missing_start)
    empty_state = radar[missing_start:manifest_read]
    assert "Ainda não há snapshot científico publicado" in empty_state
    assert "science-topics" not in empty_state
    assert "science-watch" not in empty_state
    assert "project_output_reference" not in empty_state
    assert '"paths"' not in empty_state
    assert '"next_commands"' not in empty_state


def test_article_dossier_distinguishes_verbatim_from_processed_text() -> None:
    articles = (WEB_ROOT / "articles.js").read_text(encoding="utf-8")
    assert "Fonte (verbatim)." in articles
    assert "Texto processado/extraído pelo pipeline." in articles
    assert "Não é citação literal da fonte" in articles
    assert "Trecho-fonte rastreável" not in articles
    assert "matchMedia('(max-width: 1100px)')" in articles
    assert "scrollIntoView" in articles
    assert 'id="articleDetailTitle" tabindex="-1"' in articles


def test_public_validation_boundary_is_server_verified() -> None:
    secure = (WEB_ROOT / "secure_server.py").read_text(encoding="utf-8")
    boundary = (VALIDATION_ROOT / "public-boundary.js").read_text(encoding="utf-8")
    index = (VALIDATION_ROOT / "index.html").read_text(encoding="utf-8")
    assert 'path == "/api/capabilities"' in secure
    assert '"coordinator_available": self._is_loopback()' in secure
    assert "fetch('/api/capabilities'" in boundary
    assert "prepareRound" in boundary and "buildGold" in boundary and "runMetrics" in boundary
    assert "Coordenação disponível somente no ambiente autorizado" in boundary
    assert "public-boundary.js" in index


def test_search_surface_translates_status_and_explains_result_cap() -> None:
    search = (WEB_ROOT / "search.html").read_text(encoding="utf-8")
    ui = (WEB_ROOT / "product-ui.js").read_text(encoding="utf-8")
    assert "Pular para resultados" in search
    assert "product-ui.js" in search
    assert "COMPLETE_WITH_PROVIDER_GAPS:'Concluída, com lacunas em algumas fontes'" in ui
    assert "referências únicas. Este modo possui limite de apresentação" in ui
    assert "fetch('/api/version'" in ui
