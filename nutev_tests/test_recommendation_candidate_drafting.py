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

from evidence_set_construction import _set_root, finalize_evidence_set, stage_evidence_set  # noqa: E402
from recommendation_candidate_drafting import (  # noqa: E402
    CANONICAL_RECOMMENDATION_CANDIDATE_RECORD_TYPE,
    DRAFT,
    FINALIZED,
    READINESS_NOT_EVALUATED,
    SynthesisGovernanceError,
    _recommendation_root,
    finalize_recommendation_candidate,
    recommendation_candidate_status,
    stage_recommendation_candidate,
)
from test_evidence_claim_review import _write_search_state  # noqa: E402
from test_evidence_set_construction import (  # noqa: E402
    _evaluated_claims,
    _finalize_payload_for_set,
    _stage_payload,
)


def _finalized_sets(output_root: Path) -> list[str]:
    claim_ids = _evaluated_claims(output_root)

    first = stage_evidence_set(
        _stage_payload(claim_ids, name="Food literacy evidence"), output_root=output_root
    )
    finalize_evidence_set(_finalize_payload_for_set(first["drafts"][0]), output_root=output_root)

    second_payload = _stage_payload([claim_ids[0]], name="Implementation context evidence")
    second_payload["lens"] = "implementation_context"
    second_payload["focus_statement"] = (
        "Organize one evaluated source-level claim under a separate implementation-context evidence lens."
    )
    second = stage_evidence_set(second_payload, output_root=output_root)
    second_draft = next(item for item in second["drafts"] if item["status"] == "DRAFT")
    final = finalize_evidence_set(_finalize_payload_for_set(second_draft), output_root=output_root)
    return [str(item["evidence_set_id"]) for item in final["finalized_evidence_sets"]]


def _stage_candidate_payload(evidence_set_ids: list[str]) -> dict:
    return {
        "statement": (
            "Consider structured food-literacy support when the intended context matches the populations and "
            "outcomes represented in the linked EvidenceSets."
        ),
        "rationale": (
            "This wording is a human-authored candidate for later validation and intentionally remains narrower "
            "than a clinical recommendation or certainty statement."
        ),
        "intended_audience": "Lifestyle medicine and nutrition professionals",
        "intended_context": "Scientific discussion of structured food-literacy support",
        "evidence_set_ids": evidence_set_ids,
        "staged_by": "Recommendation Coordinator",
        "statement_human_authored_confirmed": True,
    }


def _finalize_candidate_payload(draft_id: str) -> dict:
    return {
        "draft_id": draft_id,
        "finalizer": "Recommendation Candidate Editor",
        "finalization_rationale": (
            "The candidate wording and provenance are complete enough for a later explicit HumanValidation step, "
            "without changing readiness or claiming scientific certainty."
        ),
        "evidence_sets_are_not_certainty_confirmed": True,
        "candidate_is_not_validated_recommendation_confirmed": True,
        "human_validation_required_confirmed": True,
    }


def test_stage_requires_finalized_evidence_set(tmp_path: Path) -> None:
    with pytest.raises((FileNotFoundError, SynthesisGovernanceError)):
        stage_recommendation_candidate(
            _stage_candidate_payload(["evidence_set_missing"]), output_root=tmp_path
        )


def test_staging_is_order_and_operator_idempotent_and_never_finalizes(tmp_path: Path) -> None:
    evidence_set_ids = _finalized_sets(tmp_path)
    first = stage_recommendation_candidate(
        _stage_candidate_payload(evidence_set_ids), output_root=tmp_path
    )
    payload = _stage_candidate_payload(list(reversed(evidence_set_ids)))
    payload["staged_by"] = "Another Coordinator"
    second = stage_recommendation_candidate(payload, output_root=tmp_path)

    assert first["draft_count"] == 1
    assert second["draft_count"] == 1
    assert first["drafts"][0]["draft_id"] == second["drafts"][0]["draft_id"]
    assert second["draft_counts"][DRAFT] == 1
    assert second["finalized_recommendation_candidate_count"] == 0
    assert second["readiness_default"] == READINESS_NOT_EVALUATED


