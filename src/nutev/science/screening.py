"""Translate final scientific screening decisions into explicit lifecycle events."""

from __future__ import annotations

from .models import (
    DocumentState,
    ScientificEvent,
    ScreeningDecision,
    ScreeningDecisionValue,
    ScreeningStage,
)


def events_from_screening_decision(decision: ScreeningDecision) -> tuple[ScientificEvent, ...]:
    """Return PRISMA-relevant events for one final resolved screening decision.

    Individual reviewer votes must not be passed here. This function represents
    the final resolved decision for one document/stage so PRISMA counts are not
    multiplied by the number of reviewers.
    """

    if decision.decision is ScreeningDecisionValue.EXCLUDE and not str(
        decision.reason or ""
    ).strip():
        raise ValueError("final exclusion decision requires an explicit reason")

    common_metadata = {
        "screening_decision_id": decision.id,
        "stage": decision.stage.value,
        "decision": decision.decision.value,
        "adjudicator": decision.adjudicator,
        **dict(decision.metadata),
    }

    if decision.stage is ScreeningStage.TITLE_ABSTRACT:
        events: list[ScientificEvent] = [
            ScientificEvent(
                id=f"{decision.id}:screened",
                entity_type="document",
                entity_id=decision.document_id,
                action="screened",
                to_state=DocumentState.SCREENED.value,
                occurred_at=decision.decided_at,
                metadata=common_metadata,
            )
        ]
        if decision.decision is ScreeningDecisionValue.EXCLUDE:
            events.append(
                ScientificEvent(
                    id=f"{decision.id}:excluded_screening",
                    entity_type="document",
                    entity_id=decision.document_id,
                    action="excluded_screening",
                    to_state=DocumentState.EXCLUDED.value,
                    reason=decision.reason,
                    occurred_at=decision.decided_at,
                    metadata=common_metadata,
                )
            )
        return tuple(events)

    if decision.stage is ScreeningStage.FULL_TEXT:
        events = [
            ScientificEvent(
                id=f"{decision.id}:assessed_for_eligibility",
                entity_type="document",
                entity_id=decision.document_id,
                action="assessed_for_eligibility",
                occurred_at=decision.decided_at,
                metadata=common_metadata,
            )
        ]
        if decision.decision is ScreeningDecisionValue.EXCLUDE:
            events.append(
                ScientificEvent(
                    id=f"{decision.id}:excluded_full_text",
                    entity_type="document",
                    entity_id=decision.document_id,
                    action="excluded_full_text",
                    to_state=DocumentState.EXCLUDED.value,
                    reason=decision.reason,
                    occurred_at=decision.decided_at,
                    metadata=common_metadata,
                )
            )
        elif decision.decision is ScreeningDecisionValue.INCLUDE:
            events.append(
                ScientificEvent(
                    id=f"{decision.id}:included",
                    entity_type="document",
                    entity_id=decision.document_id,
                    action="included",
                    to_state=DocumentState.INCLUDED.value,
                    occurred_at=decision.decided_at,
                    metadata=common_metadata,
                )
            )
        return tuple(events)

    raise ValueError(f"unsupported screening stage: {decision.stage!r}")
