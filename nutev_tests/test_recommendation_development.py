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

from recommendation_candidate_drafting import READINESS_NOT_EVALUATED, _recommendation_root  # noqa: E402
from recommendation_development import (  # noqa: E402
    CANONICAL_RECOMMENDATION_DEVELOPMENT_RECORD_TYPE,
    DEVELOPMENT_METHOD,
    DRAFT,
    FINALIZED,
    STRENGTH_NOT_EVALUATED,
    SynthesisGovernanceError,
    _development_root,
    _record_path,
    finalize_recommendation_development,
    recommendation_development_status,
    stage_recommendation_development,
)
from recommendation_human_validation import (  # noqa: E402
    ACCEPT,
    REJECT,
    REVISE,
    _record_path as _validation_record_path,
    _validation_root,
    decide_recommendation_human_validation,
    stage_recommendation_human_validation,
)
from test_evidence_claim_review import _write_search_state  # noqa: E402
from test_recommendation_human_validation import (  # noqa: E402
    _decision_payload,
    _finalized_candidate,
    _stage_validation_payload,
)


def _validation(output_root: Path, decision: str = ACCEPT) -> tuple[str, str]:
    candidate_id = _finalized_candidate(output_root)
    staged = stage_recommendation_human_validation(
        _stage_validation_payload(candidate_id), output_root=output_root
    )
    validation_id = str(staged["cases"][0]["validation_id"])
    decide_recommendation_human_validation(
        _decision_payload(validation_id, decision), output_root=output_root
    )
    return validation_id, candidate_id


def _development_payload(validation_id: str) -> dict:
    return {
        "human_validation_id": validation_id,
        "proposed_recommendation_text": (
            "Consider structured food-literacy support only when the target population and implementation context "
            "match the evidence and review scope documented upstream."
        ),
        "population_scope": (
            "Adults represented by the accepted candidate and its linked EvidenceSets, within the declared review scope."
        ),
        "intervention_or_action": (
            "Structured food-literacy support delivered by qualified nutrition or lifestyle-medicine professionals."
        ),
        "comparator_or_alternative": "Usual care, no structured support, or context-appropriate alternatives.",
        "benefits_summary": (
            "Potential benefits must be considered from the source-linked EvidenceSets without treating membership, "
            "frequency, or favorable appraisal labels as pooled benefit magnitude."
        ),
        "harms_burdens_summary": (
            "Potential harms, burdens, opportunity costs, implementation demands, and mismatch risks require explicit "
            "human consideration and are not inferred automatically from the EvidenceSets."
        ),
        "values_preferences_summary": (
            "Patient and stakeholder values and preferences may vary across settings; this worksheet records a human "
            "consideration only and does not claim that preferences were formally measured."
        ),
        "resources_summary": (
            "Resource implications include professional time, training, access, service capacity, and follow-up needs; "
            "no formal health-economic analysis is claimed."
        ),
        "equity_summary": (
            "Equity considerations include differential access, literacy, affordability, cultural fit, and risk that "
            "implementation could widen existing disparities."
        ),
        "acceptability_summary": (
            "Acceptability may differ for patients, professionals, services, and communities and requires contextual "
            "human review rather than automatic inference."
        ),
        "feasibility_summary": (
            "Feasibility depends on workforce, workflow, infrastructure, time, continuity, and local implementation "
            "conditions that are not established by the evidence set alone."
        ),
        "implementation_considerations": (
            "Implementation should preserve scope, population fit, professional accountability, monitoring, and a "
            "clear route for revisiting the recommendation if context or evidence changes."
        ),
        "uncertainty_notes": (
            "Important uncertainty remains because this generic worksheet does not perform certainty grading, formal "
            "risk-of-bias assessment, pooled effects, or a validated Evidence-to-Decision framework."
        ),
        "developer_rationale": (
            "The proposed wording is intentionally bounded to the accepted HumanValidation scope and records decision "
            "considerations without promoting the candidate into a formal clinical or guideline recommendation."
        ),
        "prepared_by": "Recommendation Development Editor",
        "human_authorship_confirmed": True,
        "generic_method_confirmed": True,
    }


