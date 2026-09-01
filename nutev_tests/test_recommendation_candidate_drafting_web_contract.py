from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_recommendation_surface_requires_human_authorship_and_keeps_readiness_unevaluated() -> None:
    html = read("recommendation-candidates.html")
    script = read("recommendation-candidates.js")

    assert "HUMAN AUTHORSHIP" in html
    assert "CANDIDATE ≠ VALIDATED RECOMMENDATION" in html
    assert "readiness=not_evaluated" in html
    assert "Nenhum conteúdo é pré-preenchido" in html
    assert 'id="recommendationStatement"' in html
    assert 'id="humanAuthorship"' in html
    assert "HumanValidation" in html
    assert "STAGE_RECOMMENDATION_CANDIDATE" in script
    assert "FINALIZE_RECOMMENDATION_CANDIDATE" in script
    assert "statement_human_authored_confirmed" in script

    stage_match = re.search(r"async function stage\(\)\{(?P<body>.*?)\n\}", script, re.S)
    assert stage_match is not None
    stage_body = stage_match.group("body")
    assert "FINALIZE_OPERATION" not in stage_body
    assert "finalizeCandidate(" not in stage_body


def test_recommendation_frontend_has_no_external_llm_or_auto_readiness_path() -> None:
    script = read("recommendation-candidates.js").casefold()
    for token in ("openai", "anthropic", "claude", "gemini", "chatgpt"):
        assert token not in script
    assert "readiness_score" not in script
    assert "certainty_score" not in script
    assert "auto_recommend" not in script


def test_service_and_coordinator_keep_candidate_separate_from_validation() -> None:
    service = read("recommendation_candidate_drafting.py")
    coordinator = read("governed_synthesis_release.py")

    assert 'READINESS_NOT_EVALUATED = "not_evaluated"' in service
    assert '"recommendation_candidate_created": True' in service
    assert '"recommendation_validated": False' in service
    assert '"human_validation_created": False' in service
    assert '"clinical_recommendation_created": False' in service
    assert '"automatic_statement_generation_performed": False' in service
    assert '"automatic_readiness_inference_performed": False' in service
    assert '"evidence_set_agreement_inferred": False' in service
    assert '"certainty_assessed": False' in service
    assert "_load_finalized_evidence_set" in service
    assert "_member_snapshot" in service
    assert "human_validation_required_confirmed" in service

    assert 'RECOMMENDATION_STAGE_OPERATION = "STAGE_RECOMMENDATION_CANDIDATE"' in coordinator
    assert 'RECOMMENDATION_FINALIZE_OPERATION = "FINALIZE_RECOMMENDATION_CANDIDATE"' in coordinator
    assert "stage_recommendation_candidate" in coordinator
    assert "finalize_recommendation_candidate" in coordinator
    assert "recommendation_candidate_status" in coordinator


def test_recommendation_page_is_linked_from_evidence_set_chain() -> None:
    html = read("evidence-sets.html")
    dashboard = read("index.html")
    assert "/recommendation-candidates.html" in html
    assert "/recommendation-candidates.html" in dashboard
