from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_adoption_surface_is_scope_limited_and_has_no_default_decision() -> None:
    html = read("recommendation-adoption.html")
    script = read("recommendation-adoption.js")

    assert "SCOPE-LIMITED ONLY" in html
    assert "NO AUTO-STRENGTH" in html
    assert "ADOPT_FOR_DEFINED_SCOPE" in html
    assert "RETURN_FOR_REVISION" in html
    assert 'option value="">Selecione uma decisão humana' in script
    assert "recommendation strength" in html.casefold()
    assert "guideline recommendation" in html.casefold()

    lowered = script.casefold()
    for token in ("openai", "anthropic", "claude", "gemini", "chatgpt"):
        assert token not in lowered
    for token in ("auto_adopt", "auto_strength", "auto_grade", "auto_certainty"):
        assert token not in lowered


def test_stage_does_not_decide_and_decision_requires_explicit_operation() -> None:
    script = read("recommendation-adoption.js")
    stage_match = re.search(
        r'root\.querySelectorAll\("\.stage-adoption"\).*?await post\(\{(?P<body>.*?)\}\);',
        script,
        re.S,
    )
    assert stage_match is not None
    stage_body = stage_match.group("body")
    assert "STAGE_OPERATION" in stage_body
    assert "DECIDE_OPERATION" not in stage_body
    assert "decision:" not in stage_body
    assert 'const DECIDE_OPERATION = "DECIDE_RECOMMENDATION_ADOPTION"' in script


def test_service_and_coordinator_preserve_no_strength_no_guideline_semantics() -> None:
    service = read("recommendation_adoption.py")
    coordinator = read("governed_synthesis_release.py")

    assert 'ADOPTION_STAGE_OPERATION = "STAGE_RECOMMENDATION_ADOPTION"' in coordinator
    assert 'ADOPTION_DECIDE_OPERATION = "DECIDE_RECOMMENDATION_ADOPTION"' in coordinator
    assert "stage_recommendation_adoption" in coordinator
    assert "decide_recommendation_adoption" in coordinator
    assert "recommendation_adoption_status" in coordinator

    assert 'ADOPT_FOR_DEFINED_SCOPE = "ADOPT_FOR_DEFINED_SCOPE"' in service
    assert 'RETURN_FOR_REVISION = "RETURN_FOR_REVISION"' in service
    assert '"recommendation_strength_evaluated": False' in service
    assert '"certainty_assessed": False' in service
    assert '"grade_assessed": False' in service
    assert '"formal_etd_framework_applied": False' in service
    assert '"grade_etd_applied": False' in service
    assert '"validated_recommendation_created": False' in service
    assert '"clinical_recommendation_created": False' in service
    assert '"guideline_recommendation_created": False' in service
    assert '"universal_recommendation_created": False' in service
    assert '"automatic_adoption_decision_performed": False' in service
    assert "_load_finalized_development" in service
    assert "_revalidate_case" in service


def test_adoption_page_is_linked_from_development_chain() -> None:
    html = read("recommendation-development.html")
    assert "/recommendation-adoption.html" in html
    assert "never auto-adopts it" in html
