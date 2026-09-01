from __future__ import annotations

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
    _evaluation_root,
    claim_evaluation_status,
    finalize_claim_evaluation,
    stage_claim_evaluation,
)
from evidence_claim_review import _claim_path, _claim_root  # noqa: E402
from evidence_claim_review_gate import decide_claim_candidate  # noqa: E402
from evidence_set_construction import (  # noqa: E402
    CANONICAL_EVIDENCE_SET_RECORD_TYPE,
    DRAFT,
    FINALIZED,
    SynthesisGovernanceError,
    _set_root,
    evidence_set_status,
    finalize_evidence_set,
    stage_evidence_set,
)
from test_claim_evaluation_appraisal import _finalize_payload  # noqa: E402
from test_evidence_claim_review import (  # noqa: E402
    _accept_payload,
    _candidate,
    _stage,
    _write_evidence_records,
    _write_search_state,
)


def _accepted_claims(output_root: Path) -> list[str]:
    _write_search_state(output_root)
    status = _stage(output_root)
    _write_evidence_records(output_root)

    claim_ids: list[str] = []
    for document_id in ("doi:10.1000/a", "pmid:123456"):
        candidate_id = _candidate(status, document_id)["candidate_id"]
        payload = _accept_payload(candidate_id)
        if document_id == "pmid:123456":
            payload["claim_statement"] = (
                "Study B reported higher food-literacy scores after the comparator program at follow-up."
            )
        status = decide_claim_candidate(payload, output_root=output_root)
        evidence_record_id = f"evidence:{document_id}"
        claim = next(
            item
            for item in status["accepted_claims"]
            if item["evidence_record_id"] == evidence_record_id
        )
        claim_ids.append(str(claim["claim_id"]))
    return claim_ids


def _evaluated_claims(output_root: Path) -> list[str]:
    claim_ids = _accepted_claims(output_root)
    for index, claim_id in enumerate(claim_ids, start=1):
        staged = stage_claim_evaluation(
            {"claim_id": claim_id, "staged_by": f"Appraisal Coordinator {index}"},
            output_root=output_root,
        )
        candidate = next(item for item in staged["candidates"] if item["claim_id"] == claim_id)
        finalize_claim_evaluation(
            _finalize_payload(str(candidate["candidate_id"])), output_root=output_root
        )
    return claim_ids


def _stage_payload(claim_ids: list[str], *, name: str = "Food literacy outcomes") -> dict:
    return {
        "name": name,
        "lens": "food_literacy",
        "focus_statement": (
            "Organize evaluated source-level claims reporting food-literacy outcomes after structured programs."
        ),
        "scope": {
            "domain": "food_literacy",
            "population": "Adults enrolled in the included study contexts",
            "intervention_or_exposure": "",
            "comparator": "",
            "outcome": "Food-literacy score",
            "timeframe": "",
            "context": "Program evaluation contexts",
        },
        "claim_ids": claim_ids,
        "staged_by": "EvidenceSet Coordinator",
    }


def _finalize_payload_for_set(draft: dict) -> dict:
    claim_ids = [str(value) for value in draft["claim_ids"]]
    return {
        "draft_id": draft["draft_id"],
        "curator": "EvidenceSet Curator",
        "rationale": (
            "These claims are grouped because they address the declared food-literacy outcome lens while "
            "remaining separate source-level propositions."
        ),
        "membership_rationales": {
            claim_id: (
                "This claim directly addresses the declared outcome lens and has a finalized claim-level appraisal."
            )
            for claim_id in claim_ids
        },
        "membership_human_curated_confirmed": True,
        "grouping_is_not_consensus_confirmed": True,
        "scientific_boundary_confirmed": True,
    }


def test_stage_requires_finalized_claim_evaluation(tmp_path: Path) -> None:
    claim_ids = _accepted_claims(tmp_path)

    with pytest.raises(SynthesisGovernanceError, match="não possui ClaimEvaluation finalizada"):
        stage_evidence_set(_stage_payload([claim_ids[0]]), output_root=tmp_path)


def test_staging_is_order_and_operator_idempotent_and_never_finalizes(tmp_path: Path) -> None:
    claim_ids = _evaluated_claims(tmp_path)
    first = stage_evidence_set(_stage_payload(claim_ids), output_root=tmp_path)
    second_payload = _stage_payload(list(reversed(claim_ids)))
    second_payload["staged_by"] = "Another Coordinator"
    second = stage_evidence_set(second_payload, output_root=tmp_path)

    assert first["draft_count"] == 1
    assert second["draft_count"] == 1
    assert first["drafts"][0]["draft_id"] == second["drafts"][0]["draft_id"]
    assert second["draft_counts"][DRAFT] == 1
    assert second["finalized_evidence_set_count"] == 0


