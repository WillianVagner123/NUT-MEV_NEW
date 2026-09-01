from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"
TESTS = ROOT / "nutev_tests"
for path in (WEB, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from recommendation_candidate_drafting import (  # noqa: E402
    READINESS_NOT_EVALUATED,
    _recommendation_root,
    finalize_recommendation_candidate,
    stage_recommendation_candidate,
)
from recommendation_human_validation import (  # noqa: E402
    ACCEPT,
    CANONICAL_HUMAN_VALIDATION_RECORD_TYPE,
    PENDING,
    REJECT,
    REVISE,
    SynthesisGovernanceError,
    _record_path,
    _validation_root,
    decide_recommendation_human_validation,
    recommendation_human_validation_status,
    stage_recommendation_human_validation,
)
from test_evidence_claim_review import _write_search_state  # noqa: E402
from test_recommendation_candidate_drafting import (  # noqa: E402
    _finalize_candidate_payload,
    _finalized_sets,
    _stage_candidate_payload,
)


def _finalized_candidate(output_root: Path) -> str:
    evidence_set_ids = _finalized_sets(output_root)
    staged = stage_recommendation_candidate(
        _stage_candidate_payload(evidence_set_ids), output_root=output_root
    )
    finalized = finalize_recommendation_candidate(
        _finalize_candidate_payload(staged["drafts"][0]["draft_id"]), output_root=output_root
    )
    return str(finalized["finalized_recommendation_candidates"][0]["recommendation_candidate_id"])


def _stage_validation_payload(candidate_id: str) -> dict:
    return {
        "recommendation_candidate_id": candidate_id,
        "staged_by": "Human Validation Coordinator",
        "review_scope": (
            "Assess whether the candidate wording is acceptable for the explicitly declared scientific audience "
            "and context, without converting it into a clinical guideline recommendation."
        ),
    }


def _decision_payload(validation_id: str, decision: str) -> dict:
    payload = {
        "validation_id": validation_id,
        "decision": decision,
        "reviewer": "Independent Human Reviewer",
        "rationale": (
            "The decision reflects an explicit human review of the candidate wording, provenance, declared "
            "audience, context, and boundaries without inferring certainty or clinical recommendation status."
        ),
        "revision_instructions": "",
        "decision_human_entered_confirmed": True,
        "decision_is_not_certainty_confirmed": True,
        "decision_is_not_clinical_recommendation_confirmed": True,
        "upstream_candidate_immutable_confirmed": True,
    }
    if decision == REVISE:
        payload["revision_instructions"] = (
            "Narrow the wording to the declared population and context before creating a new candidate record."
        )
    return payload


def test_stage_requires_finalized_recommendation_candidate(tmp_path: Path) -> None:
    with pytest.raises((FileNotFoundError, SynthesisGovernanceError)):
        stage_recommendation_human_validation(
            _stage_validation_payload("recommendation_candidate_missing"), output_root=tmp_path
        )


def test_staging_creates_pending_case_only_and_is_operator_idempotent(tmp_path: Path) -> None:
    candidate_id = _finalized_candidate(tmp_path)
    first = stage_recommendation_human_validation(
        _stage_validation_payload(candidate_id), output_root=tmp_path
    )
    payload = _stage_validation_payload(candidate_id)
    payload["staged_by"] = "Another Validation Coordinator"
    second = stage_recommendation_human_validation(payload, output_root=tmp_path)

    assert first["case_count"] == 1
    assert second["case_count"] == 1
    assert second["counts"][PENDING] == 1
    assert second["finalized_validation_count"] == 0
    assert second["cases"][0]["decision"] == "pending"
    assert second["cases"][0]["readiness"] == READINESS_NOT_EVALUATED


@pytest.mark.parametrize(
    ("decision", "model_decision", "accepted"),
    [
        (ACCEPT, "accept", True),
        (REJECT, "reject", False),
        (REVISE, "revise", False),
    ],
)
def test_human_decisions_create_canonical_validation_without_clinical_promotion(
    tmp_path: Path, decision: str, model_decision: str, accepted: bool
) -> None:
    candidate_id = _finalized_candidate(tmp_path)
    staged = stage_recommendation_human_validation(
        _stage_validation_payload(candidate_id), output_root=tmp_path
    )
    validation_id = str(staged["cases"][0]["validation_id"])
    decided = decide_recommendation_human_validation(
        _decision_payload(validation_id, decision), output_root=tmp_path
    )

    assert decided["counts"][decision] == 1
    assert decided["finalized_validation_count"] == 1
    item = decided["finalized_validations"][0]
    assert item["decision"] == model_decision
    assert item["candidate_accepted_for_declared_scope"] is accepted
    assert item["readiness_changed"] is False
    assert item["clinical_recommendation_created"] is False

    record = json.loads(
        _record_path(_validation_root(tmp_path), validation_id).read_text(encoding="utf-8")
    )
    assert record["human_validation_record_type"] == CANONICAL_HUMAN_VALIDATION_RECORD_TYPE
    assert record["canonical"] is True
    assert record["human_finalized"] is True
    validation = record["human_validation"]
    assert validation["id"] == validation_id
    assert validation["target_type"] == "RecommendationCandidate"
    assert validation["target_id"] == candidate_id
    assert validation["decision"] == model_decision
    assert validation["metadata"]["candidate_accepted_for_declared_scope"] is accepted
    assert record["guardrails"]["human_validation_created"] is True
    assert record["guardrails"]["human_validation_decision_recorded"] is True
    assert record["guardrails"]["automatic_validation_decision_performed"] is False
    assert record["guardrails"]["automatic_revision_applied"] is False
    assert record["guardrails"]["target_revalidated_at_decision"] is True
    assert record["guardrails"]["recommendation_candidate_changed"] is False
    assert record["guardrails"]["readiness_changed"] is False
    assert record["guardrails"]["readiness_evaluated"] is False
    assert record["guardrails"]["validated_recommendation_created"] is False
    assert record["guardrails"]["clinical_recommendation_created"] is False
    assert record["guardrails"]["guideline_recommendation_created"] is False
    assert record["guardrails"]["certainty_assessed"] is False
    assert record["guardrails"]["grade_assessed"] is False
    assert record["guardrails"]["formal_risk_of_bias_assessed"] is False
    assert record["guardrails"]["canonical_scientific_synthesis_created"] is False
    assert record["guardrails"]["meta_analysis_performed"] is False
    assert record["guardrails"]["prisma_event_emitted"] is False
    assert record["guardrails"]["identity_cryptographically_authenticated"] is False


def test_revise_requires_instructions_and_other_decisions_forbid_them(tmp_path: Path) -> None:
    candidate_id = _finalized_candidate(tmp_path)
    staged = stage_recommendation_human_validation(
        _stage_validation_payload(candidate_id), output_root=tmp_path
    )
    validation_id = str(staged["cases"][0]["validation_id"])

    revise = _decision_payload(validation_id, REVISE)
    revise["revision_instructions"] = "too short"
    with pytest.raises(SynthesisGovernanceError, match="REVISE exige"):
        decide_recommendation_human_validation(revise, output_root=tmp_path)

    accept = _decision_payload(validation_id, ACCEPT)
    accept["revision_instructions"] = "Do something anyway"
    with pytest.raises(SynthesisGovernanceError, match="só são permitidas"):
        decide_recommendation_human_validation(accept, output_root=tmp_path)


def test_decision_requires_all_boundary_confirmations(tmp_path: Path) -> None:
    candidate_id = _finalized_candidate(tmp_path)
    staged = stage_recommendation_human_validation(
        _stage_validation_payload(candidate_id), output_root=tmp_path
    )
    validation_id = str(staged["cases"][0]["validation_id"])

    for key, expected in (
        ("decision_human_entered_confirmed", "humano"),
        ("decision_is_not_certainty_confirmed", "certainty"),
        ("decision_is_not_clinical_recommendation_confirmed", "clinical"),
        ("upstream_candidate_immutable_confirmed", "não reescreve"),
    ):
        payload = _decision_payload(validation_id, ACCEPT)
        payload[key] = False
        with pytest.raises(SynthesisGovernanceError, match=expected):
            decide_recommendation_human_validation(payload, output_root=tmp_path)


def test_final_decision_is_idempotent_but_conflicting_overwrite_is_blocked(tmp_path: Path) -> None:
    candidate_id = _finalized_candidate(tmp_path)
    staged = stage_recommendation_human_validation(
        _stage_validation_payload(candidate_id), output_root=tmp_path
    )
    validation_id = str(staged["cases"][0]["validation_id"])
    payload = _decision_payload(validation_id, ACCEPT)

    first = decide_recommendation_human_validation(payload, output_root=tmp_path)
    second = decide_recommendation_human_validation(payload, output_root=tmp_path)
    assert first["finalized_validations"][0]["decision"] == "accept"
    assert second["finalized_validations"][0]["decision"] == "accept"

    conflicting = _decision_payload(validation_id, REJECT)
    with pytest.raises(SynthesisGovernanceError, match="não podem sobrescrevê-la"):
        decide_recommendation_human_validation(conflicting, output_root=tmp_path)


def test_decision_fails_closed_when_context_changes_after_staging(tmp_path: Path) -> None:
    candidate_id = _finalized_candidate(tmp_path)
    staged = stage_recommendation_human_validation(
        _stage_validation_payload(candidate_id), output_root=tmp_path
    )
    validation_id = str(staged["cases"][0]["validation_id"])
    _write_search_state(tmp_path, database_sha="f" * 64)

    with pytest.raises(SynthesisGovernanceError, match="contexto|Context fingerprint|restage"):
        decide_recommendation_human_validation(
            _decision_payload(validation_id, ACCEPT), output_root=tmp_path
        )

    current = recommendation_human_validation_status(output_root=tmp_path)
    assert current["counts"][PENDING] == 1
    assert current["finalized_validation_count"] == 0


def test_human_validation_does_not_mutate_recommendation_candidate(tmp_path: Path) -> None:
    candidate_id = _finalized_candidate(tmp_path)
    candidate_path = _recommendation_root(tmp_path) / "finalized" / f"{candidate_id}.json"
    before = candidate_path.read_bytes()

    staged = stage_recommendation_human_validation(
        _stage_validation_payload(candidate_id), output_root=tmp_path
    )
    validation_id = str(staged["cases"][0]["validation_id"])
    decide_recommendation_human_validation(
        _decision_payload(validation_id, ACCEPT), output_root=tmp_path
    )

    assert candidate_path.read_bytes() == before
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    assert candidate["recommendation_candidate"]["readiness"] == READINESS_NOT_EVALUATED
    assert candidate["guardrails"]["recommendation_validated"] is False
    assert candidate["guardrails"]["human_validation_created"] is False
    assert candidate["guardrails"]["clinical_recommendation_created"] is False
