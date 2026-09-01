# RecommendationCandidate HumanValidation

## Purpose

Phase 20 adds an explicit human validation gate after a finalized `RecommendationCandidate`.

The workflow is:

```text
finalized RecommendationCandidate
  -> HumanValidation case PENDING
  -> explicit human decision: ACCEPT | REJECT | REVISE
  -> canonical HumanValidation decision record
```

This phase does **not** create a clinical recommendation, guideline recommendation, GRADE certainty judgment, formal Risk of Bias assessment, meta-analysis, PRISMA event, or canonical scientific synthesis.

## Scientific object model

The NutEV scientific model already defines:

```text
HumanValidation
  id
  target_type
  target_id
  decision: pending | accept | reject | revise
  reviewer
  rationale
  reviewed_at
```

Phase 20 operationalizes that object specifically for:

```text
target_type = RecommendationCandidate
```

The canonical record type is:

```text
NUTEV_CANONICAL_HUMAN_VALIDATION_RECORD_V1
```

`canonical:true` means NutEV treats the **validation decision record and its provenance** as authoritative. It does not mean the candidate is an authoritative clinical recommendation or scientifically certain statement.

## Decision semantics

### PENDING

A validation case has been opened. No decision has been made.

`PENDING` does not mean partial acceptance, preliminary recommendation, readiness, or implied reviewer agreement.

### ACCEPT

`ACCEPT` means:

> the named human reviewer explicitly accepted the RecommendationCandidate for the declared review scope.

It does **not** mean:

- a clinical recommendation was created;
- a guideline recommendation was created;
- the recommendation is strong or weak;
- certainty/GRADE was assessed;
- formal Risk of Bias was assessed;
- all linked EvidenceSets agree;
- the EvidenceSets are sufficient for clinical action;
- causality was established;
- the candidate became a canonical scientific synthesis;
- a PRISMA event occurred.

The canonical HumanValidation record therefore exposes:

```text
candidate_accepted_for_declared_scope: true
validated_recommendation_created: false
clinical_recommendation_created: false
guideline_recommendation_created: false
certainty_assessed: false
grade_assessed: false
formal_risk_of_bias_assessed: false
```

### REJECT

`REJECT` records that the reviewer did not accept the candidate for the declared review scope.

It does not delete or rewrite the RecommendationCandidate. The rejected candidate remains an immutable upstream scientific record with its original provenance.

### REVISE

`REVISE` requires explicit human revision instructions.

The system does not apply the requested changes automatically. A revised wording must be authored through a **new RecommendationCandidate workflow**, preserving the original candidate and the HumanValidation decision that requested revision.

This prevents silent mutation of scientific history.

## Candidate immutability and readiness

HumanValidation is stored separately from the RecommendationCandidate.

After any decision:

```text
recommendation_candidate_changed: false
readiness_changed: false
readiness_evaluated: false
```

The original RecommendationCandidate continues to carry:

```text
readiness = not_evaluated
recommendation_validated = false
human_validation_created = false
clinical_recommendation_created = false
```

Those fields describe the immutable Phase 19 candidate artifact itself. Phase 20 exposes validation state through a metadata-only join in coordinator status rather than rewriting the candidate JSON.

## Referential integrity and fail-closed behavior

Before staging and before a final decision, NutEV revalidates:

```text
RecommendationCandidate canonical record
  -> candidate content SHA-256
  -> candidate EvidenceSet snapshots
  -> canonical EvidenceSets
  -> EvidenceClaim snapshots
  -> ClaimEvaluation snapshots
  -> EvidenceRecord provenance
  -> source context fingerprint
  -> search id / context version
```

If the chain no longer matches the current context, the operation fails closed.

A stale or modified candidate cannot be human-validated merely because an old JSON file still exists.

## One canonical decision per candidate

Phase 20 creates one HumanValidation case per finalized RecommendationCandidate.

A repeated identical decision is idempotent. A conflicting later decision is rejected rather than overwriting the canonical record.

This phase intentionally does not implement:

- multiple independent reviewer votes;
- consensus panels;
- majority voting;
- adjudication between validators;
- authentication of reviewer identity;
- electronic signatures.

Those would require a separate governance model.

## Identity boundary

Reviewer names are provenance labels entered by users.

The system records:

```text
identity_cryptographically_authenticated: false
```

No typed name is represented as a cryptographically authenticated identity or digital signature.

## Coordinator boundary

No new remote write route is introduced and `server.py` is not changed.

Phase 20 reuses the existing loopback-only coordinator:

```text
GET  /api/synthesis/releases
POST /api/synthesis/releases/prepare
```

with explicit operations:

```text
STAGE_RECOMMENDATION_HUMAN_VALIDATION
DECIDE_RECOMMENDATION_HUMAN_VALIDATION
```

## UI behavior

`/recommendation-human-validation.html` provides:

- finalized RecommendationCandidates and their validation state;
- manual opening of a `PENDING` validation case;
- an empty decision selector with no default;
- explicit `ACCEPT`, `REJECT`, and `REVISE` choices;
- reviewer and rationale fields;
- revision instructions required only for `REVISE`;
- four scientific-boundary confirmations;
- finalized canonical HumanValidation records.

There is no automatic decision path and no external LLM call.

## Guardrails

Canonical HumanValidation records preserve:

```text
human_validation_created: true
human_validation_decision_recorded: true
automatic_validation_decision_performed: false
automatic_revision_applied: false
target_revalidated_at_decision: true
recommendation_candidate_changed: false
readiness_changed: false
readiness_evaluated: false
validated_recommendation_created: false
clinical_recommendation_created: false
guideline_recommendation_created: false
certainty_assessed: false
grade_assessed: false
formal_risk_of_bias_assessed: false
canonical_scientific_synthesis_created: false
meta_analysis_performed: false
prisma_event_emitted: false
identity_cryptographically_authenticated: false
```

## Central interpretation boundary

```text
HumanValidation ACCEPT != clinical recommendation
HumanValidation ACCEPT != guideline recommendation
HumanValidation ACCEPT != certainty/GRADE
HumanValidation != formal Risk of Bias
HumanValidation does not alter RecommendationCandidate readiness
REVISE does not mutate RecommendationCandidate
HumanValidation != canonical scientific synthesis
HumanValidation != meta-analysis
HumanValidation != PRISMA
```
