from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy" / "hetzner"
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-hetzner.yml"


def test_hetzner_compose_preserves_data_and_keeps_backend_private() -> None:
    compose = (DEPLOY / "compose.yaml").read_text(encoding="utf-8")
    assert '127.0.0.1:8765:8765' in compose
    assert '"8765:8765"' not in compose.replace('127.0.0.1:8765:8765', '')
    assert 'nutev_output:/app/project_output_reference' in compose
    assert 'no-new-privileges:true' in compose
    assert '${NUTEV_IMAGE:-nutev-local:latest}' in compose


def test_autodeploy_is_guarded_by_ci_and_explicit_enable_flag() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert 'workflows: ["ci"]' in workflow
    assert "github.event.workflow_run.conclusion == 'success'" in workflow
    assert "github.event.workflow_run.head_branch == 'main'" in workflow
    assert "vars.HETZNER_AUTODEPLOY == 'true'" in workflow
    assert 'environment: production' in workflow


def test_autodeploy_preflights_and_rolls_back_on_health_failure() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert '127.0.0.1:18765:8765' in workflow
    assert 'http://127.0.0.1:18765/api/health' in workflow
    assert 'http://127.0.0.1:8765/api/health' in workflow
    assert 'docker tag "$OLD_IMAGE_ID" nutev:rollback' in workflow
    assert 'NUTEV_IMAGE=nutev:rollback' in workflow
    assert 'docker compose --env-file deploy/hetzner/.env' in workflow


def test_deploy_files_do_not_embed_secrets() -> None:
    env_example = (DEPLOY / ".env.example").read_text(encoding="utf-8")
    caddy = (DEPLOY / "Caddyfile").read_text(encoding="utf-8")
    assert 'REPLACE_WITH_CADDY_PASSWORD_HASH' in env_example
    assert '{$NUTEV_BASIC_AUTH_HASH}' in caddy
    assert 'BEGIN OPENSSH PRIVATE KEY' not in WORKFLOW.read_text(encoding="utf-8")
