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

from recommendation_adoption import (  # noqa: E402
    ADOPT_FOR_DEFINED_SCOPE,
    CANONICAL_RECOMMENDATION_ADOPTION_RECORD_TYPE,
    PENDING,
    REJECT,
    RETURN_FOR_REVISION,
    SynthesisGovernanceError,
    _adoption_root,
    _record_path,
    decide_recommendation_adoption,
    recommendation_adoption_status,
    stage_recommendation_adoption,
)
from recommendation_development import (  # noqa: E402
    STRENGTH_NOT_EVALUATED,
    _development_root,
    _record_path as _development_record_path,
    finalize_recommendation_development,
    stage_recommendation_development,
)
from test_evidence_claim_review import _write_search_state  # noqa: E402
from test_recommendation_development import (  # noqa: E402
    _development_payload,
    _finalize_payload,
    _validation,
)


def _finalized_development(output_root: Path) -> str:
    validation_id, _ = _validation(output_root)
    staged = stage_recommendation_development(
        _development_payload(validation_id), output_root=output_root
    )
    development_id = str(staged["drafts"][0]["development_id"])
    finalize_recommendation_development(
        _finalize_payload(development_id), output_root=output_root
    )
    return development_id


def _stage_payload(development_id: str) -> dict:
    return {
        "recommendation_development_id": development_id,
        "staged_by": "Recommendation Governance Coordinator",
        "adoption_scope": (
            "Use of the human-authored recommendation wording only within the explicitly documented target "
            "population, professional audience, and implementation context represented by the upstream review."
        ),
        "governance_purpose": (
            "Decide whether the finalized development wording may be adopted for a bounded operational scientific "
            "scope without assigning recommendation strength, certainty, or guideline status."
        ),
    }


def _decision_payload(adoption_id: str, decision: str) -> dict:
    payload = {
        "adoption_id": adoption_id,
        "decision": decision,
        "governor": "Independent Recommendation Governor",
        "rationale": (
            "This explicit human governance decision considers the finalized development record and its declared "
            "scope while preserving the boundary that adoption does not establish strength, certainty, GRADE, or "
            "universal clinical or guideline recommendation status."
        ),
        "revision_instructions": "",
        "decision_human_entered_confirmed": True,
        "defined_scope_only_confirmed": True,
        "no_strength_or_certainty_inference_confirmed": True,
        "not_clinical_or_guideline_recommendation_confirmed": True,
        "upstream_immutable_confirmed": True,
    }
    if decision == RETURN_FOR_REVISION:
        payload["revision_instructions"] = (
            "Narrow the wording or scope and create a new development record before a new governance decision."
        )
    return payload


def test_stage_requires_finalized_development(tmp_path: Path) -> None:
    with pytest.raises((FileNotFoundError, SynthesisGovernanceError)):
        stage_recommendation_adoption(
            _stage_payload("recommendation_development_missing"), output_root=tmp_path
        )


def test_stage_creates_pending_case_only_and_is_operator_idempotent(tmp_path: Path) -> None:
    development_id = _finalized_development(tmp_path)
    first = stage_recommendation_adoption(_stage_payload(development_id), output_root=tmp_path)
    payload = _stage_payload(development_id)
    payload["staged_by"] = "Another Governance Coordinator"
    second = stage_recommendation_adoption(payload, output_root=tmp_path)

    assert first["case_count"] == 1
    assert second["case_count"] == 1
    assert second["counts"][PENDING] == 1
    assert second["finalized_adoption_count"] == 0
    assert second["cases"][0]["decision"] == "pending"
    assert second["cases"][0]["recommendation_strength"] == STRENGTH_NOT_EVALUATED


@pytest.mark.parametrize(
    ("decision", "model_decision", "adopted"),
    [
        (ADOPT_FOR_DEFINED_SCOPE, "adopt_for_defined_scope", True),
        (REJECT, "reject", False),
        (RETURN_FOR_REVISION, "return_for_revision", False),
    ],
)
def test_human_decisions_create_canonical_adoption_without_strength_or_guideline_promotion(
    tmp_path: Path, decision: str, model_decision: str, adopted: bool
) -> None:
    development_id = _finalized_development(tmp_path)
    staged = stage_recommendation_adoption(_stage_payload(development_id), output_root=tmp_path)
    adoption_id = str(staged["cases"][0]["adoption_id"])
    decided = decide_recommendation_adoption(
        _decision_payload(adoption_id, decision), output_root=tmp_path
    )

    assert decided["counts"][decision] == 1
    assert decided["finalized_adoption_count"] == 1
    item = decided["finalized_adoptions"][0]
    assert item["decision"] == model_decision
    assert item["adopted_for_defined_scope"] is adopted
    assert item["recommendation_strength"] == STRENGTH_NOT_EVALUATED
    assert item["clinical_recommendation_created"] is False
    assert item["guideline_recommendation_created"] is False
    assert item["certainty_assessed"] is False

    record = json.loads(
        _record_path(_adoption_root(tmp_path), adoption_id).read_text(encoding="utf-8")
    )
    assert record["recommendation_adoption_record_type"] == CANONICAL_RECOMMENDATION_ADOPTION_RECORD_TYPE
    assert record["canonical"] is True
    assert record["human_finalized"] is True
    adoption = record["recommendation_adoption"]
    assert adoption["decision"] == model_decision
    assert adoption["recommendation_strength"] == STRENGTH_NOT_EVALUATED
    assert adoption["metadata"]["adopted_for_defined_scope"] is adopted
    assert record["guardrails"]["recommendation_adoption_record_created"] is True
    assert record["guardrails"]["source_recommendation_development_revalidated"] is True
    assert record["guardrails"]["automatic_adoption_decision_performed"] is False
    assert record["guardrails"]["automatic_revision_applied"] is False
    assert record["guardrails"]["recommendation_strength_evaluated"] is False
    assert record["guardrails"]["certainty_assessed"] is False
    assert record["guardrails"]["grade_assessed"] is False
    assert record["guardrails"]["formal_etd_framework_applied"] is False
    assert record["guardrails"]["grade_etd_applied"] is False
    assert record["guardrails"]["validated_recommendation_created"] is False
    assert record["guardrails"]["clinical_recommendation_created"] is False
    assert record["guardrails"]["guideline_recommendation_created"] is False
    assert record["guardrails"]["universal_recommendation_created"] is False
    assert record["guardrails"]["canonical_scientific_synthesis_created"] is False
    assert record["guardrails"]["meta_analysis_performed"] is False
    assert record["guardrails"]["prisma_event_emitted"] is False