def _finalize_payload(development_id: str) -> dict:
    return {
        "development_id": development_id,
        "finalizer": "Recommendation Development Finalizer",
        "finalization_rationale": (
            "All required human-entered considerations and provenance are present for a canonical development worksheet, "
            "while recommendation strength and formal recommendation status remain explicitly unevaluated."
        ),
        "no_grade_etd_claim_confirmed": True,
        "strength_not_evaluated_confirmed": True,
        "not_formal_recommendation_confirmed": True,
        "upstream_immutable_confirmed": True,
    }


@pytest.mark.parametrize("decision", [REJECT, REVISE])
def test_stage_requires_accept_human_validation(tmp_path: Path, decision: str) -> None:
    validation_id, _ = _validation(tmp_path, decision)
    with pytest.raises(SynthesisGovernanceError, match="ACCEPT"):
        stage_recommendation_development(
            _development_payload(validation_id), output_root=tmp_path
        )


def test_stage_creates_generic_draft_without_formal_recommendation(tmp_path: Path) -> None:
    validation_id, candidate_id = _validation(tmp_path, ACCEPT)
    staged = stage_recommendation_development(
        _development_payload(validation_id), output_root=tmp_path
    )

    assert staged["method"] == DEVELOPMENT_METHOD
    assert staged["counts"][DRAFT] == 1
    assert staged["counts"][FINALIZED] == 0
    assert staged["recommendation_strength_default"] == STRENGTH_NOT_EVALUATED
    draft = staged["drafts"][0]
    assert draft["human_validation_id"] == validation_id
    assert draft["recommendation_candidate_id"] == candidate_id
    assert draft["recommendation_strength"] == STRENGTH_NOT_EVALUATED


def test_stage_is_idempotent_but_conflicting_restaging_is_blocked(tmp_path: Path) -> None:
    validation_id, _ = _validation(tmp_path, ACCEPT)
    payload = _development_payload(validation_id)
    first = stage_recommendation_development(payload, output_root=tmp_path)
    second = stage_recommendation_development(payload, output_root=tmp_path)
    assert first["draft_count"] == 1
    assert second["draft_count"] == 1

    conflicting = _development_payload(validation_id)
    conflicting["proposed_recommendation_text"] += " Different wording."
    with pytest.raises(SynthesisGovernanceError, match="conteúdo diferente"):
        stage_recommendation_development(conflicting, output_root=tmp_path)


def test_finalize_creates_canonical_development_record_not_recommendation(tmp_path: Path) -> None:
    validation_id, candidate_id = _validation(tmp_path, ACCEPT)
    staged = stage_recommendation_development(
        _development_payload(validation_id), output_root=tmp_path
    )
    development_id = str(staged["drafts"][0]["development_id"])
    finalized = finalize_recommendation_development(
        _finalize_payload(development_id), output_root=tmp_path
    )

    assert finalized["counts"][FINALIZED] == 1
    assert finalized["finalized_development_count"] == 1
    item = finalized["finalized_developments"][0]
    assert item["human_validation_id"] == validation_id
    assert item["recommendation_candidate_id"] == candidate_id
    assert item["recommendation_strength"] == STRENGTH_NOT_EVALUATED
    assert item["grade_etd_applied"] is False
    assert item["validated_recommendation_created"] is False
    assert item["clinical_recommendation_created"] is False
    assert item["guideline_recommendation_created"] is False

    record = json.loads(
        _record_path(_development_root(tmp_path), development_id).read_text(encoding="utf-8")
    )
    assert (
        record["recommendation_development_record_type"]
        == CANONICAL_RECOMMENDATION_DEVELOPMENT_RECORD_TYPE
    )
    assert record["canonical"] is True
    assert record["human_finalized"] is True
    assert record["method"] == DEVELOPMENT_METHOD
    assert record["development"]["recommendation_strength"] == STRENGTH_NOT_EVALUATED
    assert record["guardrails"]["source_human_validation_accept_revalidated"] is True
    assert record["guardrails"]["source_candidate_revalidated"] is True
    assert record["guardrails"]["automatic_recommendation_generation_performed"] is False
    assert record["guardrails"]["candidate_statement_auto_promoted"] is False
    assert record["guardrails"]["recommendation_strength_evaluated"] is False
    assert record["guardrails"]["formal_etd_framework_applied"] is False
    assert record["guardrails"]["grade_etd_applied"] is False
    assert record["guardrails"]["certainty_assessed"] is False
    assert record["guardrails"]["grade_assessed"] is False
    assert record["guardrails"]["formal_risk_of_bias_assessed"] is False
    assert record["guardrails"]["formal_benefit_harm_balance_determined"] is False
    assert record["guardrails"]["values_preferences_formally_assessed"] is False
    assert record["guardrails"]["resource_use_formally_assessed"] is False
    assert record["guardrails"]["equity_formally_assessed"] is False
    assert record["guardrails"]["acceptability_formally_assessed"] is False
    assert record["guardrails"]["feasibility_formally_assessed"] is False
    assert record["guardrails"]["recommendation_development_record_created"] is True
    assert record["guardrails"]["validated_recommendation_created"] is False
    assert record["guardrails"]["clinical_recommendation_created"] is False
    assert record["guardrails"]["guideline_recommendation_created"] is False
    assert record["guardrails"]["canonical_scientific_synthesis_created"] is False
    assert record["guardrails"]["meta_analysis_performed"] is False
    assert record["guardrails"]["prisma_event_emitted"] is False