def test_finalize_creates_canonical_membership_record_without_consensus_or_certainty(tmp_path: Path) -> None:
    claim_ids = _evaluated_claims(tmp_path)
    staged = stage_evidence_set(_stage_payload(claim_ids), output_root=tmp_path)
    draft = staged["drafts"][0]

    finalized = finalize_evidence_set(_finalize_payload_for_set(draft), output_root=tmp_path)

    assert finalized["draft_counts"][FINALIZED] == 1
    assert finalized["finalized_evidence_set_count"] == 1
    item = finalized["finalized_evidence_sets"][0]
    evidence_set_id = item["evidence_set_id"]
    record_path = _set_root(tmp_path) / "finalized" / f"{evidence_set_id}.json"
    import json

    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["evidence_set_record_type"] == CANONICAL_EVIDENCE_SET_RECORD_TYPE
    assert record["canonical"] is True
    assert record["human_finalized"] is True
    assert record["evidence_set"]["id"] == evidence_set_id
    assert set(record["evidence_set"]["claim_ids"]) == set(claim_ids)
    assert record["evidence_set"]["lens"] == "food_literacy"
    assert record["evidence_set"]["metadata"]["human_entered"] is True
    assert len(record["evidence_set"]["metadata"]["memberships"]) == 2
    assert record["guardrails"]["evidence_set_created"] is True
    assert record["guardrails"]["membership_human_curated"] is True
    assert record["guardrails"]["automatic_claim_grouping_performed"] is False
    assert record["guardrails"]["automatic_relation_inference_performed"] is False
    assert record["guardrails"]["claim_evaluation_scores_aggregated"] is False
    assert record["guardrails"]["consensus_inferred"] is False
    assert record["guardrails"]["contradiction_inferred"] is False
    assert record["guardrails"]["certainty_assessed"] is False
    assert record["guardrails"]["overall_certainty_grade_created"] is False
    assert record["guardrails"]["formal_risk_of_bias_assessed"] is False
    assert record["guardrails"]["canonical_scientific_synthesis_created"] is False
    assert record["guardrails"]["clinical_recommendation_created"] is False
    assert record["guardrails"]["meta_analysis_performed"] is False
    assert record["guardrails"]["prisma_event_emitted"] is False


def test_finalize_requires_membership_rationale_and_all_confirmations(tmp_path: Path) -> None:
    claim_ids = _evaluated_claims(tmp_path)
    staged = stage_evidence_set(_stage_payload(claim_ids), output_root=tmp_path)
    draft = staged["drafts"][0]

    payload = _finalize_payload_for_set(draft)
    payload["membership_rationales"].pop(claim_ids[0])
    with pytest.raises(SynthesisGovernanceError, match="Membership rationales inválidas"):
        finalize_evidence_set(payload, output_root=tmp_path)

    for key, expected in (
        ("membership_human_curated_confirmed", "membership"),
        ("grouping_is_not_consensus_confirmed", "consensus"),
        ("scientific_boundary_confirmed", "certainty"),
    ):
        payload = _finalize_payload_for_set(draft)
        payload[key] = False
        with pytest.raises(SynthesisGovernanceError, match=expected):
            finalize_evidence_set(payload, output_root=tmp_path)


def test_single_claim_set_is_allowed_but_explicitly_not_synthesis(tmp_path: Path) -> None:
    claim_ids = _evaluated_claims(tmp_path)
    staged = stage_evidence_set(_stage_payload([claim_ids[0]], name="Single claim lens"), output_root=tmp_path)
    draft = staged["drafts"][0]
    finalized = finalize_evidence_set(_finalize_payload_for_set(draft), output_root=tmp_path)
    evidence_set_id = finalized["finalized_evidence_sets"][0]["evidence_set_id"]

    import json

    record = json.loads(
        (_set_root(tmp_path) / "finalized" / f"{evidence_set_id}.json").read_text(encoding="utf-8")
    )
    assert record["evidence_set"]["claim_ids"] == [claim_ids[0]]
    assert record["guardrails"]["single_claim_set_is_not_synthesis"] is True


def test_same_claim_can_belong_to_multiple_human_curated_sets(tmp_path: Path) -> None:
    claim_ids = _evaluated_claims(tmp_path)
    claim_id = claim_ids[0]

    first = stage_evidence_set(_stage_payload([claim_id], name="Outcome lens"), output_root=tmp_path)
    finalize_evidence_set(_finalize_payload_for_set(first["drafts"][0]), output_root=tmp_path)

    second_payload = _stage_payload([claim_id], name="Implementation lens")
    second_payload["lens"] = "implementation_context"
    second_payload["focus_statement"] = (
        "Organize the same evaluated claim under a separate implementation-context lens for human review."
    )
    second = stage_evidence_set(second_payload, output_root=tmp_path)
    draft = next(item for item in second["drafts"] if item["status"] == DRAFT)
    final = finalize_evidence_set(_finalize_payload_for_set(draft), output_root=tmp_path)

    assert final["finalized_evidence_set_count"] == 2
    assert len(final["claim_membership_index"][claim_id]) == 2


def test_finalize_fails_closed_when_context_changes_after_staging(tmp_path: Path) -> None:
    claim_ids = _evaluated_claims(tmp_path)
    staged = stage_evidence_set(_stage_payload(claim_ids), output_root=tmp_path)
    draft = staged["drafts"][0]
    _write_search_state(tmp_path, database_sha="f" * 64)

    with pytest.raises(SynthesisGovernanceError, match="contexto|Context fingerprint|restage"):
        finalize_evidence_set(_finalize_payload_for_set(draft), output_root=tmp_path)

    current = evidence_set_status(output_root=tmp_path)
    assert current["draft_counts"][DRAFT] == 1
    assert current["finalized_evidence_set_count"] == 0


def test_evidence_set_finalization_does_not_mutate_claim_or_evaluation_artifacts(tmp_path: Path) -> None:
    claim_ids = _evaluated_claims(tmp_path)
    claim_id = claim_ids[0]
    evaluations = claim_evaluation_status(output_root=tmp_path)
    evaluation = next(item for item in evaluations["finalized_evaluations"] if item["claim_id"] == claim_id)
    claim_path = _claim_path(_claim_root(tmp_path), claim_id)
    evaluation_path = _evaluation_root(tmp_path) / "finalized" / f"{evaluation['evaluation_id']}.json"
    claim_before = claim_path.read_bytes()
    evaluation_before = evaluation_path.read_bytes()

    staged = stage_evidence_set(_stage_payload([claim_id]), output_root=tmp_path)
    finalize_evidence_set(_finalize_payload_for_set(staged["drafts"][0]), output_root=tmp_path)

    assert claim_path.read_bytes() == claim_before
    assert evaluation_path.read_bytes() == evaluation_before
