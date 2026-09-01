# EvidenceClaim Review & Promotion

## Scope

Fase 16 introduces the first NutEV surface that may create a **canonical source-level `EvidenceClaim`**.

This permission is intentionally narrow. It does not turn the prior synthesis/governance/publication chain into scientific truth. The claim layer accepts only a proposition explicitly reviewed by a human and linked to one materialized `EvidenceRecord`.

The implemented chain is:

```text
Scientific Intelligence
  -> Human Synthesis Review
  -> Human Synthesis Brief
  -> Synthesis Governance Registry
  -> Governed Synthesis Release
  -> Governed Publication Manifest
  -> atomic citation snapshot
  -> EvidenceClaim Candidate
  -> explicit human ACCEPT / REJECT / REVISE
  -> canonical source-level EvidenceClaim (ACCEPT only)
```

## Atomicity rule

The scientific object model defines `EvidenceClaim` as the smallest evidence unit and requires an `evidence_record_id`.

A pairwise synthesis statement such as:

```text
this source-linked pair was classified by the reviewer as CONVERGENT
```

belongs to **two documents** and therefore is not an atomic EvidenceClaim.

Fase 16 never promotes that statement directly. The pairwise relation remains synthesis context only.

Instead, each citation from the Publication Manifest becomes one candidate:

```text
one citation snapshot
  -> one canonical document identity
  -> one expected EvidenceRecord id
  -> one EvidenceClaim candidate
```

The candidate explicitly carries:

```text
directly_promotable_to_evidence_claim: false   # for pairwise synthesis context
pairwise_statement_directly_promotable: false
```

## Source gate

A claim candidate is built from a source-linked citation snapshot containing, when available:

- citation id;
- decision id;
- anchor/candidate role;
- document id;
- title;
- bibliographic identifiers already present;
- result-bundle id;
- `source_sentence_sha256`;
- result text;
- outcomes;
- effect measures;
- confidence intervals;
- p-values;
- routes;
- source reference.

Missing metadata is not invented.

The source snapshot is not a claim by itself.

## EvidenceRecord referential-integrity gate

`ACCEPT` is impossible unless the corresponding EvidenceRecord exists in:

```text
project_output_reference/scientific/evidence_records.jsonl
```

The expected id follows the existing scientific adapter contract:

```text
document_id = canonical identity
EvidenceRecord.id = evidence:{document_id}
```

Examples:

```text
doi:10.1000/example
  -> evidence:doi:10.1000/example

pmid:123456
  -> evidence:pmid:123456
```

The service verifies both the EvidenceRecord id and its `document_id` before canonical claim creation.

A derived id alone is insufficient.

### Transactional failure

For `ACCEPT`, this referential-integrity gate runs before the human validation record is persisted through the local coordinator.

Therefore a blocked acceptance because of a missing EvidenceRecord does not leave:

- a canonical claim;
- an accepted state;
- an `ACCEPT` review artifact that could be mistaken for a completed promotion.

## Source and context revalidation

Staging does not grandfather a candidate forever.

At decision time the service reopens the source Publication Manifest and revalidates the complete chain back through the Governed Release, governance entry, Human Synthesis Brief and current scientific context.

If the current context no longer reproduces the source artifact hash, the claim decision fails closed and the candidate must be restaged from a current manifest.

## Human decisions

Supported decisions are:

```text
ACCEPT
REJECT
REVISE
```

### REVISE

`REVISE` is non-final.

It records a human request for revision and leaves the candidate without a canonical EvidenceClaim. A later explicit decision may still accept or reject the candidate.

### REJECT

`REJECT` is final for that candidate and creates no EvidenceClaim.

### ACCEPT

`ACCEPT` is the only operation that creates a canonical EvidenceClaim.

It requires:

- reviewer name;
- rationale of at least 20 characters;
- a human-authored claim statement of at least 20 characters;
- source-attribution confirmation;
- scientific-boundary confirmation;
- current source/context revalidation;
- a real matching EvidenceRecord.

The UI deliberately starts the claim statement field **empty**. The source `result_text` is displayed for inspection but is not automatically copied or prefilled into the canonical claim statement.

## Two explicit ACCEPT confirmations

Before acceptance, the reviewer must explicitly confirm both of the following concepts:

1. the claim is a bounded proposition **reported by the linked source**; accepting it does not declare the proposition true or certain merely because the article reports it;
2. EvidenceClaim acceptance does not equal screening inclusion, Risk of Bias, certainty, evidence synthesis or recommendation.

These confirmations are persisted as human-review provenance. They are not cryptographic signatures.

