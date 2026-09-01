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

from claim_evaluation_appraisal import (  # noqa: E402
    APPRAISAL_METHOD,
    CANONICAL_EVALUATION_RECORD_TYPE,
    DIMENSIONS,
    FINALIZED,
    PENDING_APPRAISAL,
    SynthesisGovernanceError,
    _evaluation_root,
    claim_evaluation_status,
    finalize_claim_evaluation,
    stage_claim_evaluation,
)
from evidence_claim_review_gate import decide_claim_candidate  # noqa: E402
from test_evidence_claim_review import (  # noqa: E402
    _accept_payload,
    _candidate,
    _stage,
    _write_evidence_records,
    _write_search_state,
)


def _accepted_claim(output_root: Path) -> str:
    _write_search_state(output_root)
    status = _stage(output_root)
    _write_evidence_records(output_root)
    candidate_id = _candidate(status)["candidate_id"]
    decided = decide_claim_candidate(_accept_payload(candidate_id), output_root=output_root)
    return str(decided["accepted_claims"][0]["claim_id"])


def _dimensions() -> dict:
    return {
        "design_appropriateness": {
            "judgment": "FAVORABLE",
            "rationale": "The reported design is appropriate for this bounded descriptive claim.",
        },
        "internal_validity_appraisal": {
            "judgment": "SOME_CONCERNS",
            "rationale": "Some internal-validity details are not fully visible in the available material.",
        },
        "directness": {
            "judgment": "FAVORABLE",
            "rationale": "The reported population and outcome directly match the accepted claim wording.",
        },
        "precision": {
            "judgment": "FAVORABLE",
            "rationale": "The source snapshot reports an effect estimate, confidence interval and p value.",
        },
        "applicability": {
            "judgment": "UNCLEAR",
            "rationale": "Applicability beyond the reported study setting cannot be established from this claim alone.",
        },
        "reporting_completeness": {
            "judgment": "SOME_CONCERNS",
            "rationale": "The source-linked snapshot is informative but does not replace complete methodological reporting.",
        },
    }


def _finalize_payload(candidate_id: str) -> dict:
    return {
        "candidate_id": candidate_id,
        "assessor": "Scientific Appraiser",
        "rationale": (
            "This appraisal records dimension-specific human judgments for the accepted source-level claim "
            "without assigning an overall certainty grade."
        ),
        "assessment_basis": "SOURCE_SNAPSHOT_ONLY",
        "basis_details": "",
        "dimensions": _dimensions(),
        "nonformal_method_confirmed": True,
        "scientific_boundary_confirmed": True,
        "claim_scope_confirmed": True,
    }


def test_staging_is_claim_idempotent_and_never_finalizes(tmp_path: Path) -> None:
    claim_id = _accepted_claim(tmp_path)

    first = stage_claim_evaluation(
        {"claim_id": claim_id, "staged_by": "Operator One"}, output_root=tmp_path
    )
    second = stage_claim_evaluation(
        {"claim_id": claim_id, "staged_by": "Operator Two"}, output_root=tmp_path
    )

    assert first["candidate_count"] == 1
    assert second["candidate_count"] == 1
    assert first["candidates"][0]["candidate_id"] == second["candidates"][0]["candidate_id"]
    assert second["candidate_counts"][PENDING_APPRAISAL] == 1
    assert second["finalized_evaluation_count"] == 0
    assert second["appraisal_method"] == APPRAISAL_METHOD
    assert set(second["dimensions"]) == set(DIMENSIONS)


