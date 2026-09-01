from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_development_surface_requires_accept_and_keeps_strength_unevaluated() -> None:
    html = read("recommendation-development.html")
    script = read("recommendation-development.js")
    service = read("recommendation_development.py")

    assert "HumanValidation ACCEPT" in html
    assert "NOT GRADE EtD" in html
    assert "NO AUTO-RECOMMENDATION" in html
    assert "strength not_evaluated" in html
    assert "Somente ACCEPT" in html
    assert "nunca copiado" in html
    assert "STAGE_RECOMMENDATION_DEVELOPMENT" in script
    assert "FINALIZE_RECOMMENDATION_DEVELOPMENT" in script
    assert 'STRENGTH_NOT_EVALUATED = "not_evaluated"' in service
    assert 'if str(validation.get("decision") or "") != "accept"' in service


def test_development_form_has_no_candidate_prefill_or_automatic_framework_path() -> None:
    script = read("recommendation-development.js")
    lowered = script.casefold()

    for token in ("openai", "anthropic", "claude", "gemini", "chatgpt"):
        assert token not in lowered
    for token in ("auto_recommend", "auto_strength", "auto_grade", "auto_etd"):
        assert token not in lowered
    assert "candidate_statement_auto_promoted" not in lowered
    assert "value=\"${esc(candidate.statement" not in script
    assert "placeholder=\"Escreva um novo wording humano" in script

    stage_match = re.search(r"async function stage\(card\)\{(?P<body>.*?)\n\}", script, re.S)
    assert stage_match is not None
    stage_body = stage_match.group("body")
    assert "FINALIZE_OPERATION" not in stage_body
    assert "finalizeDevelopment(" not in stage_body


def test_service_and_coordinator_preserve_generic_non_grade_semantics() -> None:
    service = read("recommendation_development.py")
    coordinator = read("governed_synthesis_release.py")

    assert 'DEVELOPMENT_METHOD = "NUTEV_GENERIC_RECOMMENDATION_DEVELOPMENT_V1"' in service
    assert '"formal_etd_framework_applied": False' in service
    assert '"grade_etd_applied": False' in service
    assert '"recommendation_strength_evaluated": False' in service
    assert '"formal_benefit_harm_balance_determined": False' in service
    assert '"values_preferences_formally_assessed": False' in service
    assert '"resource_use_formally_assessed": False' in service
    assert '"equity_formally_assessed": False' in service
    assert '"acceptability_formally_assessed": False' in service
    assert '"feasibility_formally_assessed": False' in service
    assert '"validated_recommendation_created": False' in service
    assert '"clinical_recommendation_created": False' in service
    assert '"guideline_recommendation_created": False' in service
    assert "_load_accepted_human_validation" in service
    assert "_candidate_snapshot" in service
    assert "_revalidate_draft" in service

    assert 'DEVELOPMENT_STAGE_OPERATION = "STAGE_RECOMMENDATION_DEVELOPMENT"' in coordinator
    assert 'DEVELOPMENT_FINALIZE_OPERATION = "FINALIZE_RECOMMENDATION_DEVELOPMENT"' in coordinator
    assert "stage_recommendation_development" in coordinator
    assert "finalize_recommendation_development" in coordinator
    assert "recommendation_development_status" in coordinator


def test_development_page_is_linked_from_human_validation_chain() -> None:
    html = read("recommendation-human-validation.html")
    assert "/recommendation-development.html" in html
    assert "never auto-creates it" in html
