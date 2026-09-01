from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"
if str(WEB) not in sys.path:
    sys.path.insert(0, str(WEB))

from governed_synthesis_release import (  # noqa: E402
    RELEASE_TYPE,
    build_governed_release,
    prepare_governed_release,
    release_status,
)
from synthesis_governance import (  # noqa: E402
    BRIEF_TYPE,
    REVIEW_TYPE,
    SynthesisGovernanceError,
    _digest,
    context_fingerprint_source,
    decide_entry,
    stage_brief,
)


def _write_search_state(output_root: Path, *, database_sha: str = "a" * 64) -> dict:
    state = {
        "search_id": "search_release_test_01",
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


def _approved(output_root: Path) -> dict:
    staged = stage_brief(
        {"actor": "Registry Operator", "artifact": _brief(output_root)},
        output_root=output_root,
    )
    return decide_entry(
        {
            "artifact_id": staged["artifact_id"],
            "action": "APPROVE",
            "governor": "Governance Reviewer",
            "rationale": "Approved for governed dissemination after manual provenance and context review.",
        },
        output_root=output_root,
    )


def test_release_rejects_staged_registry_entry(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    staged = stage_brief(
        {"actor": "Registry Operator", "artifact": _brief(tmp_path)}, output_root=tmp_path
    )

    with pytest.raises(SynthesisGovernanceError, match="APPROVED_FOR_GOVERNED_USE"):
        build_governed_release(
            staged["artifact_id"],
            prepared_by="Release Operator",
            purpose="Prepare a governed package for manuscript drafting and scientific presentation.",
            output_root=tmp_path,
        )


def test_release_is_noncanonical_and_persisted_idempotently(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    approved = _approved(tmp_path)
    payload = {
        "artifact_id": approved["artifact_id"],
        "prepared_by": "Release Operator",
        "purpose": "Prepare a governed package for manuscript drafting and scientific presentation.",
    }

    first = prepare_governed_release(payload, output_root=tmp_path)
    second = prepare_governed_release(payload, output_root=tmp_path)

    package = first["package"]
    record = first["record"]
    assert package["release_type"] == RELEASE_TYPE
    assert package["canonical"] is False
    assert record["canonical_release_record"] is True
    assert record["release_package_canonical"] is False
    assert record["canonical_scientific_synthesis_created"] is False
    assert second["record"]["package_id"] == record["package_id"]
    assert second["package"]["content_sha256"] == package["content_sha256"]
    assert package["guardrails"]["accepted_evidence_claims_created"] is False
    assert package["guardrails"]["risk_of_bias_assessed"] is False
    assert package["guardrails"]["certainty_assessed"] is False
    assert package["guardrails"]["meta_analysis_performed"] is False
    assert package["guardrails"]["prisma_event_emitted"] is False
    assert package["guardrails"]["formal_search_state_changed"] is False


def test_release_fails_closed_when_context_changes_after_governance(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    approved = _approved(tmp_path)
    _write_search_state(tmp_path, database_sha="d" * 64)

    with pytest.raises(SynthesisGovernanceError, match="Context fingerprint"):
        prepare_governed_release(
            {
                "artifact_id": approved["artifact_id"],
                "prepared_by": "Release Operator",
                "purpose": "Prepare a governed package only if the approved source context is still current.",
            },
            output_root=tmp_path,
        )


def test_release_ledger_is_metadata_only(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    approved = _approved(tmp_path)
    prepare_governed_release(
        {
            "artifact_id": approved["artifact_id"],
            "prepared_by": "Release Operator",
            "purpose": "Prepare a governed package for manuscript drafting and scientific presentation.",
        },
        output_root=tmp_path,
    )

    status = release_status(output_root=tmp_path)
    assert status["count"] == 1
    assert len(status["records"]) == 1
    record = status["records"][0]
    assert "reviewed_decisions" not in record
    assert "package" not in record
    assert "relationship_counts" not in record


def test_release_requires_human_preparer_and_specific_purpose(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    approved = _approved(tmp_path)
    with pytest.raises(SynthesisGovernanceError, match="Identifique"):
        build_governed_release(
            approved["artifact_id"], prepared_by="", purpose="x" * 30, output_root=tmp_path
        )
    with pytest.raises(SynthesisGovernanceError, match="pelo menos 20"):
        build_governed_release(
            approved["artifact_id"],
            prepared_by="Release Operator",
            purpose="short",
            output_root=tmp_path,
        )
