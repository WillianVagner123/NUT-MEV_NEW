from __future__ import annotations

import json
from pathlib import Path

import pytest

from nutev.control_plane import (
    ControlPlaneViolation,
    assert_ai_did_not_mutate_control_state,
    formal_execution_firewall,
    formal_prisma_firewall,
    gf02_candidate_firewall,
    require_allowed,
    validate_human_gate_record,
)


def test_gf02_candidate_firewall_accepts_only_prepress_pilot_contract() -> None:
    result = gf02_candidate_firewall(
        {
            "search_type": "PILOT",
            "prisma_eligible": False,
            "formal_execution_authorized": False,
            "current_candidate": "v0.5",
        }
    )
    assert result == {
        "allowed": True,
        "rule": "GF02_PREPRESS_CANDIDATE",
        "blockers": [],
        "decision_source": "DETERMINISTIC_CODE",
    }


def test_gf02_candidate_firewall_fails_closed_on_missing_or_wrong_values() -> None:
    result = gf02_candidate_firewall(
        {
            "search_type": "FORMAL",
            "prisma_eligible": True,
            "formal_execution_authorized": True,
            "current_candidate": "",
        }
    )
    assert result["allowed"] is False
    assert result["blockers"] == [
        "search_type_must_be_PILOT",
        "prisma_eligible_must_be_false",
        "formal_execution_authorized_must_be_false",
        "current_candidate_missing",
    ]
    with pytest.raises(ControlPlaneViolation, match="GF02_PREPRESS_CANDIDATE blocked"):
        require_allowed(result)


def test_formal_execution_requires_all_deterministic_prerequisites() -> None:
    allowed = formal_execution_firewall(
        {
            "search_type": "FORMAL",
            "freeze_authorized": True,
            "formal_execution_authorized": True,
            "required_scientific_gates_closed": True,
        }
    )
    assert allowed["allowed"] is True
    require_allowed(allowed)

    blocked = formal_execution_firewall(
        {
            "search_type": "PILOT",
            "freeze_authorized": False,
            "formal_execution_authorized": False,
            "required_scientific_gates_closed": False,
        }
    )
    assert blocked["allowed"] is False
    assert blocked["blockers"] == [
        "search_type!=FORMAL",
        "freeze_authorized!=true",
        "formal_execution_authorized!=true",
        "required_scientific_gates_closed!=true",
    ]


def test_formal_prisma_requires_completed_formal_human_chain() -> None:
    fields = {
        "formal_execution_completed": True,
        "screening_completed": True,
        "fulltext_completed": True,
        "adjudication_completed": True,
        "prisma_eligible": True,
    }
    assert formal_prisma_firewall(fields)["allowed"] is True

    for key in fields:
        state = dict(fields)
        state[key] = False
        result = formal_prisma_firewall(state)
        assert result["allowed"] is False
        assert result["blockers"] == [f"{key}!=true"]


def test_human_gate_record_requires_real_structured_human_evidence() -> None:
    valid = validate_human_gate_record(
        {
            "decision": "READY_FOR_PRESS",
            "decision_source": "HUMAN",
            "reviewer": "Willian Vagner",
            "decided_at": "2026-08-15T21:00:00-03:00",
            "evidence_hash": "abc123",
        },
        allowed_decisions={"READY_FOR_PRESS", "NOT_READY_FOR_PRESS"},
    )
    assert valid["allowed"] is True

    invalid = validate_human_gate_record(
        {
            "decision": "READY_FOR_PRESS",
            "decision_source": "AI_ASSISTANT",
            "reviewer": "",
            "decided_at": "",
            "evidence_hash": "",
        },
        allowed_decisions={"READY_FOR_PRESS", "NOT_READY_FOR_PRESS"},
    )
    assert invalid["allowed"] is False
    assert invalid["blockers"] == [
        "decision_source!=HUMAN",
        "reviewer_missing",
        "decided_at_missing",
        "evidence_hash_missing",
    ]


def test_ai_actor_cannot_mutate_canonical_control_fields() -> None:
    before = {
        "stage": "GF02_HUMAN_DECISION",
        "human_decision": None,
        "formal_execution_authorized": False,
    }
    after = {
        **before,
        "human_decision": "READY_FOR_PRESS",
        "formal_execution_authorized": True,
    }
    with pytest.raises(ControlPlaneViolation, match="AI actors cannot mutate"):
        assert_ai_did_not_mutate_control_state(before, after, actor_type="AI_ASSISTANT")


def test_ai_actor_may_change_noncanonical_prose_only() -> None:
    before = {
        "stage": "GF02_HUMAN_DECISION",
        "human_decision": None,
        "presentation_text": "old",
    }
    after = {**before, "presentation_text": "improved prose"}
    assert_ai_did_not_mutate_control_state(before, after, actor_type="LLM")


def test_non_ai_actor_is_not_blocked_by_ai_specific_firewall() -> None:
    before = {"human_decision": None}
    after = {"human_decision": "READY_FOR_PRESS"}
    assert_ai_did_not_mutate_control_state(before, after, actor_type="HUMAN")


def test_control_plane_schema_is_closed_and_contains_core_contract() -> None:
    path = Path("config/schemas/article1_control_plane.schema.json")
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert "stage" in schema["required"]
    assert "formal_execution_authorized" in schema["required"]
    assert schema["properties"]["search_type"]["enum"] == ["PILOT", "FORMAL"]
    assert schema["properties"]["prisma_eligible"]["type"] == "boolean"
