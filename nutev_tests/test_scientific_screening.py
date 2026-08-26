from __future__ import annotations

import pytest

from nutev.science import (
    ScreeningDecision,
    ScreeningDecisionValue,
    ScreeningStage,
    derive_prisma_counts,
    events_from_screening_decision,
)


DECIDED_AT = "2026-08-26T20:00:00+00:00"


def test_title_abstract_include_records_screening_without_inclusion():
    decision = ScreeningDecision(
        id="screen-1",
        document_id="doi:10.1000/a",
        stage=ScreeningStage.TITLE_ABSTRACT,
        decision=ScreeningDecisionValue.INCLUDE,
        adjudicator="reviewer-final",
        decided_at=DECIDED_AT,
    )

    events = events_from_screening_decision(decision)
    prisma = derive_prisma_counts(events)

    assert [event.action for event in events] == ["screened"]
    assert prisma.screened == 1
    assert prisma.included == 0
    assert prisma.assessed_for_eligibility == 0


def test_title_abstract_exclusion_requires_and_preserves_reason():
    decision = ScreeningDecision(
        id="screen-2",
        document_id="doi:10.1000/b",
        stage=ScreeningStage.TITLE_ABSTRACT,
        decision=ScreeningDecisionValue.EXCLUDE,
        reason="wrong population",
        decided_at=DECIDED_AT,
    )

    events = events_from_screening_decision(decision)
    prisma = derive_prisma_counts(events)

    assert [event.action for event in events] == ["screened", "excluded_screening"]
    assert events[1].reason == "wrong population"
    assert prisma.screened == 1
    assert prisma.excluded_screening == 1


def test_exclusion_without_reason_fails_closed():
    decision = ScreeningDecision(
        id="screen-3",
        document_id="doi:10.1000/c",
        stage=ScreeningStage.FULL_TEXT,
        decision=ScreeningDecisionValue.EXCLUDE,
        decided_at=DECIDED_AT,
    )

    with pytest.raises(ValueError, match="requires an explicit reason"):
        events_from_screening_decision(decision)


def test_full_text_include_generates_eligibility_and_inclusion_events():
    decision = ScreeningDecision(
        id="screen-4",
        document_id="doi:10.1000/d",
        stage=ScreeningStage.FULL_TEXT,
        decision=ScreeningDecisionValue.INCLUDE,
        adjudicator="adjudicator-1",
        decided_at=DECIDED_AT,
    )

    events = events_from_screening_decision(decision)
    prisma = derive_prisma_counts(events)

    assert [event.action for event in events] == ["assessed_for_eligibility", "included"]
    assert prisma.assessed_for_eligibility == 1
    assert prisma.included == 1


def test_full_text_uncertain_does_not_infer_inclusion_or_exclusion():
    decision = ScreeningDecision(
        id="screen-5",
        document_id="doi:10.1000/e",
        stage=ScreeningStage.FULL_TEXT,
        decision=ScreeningDecisionValue.UNCERTAIN,
        decided_at=DECIDED_AT,
    )

    events = events_from_screening_decision(decision)
    prisma = derive_prisma_counts(events)

    assert [event.action for event in events] == ["assessed_for_eligibility"]
    assert prisma.assessed_for_eligibility == 1
    assert prisma.included == 0
    assert prisma.excluded_full_text == 0
