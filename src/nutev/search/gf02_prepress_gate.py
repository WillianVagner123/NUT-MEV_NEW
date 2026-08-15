"""Canonical GF-02 pre-PRESS gate under methodology decision D-096.

GF-02 pre-PRESS is decided from the current PubMed PILOT, sentinel evidence,
classified noise sample, and an explicit human READY_FOR_PRESS/NOT_READY_FOR_PRESS
decision. Final Scopus/Web of Science translation and licensed PILOT validation
are post-PRESS work and therefore are not blockers to entering PRESS.
"""
from __future__ import annotations

from typing import Any

from nutev.search.gf02_evidence import GATE_DECISIONS, PRIORITY_SENTINELS, validate_gf02_pilot_strategy


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def evaluate_gf02_prepress_gate(
    *,
    strategy_version: dict[str, Any],
    pubmed_recall: dict[str, Any],
    noise_summary: dict[str, Any],
    priority_sentinels: tuple[str, ...] = PRIORITY_SENTINELS,
    missing_explanations: dict[str, str] | None = None,
    human_decision: str | None = None,
    human_decision_by: str = "",
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        validate_gf02_pilot_strategy(strategy_version)
    except ValueError as exc:
        blockers.append(str(exc))

    explanations = {
        str(key).strip(): _clean(value)
        for key, value in (missing_explanations or {}).items()
        if str(key).strip()
    }
    unresolved = set(pubmed_recall.get("unresolved_sentinel_ids") or [])
    recovered = set(pubmed_recall.get("recovered_sentinel_ids") or [])
    missing = set(pubmed_recall.get("missing_resolved_sentinel_ids") or [])
    for sentinel_id in priority_sentinels:
        if sentinel_id in unresolved:
            blockers.append(f"{sentinel_id}:identity_unresolved")
        elif sentinel_id in recovered:
            continue
        elif sentinel_id in missing:
            if not explanations.get(sentinel_id):
                blockers.append(f"{sentinel_id}:missing_without_explanation")
        else:
            blockers.append(f"{sentinel_id}:pubmed_assessment_missing")

    if int(noise_summary.get("sample_size") or 0) <= 0:
        blockers.append("noise_sample_missing")

    normalized_decision = (human_decision or "").strip().upper()
    if normalized_decision and normalized_decision not in GATE_DECISIONS:
        raise ValueError(f"human_decision must be one of {GATE_DECISIONS}")
    if normalized_decision and not human_decision_by.strip():
        raise ValueError("human_decision_by is required when a human_decision is recorded")

    evidence_complete = not blockers
    if not evidence_complete:
        decision = "NOT_READY_FOR_PRESS"
    elif not normalized_decision:
        decision = "EVIDENCE_COMPLETE_AWAITING_HUMAN_DECISION"
    else:
        decision = normalized_decision

    return {
        "schema_version": 2,
        "gate": "GF-02",
        "stage": "PRE_PRESS",
        "methodology_decision": "D-096",
        "evidence_complete": evidence_complete,
        "decision": decision,
        "human_decision": normalized_decision or None,
        "human_decision_by": human_decision_by.strip() or None,
        "blockers": blockers,
        "priority_sentinels": list(priority_sentinels),
        "missing_explanations": explanations,
        "scopus_wos_pre_press_blocker": False,
        "post_press_required": ["SCOPUS_TRANSLATION_AND_LICENSED_PILOT", "WOS_TRANSLATION_AND_LICENSED_PILOT"],
        "press_approval_inferred": False,
        "formal_execution_authorized": False,
        "prisma_eligible": False,
    }


__all__ = ["evaluate_gf02_prepress_gate"]
