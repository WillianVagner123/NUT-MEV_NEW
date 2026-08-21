from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "apps" / "nutev-web"
VALIDATION_ROOT = REPO_ROOT / "apps" / "nutev-validation"


def test_validation_decision_api_is_local_only_and_deterministic() -> None:
    server = (WEB_ROOT / "server.py").read_text(encoding="utf-8")
    service = (WEB_ROOT / "validation_decision.py").read_text(encoding="utf-8")
    assert 'path == "/api/validation/decision"' in server
    assert 'path == "/api/validation/decision/lock"' in server
    assert "_require_loopback" in server
    assert 'CONTINUE_DECISION = "CONTINUE_TO_EXTERNAL"' in service
    assert 'STOP_DECISION = "STOP_AT_B"' in service
    assert "CONTINUATION_CRITERIA_PASS" in service
    assert "CONTINUATION_CRITERIA_FAIL" in service
    assert '"automatic_external_release": False' in service
    assert '"external_test_released": False' in service


def test_validation_decision_ui_never_offers_manual_scientific_choice() -> None:
    script = (VALIDATION_ROOT / "decision-ui.js").read_text(encoding="utf-8")
    html = (VALIDATION_ROOT / "index.html").read_text(encoding="utf-8")
    assert "Bloquear decisão de validation" in script
    assert "A decisão não será escolhida manualmente" in script
    assert "CONTINUATION_CRITERIA_PASS" in script
    assert "CONTINUE_TO_EXTERNAL" in script
    assert "CONTINUATION_CRITERIA_FAIL" in script
    assert "STOP_AT_B" in script
    assert "External test continua selado" in script
    assert "decision-ui.js" in html
    assert "manualChoice" not in script
    assert "chosenDecision" not in script


def test_validation_decision_ui_is_idempotent_across_main_panel_rerenders() -> None:
    script = (VALIDATION_ROOT / "decision-ui.js").read_text(encoding="utf-8")
    assert "data-decision-state" in script
    assert "currentState === desiredState" in script
    assert "MutationObserver" in script
    assert "renderingDecision" in script


def test_decision_lock_verifies_metric_hashes_and_preserves_external_seal() -> None:
    service = (WEB_ROOT / "validation_decision.py").read_text(encoding="utf-8")
    for output in (
        "VALIDATION_BENCHMARK_RESULTS.csv",
        "VALIDATION_COMPARISON.json",
        "VALIDATION_PAIRED.csv",
        "VALIDATION_METRICS_MANIFEST.json",
        "GOLD_STANDARD_VALIDATION.json",
        "GOLD_BUILD_MANIFEST.json",
    ):
        assert output in service
    assert "SHA-256" in service
    assert 'metrics_manifest.get("split_evaluated") != "validation"' in service
    assert 'metrics_manifest.get("systems") != ["nutev_full", "lexical_baseline"]' in service
    assert 'int(metrics_manifest.get("required_judged_through") or 0) != 100' in service
