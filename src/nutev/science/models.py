"""Scientific object model for NutEV.

This module is intentionally additive. It does not change the Reference Engine
contract or upgrade ranking into scientific eligibility/quality. It provides
small, composable, traceable entities for downstream scientific workflows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Mapping, Sequence


class DocumentState(StrEnum):
    DISCOVERED = "discovered"
    RESOLVED = "resolved"
    RETRIEVED = "retrieved"
    SCREENED = "screened"
    INCLUDED = "included"
    EXCLUDED = "excluded"
    EXTRACTED = "extracted"


class ValidationDecision(StrEnum):
    PENDING = "pending"
    ACCEPT = "accept"
    REJECT = "reject"
    REVISE = "revise"


class ScreeningStage(StrEnum):
    TITLE_ABSTRACT = "title_abstract"
    FULL_TEXT = "full_text"


class ScreeningDecisionValue(StrEnum):
    INCLUDE = "include"
    EXCLUDE = "exclude"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True, slots=True)
class ResearchQuestion:
    id: str
    text: str
    framework: str | None = None
    fields: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvidenceConstraint:
    id: str
    name: str
    values: tuple[str, ...]
    role: str | None = None

    @classmethod
    def from_values(
        cls,
        id: str,
        name: str,
        values: Sequence[str],
        role: str | None = None,
    ) -> "EvidenceConstraint":
        return cls(id=id, name=name, values=tuple(values), role=role)


@dataclass(frozen=True, slots=True)
class SearchCase:
    id: str
    question_id: str
    query: str
    provider: str
    constraints: tuple[EvidenceConstraint, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DocumentCandidate:
    id: str
    source_provider: str
    title: str
    doi: str | None = None
    pmid: str | None = None
    url: str | None = None
    year: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    id: str
    document_id: str
    source_provider: str
    source_run_id: str | None = None
    origin_sha256: str | None = None
    taxonomy: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ScreeningDecision:
    """Final resolved scientific screening decision for one document and stage."""

    id: str
    document_id: str
    stage: ScreeningStage
    decision: ScreeningDecisionValue
    adjudicator: str | None = None
    reason: str | None = None
    decided_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvidenceClaim:
    id: str
    evidence_record_id: str
    statement: str
    locator: str | None = None
    quote: str | None = None
    population: str | None = None
    intervention_or_exposure: str | None = None
    comparator: str | None = None
    outcome: str | None = None
    evidence_type: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ClaimEvaluation:
    id: str
    claim_id: str
    dimensions: Mapping[str, Any]
    assessor: str | None = None
    rationale: str | None = None


@dataclass(frozen=True, slots=True)
class EvidenceSet:
    id: str
    name: str
    claim_ids: tuple[str, ...]
    lens: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_claims(
        cls,
        id: str,
        name: str,
        claim_ids: Sequence[str],
        *,
        lens: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "EvidenceSet":
        return cls(
            id=id,
            name=name,
            claim_ids=tuple(claim_ids),
            lens=lens,
            metadata=metadata or {},
        )


@dataclass(frozen=True, slots=True)
class RecommendationCandidate:
    id: str
    statement: str
    evidence_set_ids: tuple[str, ...]
    readiness: str = "not_evaluated"
    rationale: str | None = None


@dataclass(frozen=True, slots=True)
class HumanValidation:
    id: str
    target_type: str
    target_id: str
    decision: ValidationDecision = ValidationDecision.PENDING
    reviewer: str | None = None
    rationale: str | None = None
    reviewed_at: str | None = None


@dataclass(frozen=True, slots=True)
class ScientificEvent:
    id: str
    entity_type: str
    entity_id: str
    action: str
    from_state: str | None = None
    to_state: str | None = None
    reason: str | None = None
    occurred_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PrismaCounts:
    identified: int = 0
    duplicates_removed: int = 0
    screened: int = 0
    excluded_screening: int = 0
    sought_for_retrieval: int = 0
    not_retrieved: int = 0
    assessed_for_eligibility: int = 0
    excluded_full_text: int = 0
    included: int = 0


def derive_prisma_counts(events: Sequence[ScientificEvent]) -> PrismaCounts:
    """Derive PRISMA-like counts from explicit document transition events.

    Only events that explicitly state a relevant action/transition are counted.
    The function never infers missing screening or inclusion decisions.
    """

    counts = {
        "identified": 0,
        "duplicates_removed": 0,
        "screened": 0,
        "excluded_screening": 0,
        "sought_for_retrieval": 0,
        "not_retrieved": 0,
        "assessed_for_eligibility": 0,
        "excluded_full_text": 0,
        "included": 0,
    }

    action_map = {
        "identified": "identified",
        "duplicate_removed": "duplicates_removed",
        "screened": "screened",
        "excluded_screening": "excluded_screening",
        "sought_for_retrieval": "sought_for_retrieval",
        "not_retrieved": "not_retrieved",
        "assessed_for_eligibility": "assessed_for_eligibility",
        "excluded_full_text": "excluded_full_text",
        "included": "included",
    }

    for event in events:
        key = action_map.get(event.action)
        if key is not None:
            counts[key] += 1

    return PrismaCounts(**counts)
