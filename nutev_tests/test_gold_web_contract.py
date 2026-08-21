from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "apps" / "nutev-web"
VALIDATION_ROOT = REPO_ROOT / "apps" / "nutev-validation"


def test_gold_api_is_local_only_and_uses_canonical_validator() -> None:
    server = (WEB_ROOT / "server.py").read_text(encoding="utf-8")
    service = (WEB_ROOT / "validation_gold.py").read_text(encoding="utf-8")
    assert 'path == "/api/validation/gold"' in server
    assert 'path == "/api/validation/gold/build"' in server
    assert "_require_loopback" in server
    assert "validate_gold_standard.py" in service
    assert "validator.validate(" in service
    assert "gold_standard_validated" in service
    assert '"external_test_consumed": False' in service
    assert '"synthetic_labels_created": False' in service
    assert '"metrics_calculated": False' in service


def test_gold_coordinator_gate_never_claims_scientific_performance_on_validator_pass() -> None:
    launcher = (VALIDATION_ROOT / "launcher.js").read_text(encoding="utf-8")
    assert "/api/validation/gold/build" in launcher
    assert "Construir e validar gold standard" in launcher
    assert "Gold standard validado" in launcher
    assert "Cobertura do pool: 100%" in launcher
    assert "Ainda não confirma desempenho científico do NutEV" in launcher
    assert "external_test" in launcher
    assert "gold_validated" in launcher


def test_gold_outputs_remain_under_gitignored_private_output_tree() -> None:
    service = (WEB_ROOT / "validation_gold.py").read_text(encoding="utf-8")
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert '"project_output_reference"' in service
    assert '"16_validation_server"' in service
    assert "project_output*/" in gitignore
    assert "GOLD_STANDARD.csv" in service
    assert "ASSESSMENTS.csv" in service
    assert "BLINDED_POOL_KEYS.csv" in service
