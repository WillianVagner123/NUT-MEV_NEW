from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"
if str(WEB) not in sys.path:
    sys.path.insert(0, str(WEB))

from evidence_claim_review import (  # noqa: E402
    ACCEPTED,
    CANONICAL_CLAIM_RECORD_TYPE,
    PENDING,
    REJECTED,
    REVISION_REQUIRED,
    SynthesisGovernanceError,
    _claim_root,
    claim_review_status,
    decide_claim_candidate,
    stage_claim_candidates,
)
from governed_publication_manifest import prepare_publication_manifest  # noqa: E402
from governed_synthesis_release import prepare_governed_release  # noqa: E402
from synthesis_governance import (  # noqa: E402
    BRIEF_TYPE,
    REVIEW_TYPE,
    _digest,
    context_fingerprint_source,
    decide_entry,
    stage_brief,
)


def _write_search_state(output_root: Path, *, database_sha: str = "a" * 64) -> dict:
    state = {
        "search_id": "search_claim_review_01",
        "context_version": "nutev_article1_agent_context_v1",
        "question": "What is the current evidence structure?",
        "runtime": {
            "workbench": {"database_sha256": database_sha},
            "article1_routes": {"manifest_sha256": "b" * 64},
            "review_profiles": {"profile_version": "review_profile_v2"},
            "agent_article_summaries": 12,
        },
    }
    path = output_root / "agent_context" / "article1" / "SEARCH_STATE.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state), encoding="utf-8")
    return state


def _decision() -> dict:
    return {
        "decision_id": "doi:10.1000/a::pmid:123456",
        "domain": "food_literacy",
        "domain_label": "Food / nutrition literacy",
        "anchor": {
            "document_id": "doi:10.1000/a",
            "title": "Study A",
            "bundle_id": "result:a",
            "source_sentence_sha256": "d" * 64,
            "result_text": "The intervention group reported a higher food-literacy score at follow-up.",
            "outcomes": ["food literacy"],
            "effect_measures": ["mean difference 4.2"],
            "confidence_intervals": ["95% CI 1.1 to 7.3"],
            "p_values": ["p=0.01"],
            "routes": ["C-STRUCT"],
        },
        "candidate": {
            "document_id": "pmid:123456",
            "title": "Study B",
            "bundle_id": "result:b",
            "source_sentence_sha256": "e" * 64,
            "result_text": "The comparator study also reported higher food-literacy scores after the program.",
            "outcomes": ["food literacy"],
            "effect_measures": [],
            "confidence_intervals": [],
            "p_values": [],
            "routes": ["B-NORM"],
        },
        "comparability": {
            "population": "SIMILAR",
            "construct_intervention": "SIMILAR",
            "outcome": "SIMILAR",
            "timeframe": "UNCLEAR",
        },
        "relation": "CONVERGENT",
        "rationale": "The reviewer judged the outcome direction comparable across both source-linked results.",
        "reviewer": "Reviewer One",
        "reviewed_at": "2026-09-01T12:00:00+00:00",
        "human_entered": True,
        "canonical": False,
    }


def _brief(output_root: Path) -> dict:
    search = json.loads(
        (output_root / "agent_context" / "article1" / "SEARCH_STATE.json").read_text(
            encoding="utf-8"
        )
    )
    fingerprint = _digest(context_fingerprint_source(search))
    content = {
        "export_type": BRIEF_TYPE,
        "canonical": False,
        "integrity_verified": True,
        "current_context_match": True,
        "source_review_type": REVIEW_TYPE,
        "source_review_content_sha256": "c" * 64,
        "source_context_fingerprint": fingerprint,
        "search_id": search["search_id"],
        "context_version": search["context_version"],
        "question": search["question"],
        "reviewer": "Reviewer One",
        "relationship_counts": {"CONVERGENT": 1},
        "domain_counts": {"food_literacy": 1},
        "comparability_counts": {"population": {"SIMILAR": 1}},
        "reviewed_decisions": [_decision()],
        "guardrails": {
            "source_review_is_noncanonical": True,
            "integrity_verification_is_not_scientific_validation": True,
            "integrity_verification_does_not_prove_authorship_or_authenticity": True,
            "relationship_counts_are_not_evidence_strength": True,
            "convergent_is_not_certainty": True,
            "divergent_is_not_proven_contradiction": True,
            "brief_is_not_meta_analysis": True,
            "brief_is_not_prisma": True,
            "accepted_evidence_claims_created": False,
            "risk_of_bias_assessed": False,
            "certainty_assessed": False,
            "formal_search_state_changed": False,
        },
    }
    return {
        **content,
        "content_sha256": _digest(content),
        "generated_at": "2026-09-01T12:05:00+00:00",
        "artifact_semantics": "Presentation-ready human review brief.",
    }


