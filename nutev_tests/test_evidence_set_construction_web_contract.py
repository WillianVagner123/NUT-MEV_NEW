from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_coordinator_routes_explicit_evidence_set_operations() -> None:
    release = read("governed_synthesis_release.py")
    assert 'EVIDENCE_SET_STAGE_OPERATION = "STAGE_EVIDENCE_SET"' in release
    assert 'EVIDENCE_SET_FINALIZE_OPERATION = "FINALIZE_EVIDENCE_SET"' in release
    assert "stage_evidence_set" in release
    assert "finalize_evidence_set" in release


def test_service_requires_evaluated_claims_and_preserves_non_synthesis_boundary() -> None:
    service = read("evidence_set_construction.py")
    for token in (
        '"finalized_claim_evaluations_required": True',
        '"automatic_claim_grouping_performed": False',
        '"automatic_relation_inference_performed": False',
        '"claim_evaluation_scores_aggregated": False',
        '"consensus_inferred": False',
        '"contradiction_inferred": False',
        '"certainty_assessed": False',
        '"overall_certainty_grade_created": False',
        '"formal_risk_of_bias_assessed": False',
        '"canonical_scientific_synthesis_created": False',
        '"clinical_recommendation_created": False',
        '"meta_analysis_performed": False',
        '"prisma_event_emitted": False',
        '"overlapping_evidence_sets_allowed": True',
        '"single_claim_set_is_not_synthesis": True',
    ):
        assert token in service
    assert "_load_accepted_claim" in service
    assert "_evaluation_for_claim" in service
    assert "_revalidate_draft" in service


def test_ui_has_no_preselected_claims_or_auto_grouping_language() -> None:
    html = read("evidence-sets.html")
    script = read("evidence-sets.js")
    assert "HUMAN CURATION" in html
    assert "MEMBERSHIP ≠ CONSENSUS" in html
    assert "no automatic clustering" in html
    assert "Nenhum claim vem marcado por padrão" in html
    assert "OVERLAP ALLOWED" in html
    assert "EvidenceSet membership != agreement" in html
    assert 'type="checkbox" class="set-claim-selector"' in script
    assert "checked=true" not in script.replace(" ", "").lower()
    assert ".checked=true" not in script.replace(" ", "").lower()


def test_staging_never_calls_finalization() -> None:
    script = read("evidence-sets.js")
    match = re.search(r"async function stage\(\)\{(?P<body>.*?)\n\}", script, re.S)
    assert match is not None
    body = match.group("body")
    assert "FINALIZE_OPERATION" not in body
    assert "finalizeSet(" not in body


def test_no_external_llm_or_automatic_scoring_in_evidence_set_surface() -> None:
    script = read("evidence-sets.js").casefold()
    service = read("evidence_set_construction.py").casefold()
    for token in ("openai", "anthropic", "claude", "gemini", "chatgpt"):
        assert token not in script
    for token in ("overall_score", "quality_score", "certainty_grade", "pooled_effect"):
        assert token not in service


def test_release_status_joins_membership_without_mutating_claim_artifact() -> None:
    release = read("governed_synthesis_release.py")
    assert '"evidence_set_ids": set_ids' in release
    assert '"evidence_set_membership_count": len(set_ids)' in release
    assert "_atomic_json" not in release.split("membership_index = evidence_sets", 1)[1].split("return {", 1)[0]


def test_dashboard_chain_mentions_evidence_set_construction() -> None:
    index = read("index.html")
    appraisal = read("claim-appraisal.html")
    assert "/evidence-sets.html" in index
    assert "/evidence-sets.html" in appraisal
