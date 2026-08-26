from nutev.science import (
    EvidenceClaim,
    EvidenceConstraint,
    EvidenceSet,
    ScientificEvent,
    SearchCase,
    derive_prisma_counts,
)


def test_search_case_preserves_constraints_as_scientific_entities():
    population = EvidenceConstraint.from_values(
        id="c-pop",
        name="population",
        values=["overweight", "obesity"],
        role="population",
    )
    case = SearchCase(
        id="search-1",
        question_id="rq-1",
        query="overweight obesity protein lean mass",
        provider="pubmed",
        constraints=(population,),
    )

    assert case.provider == "pubmed"
    assert case.constraints[0].values == ("overweight", "obesity")


def test_evidence_set_groups_claim_ids_without_copying_claims():
    claim = EvidenceClaim(
        id="claim-1",
        evidence_record_id="record-1",
        statement="Higher protein intake was associated with greater FFM retention.",
        outcome="fat-free mass",
        evidence_type="randomized_trial",
    )
    evidence_set = EvidenceSet.from_claims(
        id="set-1",
        name="protein_ffm",
        claim_ids=[claim.id],
        lens="dietary_intervention",
    )

    assert evidence_set.claim_ids == ("claim-1",)
    assert evidence_set.lens == "dietary_intervention"


def test_prisma_counts_are_derived_only_from_explicit_events():
    events = [
        ScientificEvent(id="e1", entity_type="document", entity_id="d1", action="identified"),
        ScientificEvent(id="e2", entity_type="document", entity_id="d2", action="identified"),
        ScientificEvent(id="e3", entity_type="document", entity_id="d2", action="duplicate_removed"),
        ScientificEvent(id="e4", entity_type="document", entity_id="d1", action="screened"),
        ScientificEvent(id="e5", entity_type="document", entity_id="d1", action="included"),
        ScientificEvent(id="e6", entity_type="claim", entity_id="c1", action="evaluated"),
    ]

    prisma = derive_prisma_counts(events)

    assert prisma.identified == 2
    assert prisma.duplicates_removed == 1
    assert prisma.screened == 1
    assert prisma.included == 1
    assert prisma.assessed_for_eligibility == 0
