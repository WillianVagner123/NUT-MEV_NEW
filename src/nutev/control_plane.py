"""Deterministic control-plane contracts and scientific firewalls.

Generative AI is intentionally excluded from this module. Scientific state,
workflow authorization and formal-output eligibility must be decided only from
structured values passed to these pure deterministic guards.
"""
from __future__ import annotations

from typing import Any, Mapping


class ControlPlaneViolation(ValueError):
    """Raised when a canonical scientific-control invariant is violated."""


AI_ACTOR_TYPES = frozenset({"AI", "AI_ASSISTANT", "LLM", "GENERATIVE_AI"})
CONTROL_FIELDS = frozenset(
    {
        "stage",
        "search_type",
        "prisma_eligible",
        "formal_execution_authorized",
        "freeze_authorized",
        "human_validated",
        "human_decision",
        "press_authorized",
        "required_scientific_gates_closed",
        "formal_execution_completed",
        "screening_completed",
        "fulltext_completed",
        "adjudication_completed",
        "blockers",
    }
)


def _bool_is(value: object, expected: bool) -> bool:
    return isinstance(value, bool) and value is expected


def _guard(rule: str, blockers: list[str]) -> dict[str, Any]:
    return {
        "allowed": not blockers,
        "rule": rule,
        "blockers": blockers,
        "decision_source": "DETERMINISTIC_CODE",
    }


def gf02_candidate_firewall(config: Mapping[str, Any]) -> dict[str, Any]:
    """Fail-closed guard for the current pre-PRESS GF-02 candidate config."""
    blockers: list[str] = []
    if str(config.get("search_type") or "").upper() != "PILOT":
        blockers.append("search_type_must_be_PILOT")
    if not _bool_is(config.get("prisma_eligible"), False):
        blockers.append("prisma_eligible_must_be_false")
    if not _bool_is(config.get("formal_execution_authorized"), False):
        blockers.append("formal_execution_authorized_must_be_false")
    if not str(config.get("current_candidate") or "").strip():
        blockers.append("current_candidate_missing")
    return _guard("GF02_PREPRESS_CANDIDATE", blockers)


def formal_execution_firewall(state: Mapping[str, Any]) -> dict[str, Any]:
    """Authorize FORMAL execution only when every deterministic prerequisite is true."""
    blockers: list[str] = []
    if str(state.get("search_type") or "").upper() != "FORMAL":
        blockers.append("search_type!=FORMAL")
    if not _bool_is(state.get("freeze_authorized"), True):
        blockers.append("freeze_authorized!=true")
    if not _bool_is(state.get("formal_execution_authorized"), True):
        blockers.append("formal_execution_authorized!=true")
    if not _bool_is(state.get("required_scientific_gates_closed"), True):
        blockers.append("required_scientific_gates_closed!=true")
    return _guard("FORMAL_EXECUTION_FIREWALL", blockers)


def formal_prisma_firewall(state: Mapping[str, Any]) -> dict[str, Any]:
    """Authorize publication-grade PRISMA counts only from completed formal state."""
    blockers: list[str] = []
    required_true = (
        "formal_execution_completed",
        "screening_completed",
        "fulltext_completed",
        "adjudication_completed",
        "prisma_eligible",
    )
    for field in required_true:
        if not _bool_is(state.get(field), True):
            blockers.append(f"{field}!=true")
    return _guard("FORMAL_PRISMA_FIREWALL", blockers)


def require_allowed(result: Mapping[str, Any]) -> None:
    """Raise on a blocked deterministic guard result."""
    if result.get("allowed") is True:
        return
    rule = str(result.get("rule") or "CONTROL_PLANE_GUARD")
    blockers = [str(item) for item in (result.get("blockers") or [])]
    detail = ", ".join(blockers) if blockers else "unspecified blocker"
    raise ControlPlaneViolation(f"{rule} blocked: {detail}")


def validate_human_gate_record(
    record: Mapping[str, Any],
    *,
    allowed_decisions: set[str] | frozenset[str],
) -> dict[str, Any]:
    """Validate an explicit human gate record without interpreting its rationale."""
    blockers: list[str] = []
    decision = str(record.get("decision") or "").strip().upper()
    source = str(record.get("decision_source") or "").strip().upper()
    reviewer = str(record.get("reviewer") or "").strip()
    decided_at = str(record.get("decided_at") or "").strip()
    evidence_hash = str(record.get("evidence_hash") or "").strip()

    if source != "HUMAN":
        blockers.append("decision_source!=HUMAN")
    if decision not in {str(item).upper() for item in allowed_decisions}:
        blockers.append("decision_not_in_allowed_enum")
    if not reviewer:
        blockers.append("reviewer_missing")
    if not decided_at:
        blockers.append("decided_at_missing")
    if not evidence_hash:
        blockers.append("evidence_hash_missing")
    return _guard("HUMAN_GATE_RECORD", blockers)


def assert_ai_did_not_mutate_control_state(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    actor_type: str,
) -> None:
    """Reject any AI-authored mutation of canonical control-plane fields."""
    actor = str(actor_type or "").strip().upper()
    if actor not in AI_ACTOR_TYPES:
        return
    changed = sorted(field for field in CONTROL_FIELDS if before.get(field) != after.get(field))
    if changed:
        raise ControlPlaneViolation(
            "AI actors cannot mutate canonical scientific control fields: " + ", ".join(changed)
        )


__all__ = [
    "AI_ACTOR_TYPES",
    "CONTROL_FIELDS",
    "ControlPlaneViolation",
    "assert_ai_did_not_mutate_control_state",
    "formal_execution_firewall",
    "formal_prisma_firewall",
    "gf02_candidate_firewall",
    "require_allowed",
    "validate_human_gate_record",
]