def _publication(output_root: Path) -> dict:
    staged = stage_brief(
        {"actor": "Registry Operator", "artifact": _brief(output_root)},
        output_root=output_root,
    )
    approved = decide_entry(
        {
            "artifact_id": staged["artifact_id"],
            "action": "APPROVE",
            "governor": "Governance Reviewer",
            "rationale": "Approved for governed dissemination after manual provenance and context review.",
        },
        output_root=output_root,
    )
    release = prepare_governed_release(
        {
            "artifact_id": approved["artifact_id"],
            "prepared_by": "Release Operator",
            "purpose": "Prepare a governed package for manuscript drafting and scientific presentation.",
        },
        output_root=output_root,
    )
    return prepare_publication_manifest(
        {
            "package_id": release["record"]["package_id"],
            "publication_owner": "Publication Owner",
            "intended_use": "Prepare a manuscript results section with explicit source traceability.",
        },
        output_root=output_root,
    )


def _write_evidence_records(output_root: Path) -> None:
    path = output_root / "scientific" / "evidence_records.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "id": "evidence:doi:10.1000/a",
            "document_id": "doi:10.1000/a",
            "source_provider": "pubmed",
            "source_run_id": "run-1",
        },
        {
            "id": "evidence:pmid:123456",
            "document_id": "pmid:123456",
            "source_provider": "pubmed",
            "source_run_id": "run-1",
        },
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _stage(output_root: Path) -> dict:
    publication = _publication(output_root)
    return stage_claim_candidates(
        {
            "manifest_id": publication["record"]["manifest_id"],
            "staged_by": "Claim Coordinator",
        },
        output_root=output_root,
    )


def _accept_payload(candidate_id: str) -> dict:
    return {
        "candidate_id": candidate_id,
        "decision": "ACCEPT",
        "reviewer": "Claim Reviewer",
        "rationale": "The statement is a bounded source-level proposition supported by the linked result snapshot.",
        "claim_statement": "Study A reported a higher food-literacy score in the intervention group at follow-up.",
        "population": "Adults enrolled in the study",
        "intervention_or_exposure": "Food-literacy intervention",
        "comparator": "Comparator condition",
        "outcome": "Food-literacy score",
        "evidence_type": "Study-reported result",
        "source_attribution_confirmed": True,
        "scientific_boundary_confirmed": True,
    }


