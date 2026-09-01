from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_appraisal_reuses_existing_local_only_coordinator() -> None:
    server = read("server.py")
    release = read("governed_synthesis_release.py")
    script = read("claim-appraisal.js")

    assert 'path == "/api/synthesis/releases"' in server
    assert 'path == "/api/synthesis/releases/prepare"' in server
    assert "_require_loopback" in server
    assert 'EVALUATION_STAGE_OPERATION = "STAGE_CLAIM_EVALUATION"' in release
    assert 'EVALUATION_FINALIZE_OPERATION = "FINALIZE_CLAIM_EVALUATION"' in release
    assert "stage_claim_evaluation" in release
    assert "finalize_claim_evaluation" in release
    assert "operation:STAGE_OPERATION" in script
    assert "operation:FINALIZE_OPERATION" in script
    assert "fetch('/api/synthesis/releases/prepare'" in script
    assert "/api/claim-evaluation" not in script


def test_appraisal_has_six_explicit_human_dimensions_and_no_auto_score() -> None:
    service = read("claim_evaluation_appraisal.py")
    html = read("claim-appraisal.html")

    for dimension in (
        "design_appropriateness",
        "internal_validity_appraisal",
        "directness",
        "precision",
        "applicability",
        "reporting_completeness",
    ):
        assert f'"{dimension}"' in service
    assert 'APPRAISAL_METHOD = "NUTEV_GENERIC_CLAIM_APPRAISAL_V1"' in service
    assert '"numeric_score": False' in service
    assert '"automatic_overall_judgment": False' in service
    assert '"automatic_dimension_aggregation_performed": False' in service
    assert "NO AUTOMATIC SCORE" in html
    assert "NO AGGREGATION" in html


def test_appraisal_does_not_claim_formal_rob_grade_or_study_validity() -> None:
    service = read("claim_evaluation_appraisal.py")
    html = read("claim-appraisal.html")

    for token in (
        '"formal_external_instrument": False',
        '"formal_risk_of_bias_assessed": False',
        '"risk_of_bias_assessed": False',
        '"study_validity_determined": False',
        '"certainty_assessed": False',
        '"overall_certainty_grade_created": False',
        '"evidence_set_created": False',
        '"clinical_recommendation_created": False',
        '"screening_eligibility_changed": False',
        '"accepted_claim_statement_changed": False',
        '"meta_analysis_performed": False',
        '"prisma_event_emitted": False',
    ):
        assert token in service
    assert "ClaimEvaluation != formal Risk of Bias" in html
    assert "ClaimEvaluation != GRADE" in html
    assert "major concerns != automatic exclusion" in html


def test_ui_staging_never_auto_finalizes_and_load_never_finalizes() -> None:
    script = read("claim-appraisal.js")

    stage_body = script.split("async function stage()", 1)[1].split("function field", 1)[0]
    assert "FINALIZE_OPERATION" not in stage_body
    assert "finalizeAppraisal(" not in stage_body

    load_body = script.split("async function load()", 1)[1].split("$('appraisalClaim')", 1)[0]
    assert "FINALIZE_OPERATION" not in load_body
    assert "finalizeAppraisal(" not in load_body


def test_ui_requires_dimension_rationales_and_three_confirmations() -> None:
    script = read("claim-appraisal.js")

    assert "value.rationale.length<15" in script
    assert "overall.length<30" in script
    assert "nonformal_method_confirmed" in script
    assert "claim_scope_confirmed" in script
    assert "scientific_boundary_confirmed" in script
    assert "Confirme as três fronteiras científicas" in script


def test_appraisal_ui_has_no_external_llm_path() -> None:
    script = read("claim-appraisal.js").casefold()
    for token in ("openai", "anthropic", "claude", "gemini", "chatgpt"):
        assert token not in script


def test_appraisal_navigation_is_connected() -> None:
    dashboard = read("index.html")
    claims = read("evidence-claims.html")
    appraisal = read("claim-appraisal.html")

    assert "/claim-appraisal.html" in dashboard
    assert "/claim-appraisal.html" in claims
    assert "/evidence-claims.html" in appraisal
