from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_human_synthesis_brief_is_fail_closed_and_noncanonical() -> None:
    html = read("synthesis-brief.html")
    script = read("synthesis-brief.js")

    assert "NUTEV_HUMAN_SYNTHESIS_REVIEW_DRAFT_V1" in script
    assert "NUTEV_HUMAN_SYNTHESIS_BRIEF_V1" in script
    assert 'id="reviewFile"' in html
    assert 'id="exportBrief"' in html and "disabled" in html
    assert 'id="printBrief"' in html and "disabled" in html
    assert "if(!allOk){resetBrief" in script
    assert "canonical:false" in script
    assert "integrity_verified:true" in script
    assert "current_context_match:true" in script
    assert "integrity_verification_is_not_scientific_validation:true" in script
    assert "integrity_verification_does_not_prove_authorship_or_authenticity:true" in script
    assert "SHA-256 ≠ authorship/authenticity" in html


def test_brief_verifies_content_sha_and_strong_context_fingerprint() -> None:
    script = read("synthesis-brief.js")

    assert "crypto.subtle.digest('SHA-256'" in script
    assert "content_sha256" in script
    assert "contextFingerprintSource" in script
    assert "context_fingerprint" in script
    assert "context_source" in script
    assert "workbench_database_sha256" in script
    assert "route_manifest_sha256" in script
    assert "review_profile_version" in script
    assert "agent_article_summaries" in script
    assert "reviewContextSourceOk" in script
    assert "contextFingerprintOk" in script
    assert "currentMatch=searchOk&&contextVersionOk&&questionOk&&contextFingerprintOk" in script
    assert "review?.context_fingerprint===state.currentContextFingerprint" in script


def test_source_human_review_is_bound_to_context_fingerprint() -> None:
    script = read("synthesis-review.js")

    assert "contextFingerprintSource" in script
    assert "state.contextFingerprint" in script
    assert "state.contextFingerprint.slice(0,16)" in script
    assert "parsed?.context_fingerprint===state.contextFingerprint" in script
    assert "context_fingerprint:contextFingerprint" in script
    assert "context_source:contextSource" in script
    assert "contextFingerprint!==state.contextFingerprint" in script


def test_brief_validates_human_semantics_without_creating_scientific_state() -> None:
    script = read("synthesis-brief.js")

    assert "validateReviewGuardrails" in script
    assert "validateDecisions" in script
    assert "human_entered_relations===true" in script
    for token in (
        "automatic_convergence_divergence",
        "accepted_evidence_claims_created",
        "screening_decisions_created",
        "risk_of_bias_assessed",
        "certainty_assessed",
        "prisma_event_emitted",
        "formal_search_state_changed",
    ):
        assert token in script

    assert "accepted_evidence_claims_created:false" in script
    assert "risk_of_bias_assessed:false" in script
    assert "certainty_assessed:false" in script
    assert "formal_search_state_changed:false" in script
    compact = script.replace(" ", "")
    assert "method:'POST'" not in compact
    assert 'method:"POST"' not in compact
    assert "api.openai.com" not in script
    assert "api.anthropic.com" not in script
    for forbidden in (
        "reference_rank",
        "reference_score",
        "machine_relevance_score",
        "machine_relevance_band",
    ):
        assert forbidden not in script


def test_brief_preserves_source_linked_human_decisions_and_descriptive_semantics() -> None:
    html = read("synthesis-brief.html")
    script = read("synthesis-brief.js")

    assert "source_sentence_sha256" in script
    assert "bundle_id" in script
    assert "relationship_counts_are_not_evidence_strength:true" in script
    assert "convergent_is_not_certainty:true" in script
    assert "divergent_is_not_proven_contradiction:true" in script
    assert "brief_is_not_meta_analysis:true" in script
    assert "brief_is_not_prisma:true" in script
    assert "Contagem não mede força" in html


def test_synthesis_chain_exposes_brief_navigation() -> None:
    assert "/synthesis-brief.html" in read("intelligence.html")
    assert "/synthesis-brief.html" in read("synthesis-review.html")
    assert "/synthesis-brief.html" in read("synthesis-brief.html")


def test_workspace_death_test_includes_brief_contract() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "audit_scientific_workspace_v2.py"), "--compact"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    assert result["mode"] == "NUTEV_SCIENTIFIC_WORKSPACE_V2_DEATH_TEST"
    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["read_only"] is True