def test_staging_is_atomic_source_level_and_never_auto_accepts(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    status = _stage(tmp_path)

    assert status["candidate_count"] == 2
    assert status["candidate_counts"][PENDING] == 2
    assert status["accepted_claim_count"] == 0
    for candidate in status["candidates"]:
        assert candidate["evidence_record_id"].startswith("evidence:")
        assert candidate["evidence_record_resolved"] is False
        assert candidate["synthesis_context"]["directly_promotable_to_evidence_claim"] is False
        assert candidate["synthesis_context"]["relation"] == "CONVERGENT"


def test_accept_creates_canonical_source_claim_only_after_evidence_record_resolution(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    status = _stage(tmp_path)
    _write_evidence_records(tmp_path)
    candidate_id = status["candidates"][0]["candidate_id"]

    decided = decide_claim_candidate(_accept_payload(candidate_id), output_root=tmp_path)

    assert decided["candidate_counts"][ACCEPTED] == 1
    assert decided["accepted_claim_count"] == 1
    claim_meta = decided["accepted_claims"][0]
    assert claim_meta["evidence_record_id"].startswith("evidence:")
    assert claim_meta["claim_evaluation_created"] is False

    claim_id = claim_meta["claim_id"]
    record = json.loads(
        (_claim_root(tmp_path) / "accepted" / f"{claim_id}.json").read_text(encoding="utf-8")
    )
    assert record["claim_record_type"] == CANONICAL_CLAIM_RECORD_TYPE
    assert record["canonical"] is True
    assert record["source_evidence_record_verified"] is True
    assert record["evidence_claim"]["locator"] == "result:a"
    assert record["evidence_claim"]["quote"] is None
    assert record["evidence_claim"]["metadata"]["claim_semantics"] == "SOURCE_REPORTED_PROPOSITION"
    assert record["guardrails"]["accepted_evidence_claim_created"] is True
    assert record["guardrails"]["claim_acceptance_is_not_screening_inclusion"] is True
    assert record["guardrails"]["screening_eligibility_verified"] is False
    assert record["guardrails"]["claim_evaluation_created"] is False
    assert record["guardrails"]["risk_of_bias_assessed"] is False
    assert record["guardrails"]["certainty_assessed"] is False
    assert record["guardrails"]["evidence_set_created"] is False
    assert record["guardrails"]["clinical_recommendation_created"] is False
    assert record["guardrails"]["prisma_event_emitted"] is False
    assert record["guardrails"]["pairwise_synthesis_statement_promoted"] is False


def test_accept_missing_evidence_record_fails_without_acceptance_artifacts(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    status = _stage(tmp_path)
    candidate_id = status["candidates"][0]["candidate_id"]

    with pytest.raises(SynthesisGovernanceError, match="EvidenceRecord correspondente"):
        decide_claim_candidate(_accept_payload(candidate_id), output_root=tmp_path)

    current = claim_review_status(output_root=tmp_path)
    assert current["candidate_counts"][PENDING] == 2
    assert current["accepted_claim_count"] == 0
    accepted_dir = _claim_root(tmp_path) / "accepted"
    assert not accepted_dir.exists() or not list(accepted_dir.glob("*.json"))
    review_dir = _claim_root(tmp_path) / "reviews" / candidate_id
    assert not review_dir.exists() or not list(review_dir.glob("*.json"))


def test_revise_is_nonfinal_and_can_be_followed_by_accept(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    status = _stage(tmp_path)
    _write_evidence_records(tmp_path)
    candidate_id = status["candidates"][0]["candidate_id"]

    revised = decide_claim_candidate(
        {
            "candidate_id": candidate_id,
            "decision": "REVISE",
            "reviewer": "Claim Reviewer",
            "rationale": "The proposed wording needs a narrower source-attribution frame before it can be accepted.",
        },
        output_root=tmp_path,
    )
    assert revised["candidate_counts"][REVISION_REQUIRED] == 1
    assert revised["accepted_claim_count"] == 0

    accepted = decide_claim_candidate(_accept_payload(candidate_id), output_root=tmp_path)
    assert accepted["candidate_counts"][ACCEPTED] == 1
    assert accepted["accepted_claim_count"] == 1


def test_reject_is_final_and_does_not_create_claim(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    status = _stage(tmp_path)
    _write_evidence_records(tmp_path)
    candidate_id = status["candidates"][0]["candidate_id"]

    rejected = decide_claim_candidate(
        {
            "candidate_id": candidate_id,
            "decision": "REJECT",
            "reviewer": "Claim Reviewer",
            "rationale": "The source snapshot does not support a sufficiently bounded claim for the evidence bank.",
        },
        output_root=tmp_path,
    )
    assert rejected["candidate_counts"][REJECTED] == 1
    assert rejected["accepted_claim_count"] == 0

    with pytest.raises(SynthesisGovernanceError, match="decisão final"):
        decide_claim_candidate(_accept_payload(candidate_id), output_root=tmp_path)


def test_accept_requires_explicit_source_and_boundary_confirmations(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    status = _stage(tmp_path)
    _write_evidence_records(tmp_path)
    candidate_id = status["candidates"][0]["candidate_id"]
    payload = _accept_payload(candidate_id)
    payload["source_attribution_confirmed"] = False
    with pytest.raises(SynthesisGovernanceError, match="proposição reportada"):
        decide_claim_candidate(payload, output_root=tmp_path)

    payload = _accept_payload(candidate_id)
    payload["scientific_boundary_confirmed"] = False
    with pytest.raises(SynthesisGovernanceError, match="certainty"):
        decide_claim_candidate(payload, output_root=tmp_path)


def test_claim_decision_fails_closed_when_context_changes_after_staging(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    status = _stage(tmp_path)
    _write_evidence_records(tmp_path)
    candidate_id = status["candidates"][0]["candidate_id"]
    _write_search_state(tmp_path, database_sha="f" * 64)

    with pytest.raises(SynthesisGovernanceError, match="contexto científico atual|Context fingerprint"):
        decide_claim_candidate(_accept_payload(candidate_id), output_root=tmp_path)