def test_finalize_creates_candidate_record_without_validating_recommendation(tmp_path: Path) -> None:
    evidence_set_ids = _finalized_sets(tmp_path)
    staged = stage_recommendation_candidate(
        _stage_candidate_payload(evidence_set_ids), output_root=tmp_path
    )
    draft_id = staged["drafts"][0]["draft_id"]

    finalized = finalize_recommendation_candidate(
        _finalize_candidate_payload(draft_id), output_root=tmp_path
    )

    assert finalized["draft_counts"][FINALIZED] == 1
    assert finalized["finalized_recommendation_candidate_count"] == 1
    item = finalized["finalized_recommendation_candidates"][0]
    assert item["readiness"] == READINESS_NOT_EVALUATED
    assert item["recommendation_validated"] is False
    assert item["clinical_recommendation_created"] is False

    candidate_id = item["recommendation_candidate_id"]
    record = json.loads(
        (
            _recommendation_root(tmp_path)
            / "finalized"
            / f"{candidate_id}.json"
        ).read_text(encoding="utf-8")
    )
    assert (
        record["recommendation_candidate_record_type"]
        == CANONICAL_RECOMMENDATION_CANDIDATE_RECORD_TYPE
    )
    assert record["canonical"] is True
    assert record["human_finalized"] is True
    candidate = record["recommendation_candidate"]
    assert candidate["id"] == candidate_id
    assert candidate["readiness"] == READINESS_NOT_EVALUATED
    assert set(candidate["evidence_set_ids"]) == set(evidence_set_ids)
    assert record["guardrails"]["recommendation_candidate_created"] is True
    assert record["guardrails"]["automatic_statement_generation_performed"] is False
    assert record["guardrails"]["automatic_readiness_inference_performed"] is False
    assert record["guardrails"]["readiness_evaluated"] is False
    assert record["guardrails"]["recommendation_validated"] is False
    assert record["guardrails"]["human_validation_created"] is False
    assert record["guardrails"]["evidence_set_agreement_inferred"] is False
    assert record["guardrails"]["evidence_set_scores_aggregated"] is False
    assert record["guardrails"]["certainty_assessed"] is False
    assert record["guardrails"]["overall_certainty_grade_created"] is False
    assert record["guardrails"]["formal_risk_of_bias_assessed"] is False
    assert record["guardrails"]["clinical_recommendation_created"] is False
    assert record["guardrails"]["canonical_scientific_synthesis_created"] is False
    assert record["guardrails"]["meta_analysis_performed"] is False
    assert record["guardrails"]["prisma_event_emitted"] is False


def test_stage_requires_human_authorship_confirmation(tmp_path: Path) -> None:
    evidence_set_ids = _finalized_sets(tmp_path)
    payload = _stage_candidate_payload(evidence_set_ids)
    payload["statement_human_authored_confirmed"] = False
    with pytest.raises(SynthesisGovernanceError, match="escrito por humano"):
        stage_recommendation_candidate(payload, output_root=tmp_path)


def test_finalize_requires_all_scientific_confirmations(tmp_path: Path) -> None:
    evidence_set_ids = _finalized_sets(tmp_path)
    staged = stage_recommendation_candidate(
        _stage_candidate_payload(evidence_set_ids), output_root=tmp_path
    )
    draft_id = staged["drafts"][0]["draft_id"]

    for key, expected in (
        ("evidence_sets_are_not_certainty_confirmed", "certainty"),
        ("candidate_is_not_validated_recommendation_confirmed", "não é recomendação validada"),
        ("human_validation_required_confirmed", "HumanValidation"),
    ):
        payload = _finalize_candidate_payload(draft_id)
        payload[key] = False
        with pytest.raises(SynthesisGovernanceError, match=expected):
            finalize_recommendation_candidate(payload, output_root=tmp_path)


def test_finalize_fails_closed_when_context_changes_after_staging(tmp_path: Path) -> None:
    evidence_set_ids = _finalized_sets(tmp_path)
    staged = stage_recommendation_candidate(
        _stage_candidate_payload(evidence_set_ids), output_root=tmp_path
    )
    draft_id = staged["drafts"][0]["draft_id"]
    _write_search_state(tmp_path, database_sha="f" * 64)

    with pytest.raises(SynthesisGovernanceError, match="contexto|Context fingerprint|restage"):
        finalize_recommendation_candidate(
            _finalize_candidate_payload(draft_id), output_root=tmp_path
        )

    current = recommendation_candidate_status(output_root=tmp_path)
    assert current["draft_counts"][DRAFT] == 1
    assert current["finalized_recommendation_candidate_count"] == 0


def test_finalization_does_not_mutate_evidence_set_artifacts(tmp_path: Path) -> None:
    evidence_set_ids = _finalized_sets(tmp_path)
    set_root = _set_root(tmp_path)
    before = {
        evidence_set_id: (set_root / "finalized" / f"{evidence_set_id}.json").read_bytes()
        for evidence_set_id in evidence_set_ids
    }

    staged = stage_recommendation_candidate(
        _stage_candidate_payload(evidence_set_ids), output_root=tmp_path
    )
    finalize_recommendation_candidate(
        _finalize_candidate_payload(staged["drafts"][0]["draft_id"]), output_root=tmp_path
    )

    for evidence_set_id in evidence_set_ids:
        assert (
            set_root / "finalized" / f"{evidence_set_id}.json"
        ).read_bytes() == before[evidence_set_id]
