from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"
if str(WEB) not in sys.path:
    sys.path.insert(0, str(WEB))

from synthesis_governance import (  # noqa: E402
    APPROVED,
    BRIEF_TYPE,
    REJECTED,
    REVIEW_TYPE,
    STAGED,
    SynthesisGovernanceError,
    _digest,
    context_fingerprint_source,
    decide_entry,
    registry_status,
    stage_brief,
)


def _write_search_state(output_root: Path, *, database_sha: str = "a" * 64) -> dict:
    state = {
        "search_id": "search_test_01",
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
        "decision_id": "doi:10.1/a::doi:10.1/b",
        "domain": "food_literacy",
        "domain_label": "Food / nutrition literacy",
        "anchor": {
            "document_id": "doi:10.1/a",
            "title": "Study A",
            "bundle_id": "result:a",
            "result_text": "Outcome improved in the intervention group.",
        },
        "candidate": {
            "document_id": "doi:10.1/b",
            "title": "Study B",
            "bundle_id": "result:b",
            "result_text": "Outcome also improved in the comparator study.",
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
    state_path = output_root / "agent_context" / "article1" / "SEARCH_STATE.json"
    search = json.loads(state_path.read_text(encoding="utf-8"))
    context_fingerprint = _digest(context_fingerprint_source(search))
    content = {
        "export_type": BRIEF_TYPE,
        "canonical": False,
        "integrity_verified": True,
        "current_context_match": True,
        "source_review_type": REVIEW_TYPE,
        "source_review_content_sha256": "c" * 64,
        "source_context_fingerprint": context_fingerprint,
        "search_id": search["search_id"],
        "context_version": search["context_version"],
        "question": search["question"],
        "reviewer": "Reviewer One",
        "relationship_counts": {"CONVERGENT": 1},
        "domain_counts": {"food_literacy": 1},
        "comparability_counts": {},
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


def test_stage_is_idempotent_and_does_not_approve(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    brief = _brief(tmp_path)

    first = stage_brief({"actor": "Registry Operator", "artifact": brief}, output_root=tmp_path)
    second = stage_brief({"actor": "Someone Else", "artifact": brief}, output_root=tmp_path)

    assert first["status"] == STAGED
    assert second["artifact_id"] == first["artifact_id"]
    assert second["staged_by"] == "Registry Operator"
    assert first["source_artifact_canonical"] is False
    assert first["canonical_registry_record"] is True
    assert first["canonical_scientific_synthesis_created"] is False
    assert first["reviewer_identity_cryptographically_authenticated"] is False
    registry = registry_status(output_root=tmp_path)
    assert registry["counts"][STAGED] == 1
    assert len(registry["entries"]) == 1


def test_governance_approval_is_explicit_and_not_scientific_canonization(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    staged = stage_brief(
        {"actor": "Registry Operator", "artifact": _brief(tmp_path)}, output_root=tmp_path
    )

    approved = decide_entry(
        {
            "artifact_id": staged["artifact_id"],
            "action": "APPROVE",
            "governor": "Governance Reviewer",
            "rationale": "Approved for governed presentation use after manual inspection of provenance and context.",
        },
        output_root=tmp_path,
    )

    assert approved["status"] == APPROVED
    assert approved["governance_decision"]["human_entered"] is True
    assert approved["governance_decision"]["source_revalidated_at_decision"] is True
    assert approved["governance_decision"]["identity_cryptographically_authenticated"] is False
    assert approved["canonical_scientific_synthesis_created"] is False


def test_governance_reject_is_a_governance_state_not_prisma(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    staged = stage_brief(
        {"actor": "Registry Operator", "artifact": _brief(tmp_path)}, output_root=tmp_path
    )
    rejected = decide_entry(
        {
            "artifact_id": staged["artifact_id"],
            "action": "REJECT",
            "governor": "Governance Reviewer",
            "rationale": "Rejected for governed use because the review package requires human correction before circulation.",
        },
        output_root=tmp_path,
    )
    assert rejected["status"] == REJECTED
    assert "PRISMA" not in rejected["status"]
    assert rejected["canonical_scientific_synthesis_created"] is False


def test_decision_fails_closed_if_context_changed_after_staging(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    staged = stage_brief(
        {"actor": "Registry Operator", "artifact": _brief(tmp_path)}, output_root=tmp_path
    )
    _write_search_state(tmp_path, database_sha="d" * 64)

    with pytest.raises(SynthesisGovernanceError, match="Context fingerprint"):
        decide_entry(
            {
                "artifact_id": staged["artifact_id"],
                "action": "APPROVE",
                "governor": "Governance Reviewer",
                "rationale": "This should fail because the materialized context changed after staging.",
            },
            output_root=tmp_path,
        )


def test_governance_requires_named_human_and_rationale(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    staged = stage_brief(
        {"actor": "Registry Operator", "artifact": _brief(tmp_path)}, output_root=tmp_path
    )
    with pytest.raises(SynthesisGovernanceError, match="Identifique"):
        decide_entry(
            {"artifact_id": staged["artifact_id"], "action": "APPROVE", "governor": "", "rationale": "x" * 30},
            output_root=tmp_path,
        )
    with pytest.raises(SynthesisGovernanceError, match="pelo menos 20"):
        decide_entry(
            {"artifact_id": staged["artifact_id"], "action": "APPROVE", "governor": "Governor", "rationale": "short"},
            output_root=tmp_path,
        )