def test_finalize_requires_all_boundary_confirmations(tmp_path: Path) -> None:
    validation_id, _ = _validation(tmp_path, ACCEPT)
    staged = stage_recommendation_development(
        _development_payload(validation_id), output_root=tmp_path
    )
    development_id = str(staged["drafts"][0]["development_id"])

    for key, expected in (
        ("no_grade_etd_claim_confirmed", "GRADE Evidence-to-Decision"),
        ("strength_not_evaluated_confirmed", "força"),
        ("not_formal_recommendation_confirmed", "clinical/guideline"),
        ("upstream_immutable_confirmed", "imutáveis"),
    ):
        payload = _finalize_payload(development_id)
        payload[key] = False
        with pytest.raises(SynthesisGovernanceError, match=expected):
            finalize_recommendation_development(payload, output_root=tmp_path)


def test_finalize_fails_closed_when_context_changes_after_staging(tmp_path: Path) -> None:
    validation_id, _ = _validation(tmp_path, ACCEPT)
    staged = stage_recommendation_development(
        _development_payload(validation_id), output_root=tmp_path
    )
    development_id = str(staged["drafts"][0]["development_id"])
    _write_search_state(tmp_path, database_sha="f" * 64)

    with pytest.raises(SynthesisGovernanceError, match="contexto|Context fingerprint|restage"):
        finalize_recommendation_development(
            _finalize_payload(development_id), output_root=tmp_path
        )

    current = recommendation_development_status(output_root=tmp_path)
    assert current["counts"][DRAFT] == 1
    assert current["finalized_development_count"] == 0


def test_development_does_not_mutate_human_validation_or_candidate(tmp_path: Path) -> None:
    validation_id, candidate_id = _validation(tmp_path, ACCEPT)
    validation_path = _validation_record_path(_validation_root(tmp_path), validation_id)
    candidate_path = _recommendation_root(tmp_path) / "finalized" / f"{candidate_id}.json"
    before_validation = validation_path.read_bytes()
    before_candidate = candidate_path.read_bytes()

    staged = stage_recommendation_development(
        _development_payload(validation_id), output_root=tmp_path
    )
    finalize_recommendation_development(
        _finalize_payload(str(staged["drafts"][0]["development_id"])), output_root=tmp_path
    )

    assert validation_path.read_bytes() == before_validation
    assert candidate_path.read_bytes() == before_candidate
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    assert candidate["recommendation_candidate"]["readiness"] == READINESS_NOT_EVALUATED
    assert candidate["guardrails"]["recommendation_validated"] is False
    assert candidate["guardrails"]["clinical_recommendation_created"] is False