def test_finalize_creates_canonical_human_appraisal_without_certainty_or_rob(tmp_path: Path) -> None:
    claim_id = _accepted_claim(tmp_path)
    staged = stage_claim_evaluation(
        {"claim_id": claim_id, "staged_by": "Appraisal Coordinator"}, output_root=tmp_path
    )
    candidate_id = staged["candidates"][0]["candidate_id"]

    finalized = finalize_claim_evaluation(
        _finalize_payload(candidate_id), output_root=tmp_path
    )

    assert finalized["candidate_counts"][FINALIZED] == 1
    assert finalized["finalized_evaluation_count"] == 1
    item = finalized["finalized_evaluations"][0]
    assert item["claim_id"] == claim_id
    assert item["formal_risk_of_bias_assessed"] is False
    assert item["certainty_assessed"] is False

    evaluation_id = item["evaluation_id"]
    record = json.loads(
        (_evaluation_root(tmp_path) / "finalized" / f"{evaluation_id}.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["evaluation_record_type"] == CANONICAL_EVALUATION_RECORD_TYPE
    assert record["canonical"] is True
    assert record["human_finalized"] is True
    assert record["appraisal_method"] == APPRAISAL_METHOD
    assert record["claim_evaluation"]["claim_id"] == claim_id
    assert set(record["claim_evaluation"]["dimensions"]) == set(DIMENSIONS)
    assert record["methodology"]["formal_external_instrument"] is False
    assert record["methodology"]["numeric_score"] is False
    assert record["methodology"]["automatic_overall_judgment"] is False
    assert record["guardrails"]["claim_evaluation_created"] is True
    assert record["guardrails"]["formal_risk_of_bias_assessed"] is False
    assert record["guardrails"]["risk_of_bias_assessed"] is False
    assert record["guardrails"]["study_validity_determined"] is False
    assert record["guardrails"]["certainty_assessed"] is False
    assert record["guardrails"]["overall_certainty_grade_created"] is False
    assert record["guardrails"]["numeric_appraisal_score_created"] is False
    assert record["guardrails"]["automatic_dimension_aggregation_performed"] is False
    assert record["guardrails"]["evidence_set_created"] is False
    assert record["guardrails"]["clinical_recommendation_created"] is False
    assert record["guardrails"]["screening_eligibility_changed"] is False
    assert record["guardrails"]["accepted_claim_statement_changed"] is False
    assert record["guardrails"]["prisma_event_emitted"] is False
    assert "overall_score" not in record
    assert "certainty_grade" not in record


def test_finalize_requires_all_dimensions_and_dimension_rationales(tmp_path: Path) -> None:
    claim_id = _accepted_claim(tmp_path)
    staged = stage_claim_evaluation(
        {"claim_id": claim_id, "staged_by": "Appraisal Coordinator"}, output_root=tmp_path
    )
    candidate_id = staged["candidates"][0]["candidate_id"]

    payload = _finalize_payload(candidate_id)
    payload["dimensions"].pop("precision")
    with pytest.raises(SynthesisGovernanceError, match="Dimensions inválidas"):
        finalize_claim_evaluation(payload, output_root=tmp_path)

    payload = _finalize_payload(candidate_id)
    payload["dimensions"]["precision"]["rationale"] = "short"
    with pytest.raises(SynthesisGovernanceError, match="Rationale de precision"):
        finalize_claim_evaluation(payload, output_root=tmp_path)


def test_finalize_rejects_unknown_judgment_and_requires_explicit_confirmations(tmp_path: Path) -> None:
    claim_id = _accepted_claim(tmp_path)
    staged = stage_claim_evaluation(
        {"claim_id": claim_id, "staged_by": "Appraisal Coordinator"}, output_root=tmp_path
    )
    candidate_id = staged["candidates"][0]["candidate_id"]

    payload = _finalize_payload(candidate_id)
    payload["dimensions"]["directness"]["judgment"] = "HIGH_CERTAINTY"
    with pytest.raises(SynthesisGovernanceError, match="Judgment inválido"):
        finalize_claim_evaluation(payload, output_root=tmp_path)

    for key, expected in (
        ("nonformal_method_confirmed", "instrumento formal"),
        ("scientific_boundary_confirmed", "certainty"),
        ("claim_scope_confirmed", "claim avaliado"),
    ):
        payload = _finalize_payload(candidate_id)
        payload[key] = False
        with pytest.raises(SynthesisGovernanceError, match=expected):
            finalize_claim_evaluation(payload, output_root=tmp_path)


def test_other_assessment_basis_requires_details(tmp_path: Path) -> None:
    claim_id = _accepted_claim(tmp_path)
    staged = stage_claim_evaluation(
        {"claim_id": claim_id, "staged_by": "Appraisal Coordinator"}, output_root=tmp_path
    )
    candidate_id = staged["candidates"][0]["candidate_id"]
    payload = _finalize_payload(candidate_id)
    payload["assessment_basis"] = "OTHER"

    with pytest.raises(SynthesisGovernanceError, match="assessment basis OTHER"):
        finalize_claim_evaluation(payload, output_root=tmp_path)


def test_finalize_fails_closed_when_scientific_context_changes_after_staging(tmp_path: Path) -> None:
    claim_id = _accepted_claim(tmp_path)
    staged = stage_claim_evaluation(
        {"claim_id": claim_id, "staged_by": "Appraisal Coordinator"}, output_root=tmp_path
    )
    candidate_id = staged["candidates"][0]["candidate_id"]
    _write_search_state(tmp_path, database_sha="f" * 64)

    with pytest.raises(SynthesisGovernanceError, match="contexto científico atual|Context fingerprint"):
        finalize_claim_evaluation(_finalize_payload(candidate_id), output_root=tmp_path)

    current = claim_evaluation_status(output_root=tmp_path)
    assert current["candidate_counts"][PENDING_APPRAISAL] == 1
    assert current["finalized_evaluation_count"] == 0


def test_stage_requires_existing_accepted_claim_and_verified_evidence_record(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    with pytest.raises((FileNotFoundError, SynthesisGovernanceError)):
        stage_claim_evaluation(
            {"claim_id": "claim_missing", "staged_by": "Appraisal Coordinator"},
            output_root=tmp_path,
        )