## Canonical claim record

Accepted claims are stored under:

```text
project_output_reference/scientific/evidence_claims/accepted/<claim_id>.json
```

Record type:

```text
NUTEV_CANONICAL_EVIDENCE_CLAIM_RECORD_V1
```

The nested object follows the existing `EvidenceClaim` field contract:

```text
id
evidence_record_id
statement
locator
quote
population
intervention_or_exposure
comparator
outcome
evidence_type
metadata
```

For Fase 16:

```text
claim_semantics = SOURCE_REPORTED_PROPOSITION
locator = source result-bundle id
quote = null
```

`quote = null` is intentional. The result snapshot is provenance/context; the system does not pretend that it is a verified verbatim quotation from full text.

## Canonical does not mean certain

`canonical:true` on the accepted claim record means only that this is the authoritative NutEV record of the **human-accepted source-level proposition**.

It does not mean:

- the study is scientifically valid;
- the study was included in a formal review;
- the claim is true;
- the claim is causal;
- Risk of Bias was assessed;
- certainty was assessed;
- the claim belongs to an EvidenceSet;
- multiple studies agree;
- a recommendation is warranted.

The accepted record explicitly keeps:

```text
claim_acceptance_is_not_screening_inclusion: true
screening_eligibility_verified: false
claim_evaluation_created: false
risk_of_bias_assessed: false
certainty_assessed: false
evidence_set_created: false
canonical_scientific_synthesis_created: false
clinical_recommendation_created: false
meta_analysis_performed: false
prisma_event_emitted: false
pairwise_synthesis_statement_promoted: false
identity_cryptographically_authenticated: false
```

## ClaimEvaluation remains separate

Fase 16 creates **no `ClaimEvaluation`**.

This is deliberate. Acceptance answers:

> Is this a bounded source-level proposition that a human reviewer accepts into the NutEV evidence bank with traceable provenance?

It does not answer:

> How methodologically trustworthy, direct, precise, applicable or certain is this claim?

Those dimensions belong to the next explicit layer.

## No PRISMA event

Claim review does not emit a PRISMA lifecycle event.

EvidenceClaim acceptance is not article screening or eligibility. PRISMA remains derived only from explicit screening/retrieval/inclusion events in the scientific workflow.

## No EvidenceSet or recommendation

An accepted claim does not automatically enter an `EvidenceSet` and cannot automatically create a `RecommendationCandidate`.

Those operations require their own scientific review semantics.

## Local-only coordinator

Fase 16 does not introduce a new remote write endpoint.

It reuses the existing loopback-protected coordinator:

```text
GET  /api/synthesis/releases
POST /api/synthesis/releases/prepare
```

Explicit operations:

```text
STAGE_EVIDENCE_CLAIM_REVIEW
DECIDE_EVIDENCE_CLAIM
```

`server.py` does not need a new mutation route.

## Storage

```text
project_output_reference/scientific/evidence_claims/
  candidates/
  states/
  reviews/
  accepted/
```

Candidate and accepted artifacts carry deterministic content hashes. Lists returned to the UI are bounded to avoid turning this surface into an unbounded source-document transport.

## Identity boundary

Reviewer names are typed provenance labels.

Fase 16 does not implement cryptographic reviewer identity authentication.

## No external LLM decision

The EvidenceClaim review UI/service does not call an external LLM to formulate or accept the canonical scientific claim.

The reviewer writes the canonical claim statement explicitly.

## Adversarial checks

Fase 16 adds:

```text
nutev_tests/test_evidence_claim_review.py
nutev_tests/test_evidence_claim_review_web_contract.py
tools/audit_evidence_claim_review.py
```

The death test blocks regressions such as:

- direct pairwise-statement promotion;
- ACCEPT without a real EvidenceRecord;
- automatic claim statement prefill from result text;
- staging that auto-accepts;
- missing human confirmations;
- silent RoB/certainty/EvidenceSet/recommendation/PRISMA creation;
- fake identity authentication;
- external-LLM scientific claim acceptance.

## Scientific boundary

```text
source snapshot != accepted EvidenceClaim
pairwise synthesis statement != atomic EvidenceClaim
EvidenceClaim acceptance != screening inclusion
EvidenceClaim acceptance != study validity
EvidenceClaim acceptance != Risk of Bias
EvidenceClaim acceptance != certainty
EvidenceClaim acceptance != EvidenceSet synthesis
EvidenceClaim acceptance != recommendation
EvidenceClaim acceptance != meta-analysis
EvidenceClaim acceptance != PRISMA
canonical claim record != canonical scientific synthesis
```