def test_return_for_revision_requires_instructions_and_other_decisions_forbid_them(tmp_path: Path) -> None:
    development_id = _finalized_development(tmp_path)
    staged = stage_recommendation_adoption(_stage_payload(development_id), output_root=tmp_path)
    adoption_id = str(staged["cases"][0]["adoption_id"])

    revise = _decision_payload(adoption_id, RETURN_FOR_REVISION)
    revise["revision_instructions"] = "too short"
    with pytest.raises(SynthesisGovernanceError, match="RETURN_FOR_REVISION exige"):
        decide_recommendation_adoption(revise, output_root=tmp_path)

    adopt = _decision_payload(adoption_id, ADOPT_FOR_DEFINED_SCOPE)
    adopt["revision_instructions"] = "Do revision anyway despite adoption"
    with pytest.raises(SynthesisGovernanceError, match="só são permitidas"):
        decide_recommendation_adoption(adopt, output_root=tmp_path)


def test_decision_requires_all_boundary_confirmations(tmp_path: Path) -> None:
    development_id = _finalized_development(tmp_path)
    staged = stage_recommendation_adoption(_stage_payload(development_id), output_root=tmp_path)
    adoption_id = str(staged["cases"][0]["adoption_id"])

    for key, expected in (
        ("decision_human_entered_confirmed", "humano"),
        ("defined_scope_only_confirmed", "scope"),
        ("no_strength_or_certainty_inference_confirmed", "strength"),
        ("not_clinical_or_guideline_recommendation_confirmed", "clinical"),
        ("upstream_immutable_confirmed", "imutáveis"),
    ):
        payload = _decision_payload(adoption_id, ADOPT_FOR_DEFINED_SCOPE)
        payload[key] = False
        with pytest.raises(SynthesisGovernanceError, match=expected):
            decide_recommendation_adoption(payload, output_root=tmp_path)


def test_final_decision_is_idempotent_but_conflicting_overwrite_is_blocked(tmp_path: Path) -> None:
    development_id = _finalized_development(tmp_path)
    staged = stage_recommendation_adoption(_stage_payload(development_id), output_root=tmp_path)
    adoption_id = str(staged["cases"][0]["adoption_id"])
    payload = _decision_payload(adoption_id, ADOPT_FOR_DEFINED_SCOPE)

    first = decide_recommendation_adoption(payload, output_root=tmp_path)
    second = decide_recommendation_adoption(payload, output_root=tmp_path)
    assert first["finalized_adoptions"][0]["decision"] == "adopt_for_defined_scope"
    assert second["finalized_adoptions"][0]["decision"] == "adopt_for_defined_scope"

    with pytest.raises(SynthesisGovernanceError, match="não pode sobrescrevê-la"):
        decide_recommendation_adoption(
            _decision_payload(adoption_id, REJECT), output_root=tmp_path
        )


def test_decision_fails_closed_when_context_changes_after_staging(tmp_path: Path) -> None:
    development_id = _finalized_development(tmp_path)
    staged = stage_recommendation_adoption(_stage_payload(development_id), output_root=tmp_path)
    adoption_id = str(staged["cases"][0]["adoption_id"])
    _write_search_state(tmp_path, database_sha="f" * 64)

    with pytest.raises(SynthesisGovernanceError, match="contexto|Context fingerprint|restage"):
        decide_recommendation_adoption(
            _decision_payload(adoption_id, ADOPT_FOR_DEFINED_SCOPE), output_root=tmp_path
        )

    current = recommendation_adoption_status(output_root=tmp_path)
    assert current["counts"][PENDING] == 1
    assert current["finalized_adoption_count"] == 0


def test_adoption_does_not_mutate_recommendation_development(tmp_path: Path) -> None:
    development_id = _finalized_development(tmp_path)
    development_path = _development_record_path(
        _development_root(tmp_path), development_id
    )
    before = development_path.read_bytes()

    staged = stage_recommendation_adoption(_stage_payload(development_id), output_root=tmp_path)
    adoption_id = str(staged["cases"][0]["adoption_id"])
    decide_recommendation_adoption(
        _decision_payload(adoption_id, ADOPT_FOR_DEFINED_SCOPE), output_root=tmp_path
    )

    assert development_path.read_bytes() == before
    development = json.loads(development_path.read_text(encoding="utf-8"))
    assert development["development"]["recommendation_strength"] == STRENGTH_NOT_EVALUATED
    assert development["guardrails"]["validated_recommendation_created"] is False
    assert development["guardrails"]["clinical_recommendation_created"] is False
    assert development["guardrails"]["guideline_recommendation_created"] is False
