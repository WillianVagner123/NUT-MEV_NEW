# ClaimEvaluation / Scientific Appraisal

## Purpose

Phase 17 adds the first explicit scientific appraisal layer downstream of an accepted source-level `EvidenceClaim`.

The flow is:

```text
accepted EvidenceClaim
  -> ClaimEvaluation candidate
  -> explicit human dimension-by-dimension appraisal
  -> finalized ClaimEvaluation record
```

This phase evaluates **one accepted claim at a time**. It does not automatically evaluate the whole study and does not aggregate multiple claims.

## Scientific boundary

An accepted EvidenceClaim means only that a reviewer accepted a bounded proposition as being reported by a traceable source.

A ClaimEvaluation adds explicit human judgments about how that particular claim is supported and how it may be interpreted.

Neither object is automatically equivalent to:

- screening inclusion;
- study validity;
- a validated risk-of-bias judgment;
- GRADE certainty;
- an EvidenceSet;
- scientific synthesis;
- a clinical recommendation;
- meta-analysis;
- PRISMA state.

## Method identifier

Phase 17 uses:

```text
NUTEV_GENERIC_CLAIM_APPRAISAL_V1
```

This is a NutEV-native generic claim-level appraisal contract. It is **not** RoB 2, ROBINS-I, ROBINS-E, QUADAS-2, AMSTAR, GRADE or another external validated instrument.

The system therefore records:

```text
formal_external_instrument_applied: false
formal_risk_of_bias_assessed: false
risk_of_bias_assessed: false
study_validity_determined: false
certainty_assessed: false
overall_certainty_grade_created: false
```

A future phase may implement a named external instrument, but only with an explicit methodology-specific contract and independent tests.

## Six appraisal dimensions

Each finalized appraisal requires all six dimensions.

### `design_appropriateness`

Whether the reported study design is appropriate for supporting the specific claim as written.

### `internal_validity_appraisal`

Human appraisal of internal-validity concerns relevant to the specific claim.

This dimension is deliberately named `internal_validity_appraisal`, not `risk_of_bias`, because Phase 17 does not implement a formal RoB instrument.

### `directness`

How directly the reported population, intervention/exposure, comparator and outcome correspond to the accepted claim.

### `precision`

How precisely the reported result supports the claim, considering the estimates and uncertainty actually available to the assessor.

### `applicability`

How applicable the reported evidence is to the intended scientific context represented by the claim.

### `reporting_completeness`

Whether the available reporting is sufficient to appraise the claim without inventing missing methods, estimates or context.

## Judgment scale

Each dimension must use exactly one of:

```text
FAVORABLE
SOME_CONCERNS
MAJOR_CONCERNS
UNCLEAR
NOT_APPLICABLE
```

Every dimension also requires a human rationale of at least 15 characters.

There is no numerical mapping between these values.

## No automatic aggregation

The six judgments remain separate.

Phase 17 does **not** calculate:

- a mean score;
- a quality score;
- a total score;
- an overall favorable/unfavorable label;
- an evidence level;
- a certainty grade.

The finalized record therefore contains:

```text
numeric_appraisal_score_created: false
automatic_dimension_aggregation_performed: false
appraisal_dimensions_are_not_certainty: true
```

A `FAVORABLE` judgment on one or more dimensions is not a certainty claim.

`MAJOR_CONCERNS` does not automatically exclude the article or invalidate the EvidenceClaim.

## Assessment basis

The assessor must declare what material was actually used:

```text
FULL_TEXT
ABSTRACT_ONLY
SOURCE_SNAPSHOT_ONLY
MIXED
OTHER
UNCLEAR
```

If `OTHER` is selected, additional details are required.

The basis is descriptive provenance. The system does not infer that `FULL_TEXT` makes an appraisal valid or that `ABSTRACT_ONLY` makes it invalid.

## Staging

Staging requires:

- an existing canonical `NUTEV_CANONICAL_EVIDENCE_CLAIM_RECORD_V1`;
- an existing linked `EvidenceRecord`;
- a valid accepted claim state;
- source snapshot integrity;
- publication-manifest/source-context revalidation.

The same claim generates the same ClaimEvaluation candidate regardless of who stages it. The operator name is operational state, not part of the scientific candidate identity.

Staging is idempotent and creates no finalized appraisal.

## Finalization

Finalization requires:

- assessor name;
- general rationale of at least 30 characters;
- assessment basis;
- all six dimensions;
- allowed judgment for every dimension;
- rationale for every dimension;
- explicit confirmation that the generic method is not a formal RoB/GRADE instrument;
- explicit confirmation that judgments apply to the claim and not automatically to the entire study;
- explicit confirmation that ClaimEvaluation is not certainty, EvidenceSet synthesis or recommendation.

The source chain is revalidated again immediately before finalization.

If the scientific context changed after staging, finalization fails closed and the candidate must be staged again under the current context.

## Canonical finalized record

A finalized appraisal is stored as:

```text
NUTEV_CANONICAL_CLAIM_EVALUATION_RECORD_V1
```

`canonical:true` means the record is the authoritative NutEV record of that human appraisal.

It does **not** mean the claim is scientifically true, the study is valid, risk of bias is low or certainty is high.

The embedded `claim_evaluation` follows the existing scientific object model:

```text
id
claim_id
dimensions
assessor
rationale
```

The wrapper adds provenance, assessment basis, methodology metadata, integrity hashes and scientific guardrails.

## Persistence

```text
project_output_reference/scientific/claim_evaluations/
  candidates/<candidate_id>.json
  states/<candidate_id>.json
  finalized/<evaluation_id>.json
```

Candidates are non-canonical.

Finalized evaluations are immutable scientific appraisal records for this phase.

## Coordinator and local-only boundary

Phase 17 does not create a new remote write route.

It reuses:

```text
GET  /api/synthesis/releases
POST /api/synthesis/releases/prepare
```

with explicit operations:

```text
STAGE_CLAIM_EVALUATION
FINALIZE_CLAIM_EVALUATION
```

Those endpoints retain the existing loopback-only enforcement.

## UI

`/claim-appraisal.html` exposes:

- accepted EvidenceClaims eligible for staging;
- accepted claim statement;
- source-linked result snapshot;
- assessment basis;
- six dimension judgments;
- rationale per dimension;
- overall rationale;
- three scientific-boundary confirmations;
- finalized ClaimEvaluation ledger.

The UI contains no automatic scientific judgment, external LLM call or aggregate score.

## CI / adversarial audit

Phase 17 adds:

```text
nutev_tests/test_claim_evaluation_appraisal.py
nutev_tests/test_claim_evaluation_appraisal_web_contract.py
tools/audit_claim_evaluation_appraisal.py
```

The adversarial audit fails if the layer:

- auto-finalizes during staging;
- adds an automatic score or aggregate judgment;
- claims formal RoB/GRADE;
- loses EvidenceRecord/source revalidation;
- drops explicit human confirmations;
- invokes an external LLM to create appraisal judgments;
- mutates screening, EvidenceClaim wording, EvidenceSet, recommendation or PRISMA state.
