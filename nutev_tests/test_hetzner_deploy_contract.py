from pathlib import Path
import py_compile


REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_ROOT = REPO_ROOT / "deploy" / "hetzner"
WEB_ROOT = REPO_ROOT / "apps" / "nutev-web"


def test_backend_is_not_public_in_base_stack_and_state_is_persistent() -> None:
    compose = (DEPLOY_ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert 'expose:\n      - "8765"' in compose
    assert '"8765:8765"' not in compose
    assert "nutev_data:/app/project_output_reference" in compose
    assert 'profiles: ["edge"]' in compose
    assert '"80:80"' in compose
    assert '"443:443"' in compose


def test_shared_host_binds_backend_only_to_loopback() -> None:
    shared = (DEPLOY_ROOT / "compose.shared.yaml").read_text(encoding="utf-8")
    assert '"127.0.0.1:8765:8765"' in shared
    assert '"0.0.0.0:8765:8765"' not in shared


def test_caddy_separates_reviewer_token_routes_from_coordinator_auth() -> None:
    caddy = (DEPLOY_ROOT / "Caddyfile").read_text(encoding="utf-8")
    assert "@reviewer" in caddy
    assert "/validation/review.html" in caddy
    assert "/api/validation/reviewer/save" in caddy
    assert "basic_auth" in caddy
    assert "X-NutEV-Coordinator-Secret" in caddy
    reviewer_handle = caddy.index("handle @reviewer")
    auth_handle = caddy.index("basic_auth")
    assert reviewer_handle < auth_handle


def test_production_server_requires_exact_proxy_secret_without_weakening_local_server() -> None:
    production_path = WEB_ROOT / "production_server.py"
    production = production_path.read_text(encoding="utf-8")
    local = (WEB_ROOT / "server.py").read_text(encoding="utf-8")
    py_compile.compile(str(production_path), doraise=True)
    assert "compare_digest" in production
    assert "NUTEV_PROXY_COORDINATOR_SECRET" in production
    assert "X-NutEV-Coordinator-Secret" in production
    assert "self._is_loopback() or self._trusted_proxy_coordinator()" in production
    assert "_require_loopback" in local
    assert "ipaddress.ip_address" in local


def test_image_excludes_private_validation_and_generated_outputs() -> None:
    dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
    for required in (
        "project_output*",
        "validation/data/validation_assessor_packets",
        "validation/data/validation_coordinator_audit",
        ".env",
    ):
        assert required in dockerignore


def test_deployment_uses_production_entrypoint_and_documents_inflight_job_limit() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    runbook = (DEPLOY_ROOT / "README.md").read_text(encoding="utf-8")
    assert "apps/nutev-web/production_server.py" in dockerfile
    assert "127.0.0.1:8765:8765" in runbook
    assert "job de busca **em andamento** ainda vive na memória" in runbook
