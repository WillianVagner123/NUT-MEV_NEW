from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "apps" / "nutev-web"
VALIDATION_ROOT = REPO_ROOT / "apps" / "nutev-validation"


def test_validation_metrics_api_is_local_only_and_uses_canonical_tools() -> None:
    server = (WEB_ROOT / "server.py").read_text(encoding="utf-8")
    service = (WEB_ROOT / "validation_metrics.py").read_text(encoding="utf-8")
    assert 'path == "/api/validation/metrics"' in server
    assert 'path == "/api/validation/metrics/run"' in server
    assert "_require_loopback" in server
    assert "evaluate_scientific_validation.py" in service
    assert "compare_scientific_benchmark.py" in service
    assert 'split="validation"' in service
    assert '("nutev_full", "lexical_baseline")' in service
    assert "required_judged_depth=100" in service


def test_validation_metrics_source_requires_label_blind_manifest_and_is_private() -> None:
    service = (WEB_ROOT / "validation_metrics.py").read_text(encoding="utf-8")
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert 'manifest.get("label_blind_build") is not True' in service
    assert 'manifest.get("gold_standard_consumed") is not False' in service
    assert "candidate_runtime_sha" in service
    assert "questions_sha256" in service
    assert "ranking_sha256" in service
    assert "validation/data/validation_coordinator_audit/" in gitignore


def test_coordinator_ui_exposes_validation_only_metrics_and_keeps_external_sealed() -> None:
    launcher = (VALIDATION_ROOT / "launcher.js").read_text(encoding="utf-8")
    assert "/api/validation/metrics/run" in launcher
    assert "Calcular métricas da validation" in launcher
    assert "nutev_full" in launcher
    assert "lexical_baseline" in launcher
    assert "Δ mediano nDCG@20" in launcher
    assert "Δ mediano recall@100" in launcher
    assert "External test segue selado" in launcher
    assert "decisão ainda precisa ser formalmente bloqueada" in launcher
    assert "validation_metrics_complete" in launcher


def test_metrics_service_never_releases_external_test_or_claims_final_promotion() -> None:
    service = (WEB_ROOT / "validation_metrics.py").read_text(encoding="utf-8")
    launcher = (VALIDATION_ROOT / "launcher.js").read_text(encoding="utf-8")
    assert '"external_test_labels_consumed": False' in service
    assert '"external_test_metrics_calculated": False' in service
    assert '"external_test_released": False' in service
    assert '"decision_locked": False' in service
    assert "C — SCIENTIFIC_CANDIDATE" not in launcher
    assert "external_test_released": True not in launcher
