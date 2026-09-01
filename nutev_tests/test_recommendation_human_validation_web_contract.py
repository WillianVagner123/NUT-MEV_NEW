from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_human_validation_surface_requires_explicit_unselected_human_decision() -> None:
    html = read("recommendation-human-validation.html")
    script = read("recommendation-human-validation.js")

    assert "HUMAN DECISION" in html
    assert "NO AUTO-ACCEPT" in html
    assert "ACCEPT ≠ CLINICAL RECOMMENDATION" in html
    assert "PENDING → ACCEPT / REJECT / REVISE" in html
    assert "readiness=not_evaluated" in html
    assert '<option value="">Selecione explicitamente…</option>' in script
    assert '<option value="ACCEPT">' in script
    assert '<option value="REJECT">' in script
    assert '<option value="REVISE">' in script
    assert "STAGE_RECOMMENDATION_HUMAN_VALIDATION" in script
    assert "DECIDE_RECOMMENDATION_HUMAN_VALIDATION" in script

    decision_match = re.search(r"async function decide\(card\)\{(?P<body>.*?)\n\}", script, re.S)
    assert decision_match is not None
    body = decision_match.group("body")
    assert "['ACCEPT','REJECT','REVISE'].includes(decision)" in body
    assert "decision_human_entered_confirmed:true" in body
    assert "decision_is_not_certainty_confirmed:true" in body
    assert "decision_is_not_clinical_recommendation_confirmed:true" in body
    assert "upstream_candidate_immutable_confirmed:true" in body


def test_human_validation_frontend_has_no_external_llm_or_auto_decision_path() -> None:
    script = read("recommendation-human-validation.js").casefold()
    for token in ("openai", "anthropic", "claude", "gemini", "chatgpt"):
        assert token not in script
    assert "auto_accept" not in script
    assert "auto_reject" not in script
    assert "auto_revise" not in script
    assert "readiness_score" not in script
    assert "certainty_score" not in script


def test_service_and_coordinator_preserve_validation_boundary() -> None:
    service = read("recommendation_human_validation.py")
    coordinator = read("governed_synthesis_release.py")

    assert 'VALIDATION_CASE_TYPE = "NUTEV_RECOMMENDATION_HUMAN_VALIDATION_CASE_V1"' in service
    assert 'CANONICAL_HUMAN_VALIDATION_RECORD_TYPE = "NUTEV_CANONICAL_HUMAN_VALIDATION_RECORD_V1"' in service
    assert 'PENDING = "PENDING"' in service
    assert 'DECISIONS = {ACCEPT, REJECT, REVISE}' in service
    assert '"automatic_validation_decision_performed": False' in service
    assert '"automatic_revision_applied": False' in service
    assert '"recommendation_candidate_changed": False' in service
    assert '"readiness_changed": False' in service
    assert '"readiness_evaluated": False' in service
    assert '"validated_recommendation_created": False' in service
    assert '"clinical_recommendation_created": False' in service
    assert '"guideline_recommendation_created": False' in service
    assert '"certainty_assessed": False' in service
    assert '"grade_assessed": False' in service
    assert '"formal_risk_of_bias_assessed": False' in service
    assert "_load_finalized_candidate" in service
    assert "_set_snapshot" in service
    assert "_revalidate_case" in service

    assert 'VALIDATION_STAGE_OPERATION = "STAGE_RECOMMENDATION_HUMAN_VALIDATION"' in coordinator
    assert 'VALIDATION_DECIDE_OPERATION = "DECIDE_RECOMMENDATION_HUMAN_VALIDATION"' in coordinator
    assert "stage_recommendation_human_validation" in coordinator
    assert "decide_recommendation_human_validation" in coordinator
    assert "recommendation_human_validation_status" in coordinator


def test_human_validation_is_linked_from_candidate_and_dashboard() -> None:
    candidate_html = read("recommendation-candidates.html")
    dashboard = read("index.html")
    assert "/recommendation-human-validation.html" in candidate_html
    assert "/recommendation-human-validation.html" in dashboard
    assert "HumanValidation ACCEPT ≠ clinical/guideline recommendation/certainty/GRADE" in dashboard
