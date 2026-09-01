# RecommendationCandidate Drafting

## Status

Phase 19 adds explicit human-authored `RecommendationCandidate` construction downstream of finalized `EvidenceSet` records.

The phase does **not** validate a recommendation, assign certainty, calculate readiness, create a clinical recommendation, perform meta-analysis, or mutate PRISMA state.

## Scientific flow

```text
accepted EvidenceClaim
  -> finalized ClaimEvaluation
  -> finalized EvidenceSet
  -> RecommendationCandidate draft
  -> finalized RecommendationCandidate
  -> future explicit HumanValidation
```

The final arrow is intentionally not implemented in this phase.

## Source requirements

A RecommendationCandidate can only reference finalized canonical EvidenceSets.

At staging and finalization the service revalidates each selected EvidenceSet and its upstream provenance:

- EvidenceSet record type and canonical hash;
- human-finalized status;
- human-curated membership;
- EvidenceClaim and ClaimEvaluation member snapshots;
- EvidenceRecord-linked claim provenance;
- source context fingerprint;
- search id;
- context version.

If an EvidenceSet no longer matches current claim/evaluation/context state, the operation fails closed and requires restaging.

## Human authorship

The system does not generate the recommendation statement.

The UI starts with an empty statement field. Staging requires an explicit confirmation that the text was written by a human.

The system does not:

- copy an EvidenceSet focus statement into the candidate;
- concatenate EvidenceClaims into a recommendation;
- call an external LLM to create scientific wording;
- derive wording from relationship counts, appraisal dimensions, ranking, taxonomy, or membership size.

## EvidenceSet selection

EvidenceSets are manually selected. No set is selected by default.

One or more finalized EvidenceSets may be referenced, up to the phase limit of 20.

All selected sets must share the same:

```text
source_context_fingerprint
search_id
context_version
```

This prevents one candidate from silently mixing incompatible scientific workbench states.

## Readiness

Every draft and finalized candidate uses:

```text
readiness = not_evaluated
```

Phase 19 never calculates or upgrades readiness.

The following are not readiness signals:

- number of EvidenceSets;
- number of claims;
- number of favorable ClaimEvaluation dimensions;
- presence of multiple studies;
- repeated outcome labels;
- pairwise convergence;
- governance approval;
- EvidenceSet membership.

## Draft contract

A draft is:

```text
NUTEV_RECOMMENDATION_CANDIDATE_DRAFT_V1
canonical: false
```

Staging requires:

- human-authored statement >= 30 characters;
- rationale >= 30 characters;
- intended audience;
- intended context;
- at least one finalized EvidenceSet;
- staging operator name;
- explicit human-authorship confirmation.

Staging never finalizes the candidate automatically.

## Finalization contract

Finalization requires:

- finalizer name;
- finalization rationale >= 30 characters;
- confirmation that EvidenceSet membership/count is not certainty, consensus, or evidence strength;
- confirmation that the candidate is not a validated recommendation;
- confirmation that a later explicit `HumanValidation` is required.

Only explicit finalization creates:

```text
NUTEV_CANONICAL_RECOMMENDATION_CANDIDATE_RECORD_V1
```

The embedded scientific object follows the existing `RecommendationCandidate` model:

```text
id
statement
evidence_set_ids
readiness = not_evaluated
rationale
```

Additional provenance is stored in metadata.

## Meaning of canonical

`canonical:true` means the RecommendationCandidate record is the authoritative NutEV record of that **candidate text and provenance**.

It does not mean:

- the recommendation is accepted;
- the recommendation is clinically indicated;
- the recommendation is guideline-grade;
- the evidence has high certainty;
- GRADE was performed;
- formal Risk of Bias was performed;
- the EvidenceSets agree;
- a canonical scientific synthesis exists.

## Guardrails

A finalized candidate explicitly preserves:

```text
recommendation_candidate_created: true
automatic_statement_generation_performed: false
automatic_readiness_inference_performed: false
readiness_evaluated: false
recommendation_validated: false
human_validation_created: false
evidence_sets_revalidated_at_finalization: true
evidence_set_agreement_inferred: false
evidence_set_contradiction_inferred: false
evidence_set_scores_aggregated: false
certainty_assessed: false
overall_certainty_grade_created: false
formal_risk_of_bias_assessed: false
clinical_recommendation_created: false
canonical_scientific_synthesis_created: false
meta_analysis_performed: false
prisma_event_emitted: false
single_evidence_set_candidate_is_not_validated_recommendation: true
multiple_evidence_sets_do_not_imply_consensus: true
identity_cryptographically_authenticated: false
```

## Upstream immutability

Finalizing a RecommendationCandidate does not rewrite EvidenceSets, EvidenceClaims, or ClaimEvaluations.

The release/status surface performs a metadata-only join to expose which RecommendationCandidates reference each EvidenceSet.

This downstream index is not written back into the canonical EvidenceSet artifact.

## Local-only coordinator

No new remote write route is introduced and `server.py` remains unchanged.

The existing loopback-only coordinator handles:

```text
GET /api/synthesis/releases
POST /api/synthesis/releases/prepare
```

with explicit operations:

```text
STAGE_RECOMMENDATION_CANDIDATE
FINALIZE_RECOMMENDATION_CANDIDATE
```

## UI

`/recommendation-candidates.html` provides:

- manual finalized-EvidenceSet selection;
- an empty human-authored statement field;
- rationale, intended audience and intended context;
- explicit authorship confirmation;
- RecommendationCandidate drafts;
- explicit finalization confirmations;
- finalized candidate ledger;
- visible `readiness=not_evaluated`;
- explicit candidate-versus-recommendation boundary.

## Verification

Phase 19 adds:

- `nutev_tests/test_recommendation_candidate_drafting.py`;
- `nutev_tests/test_recommendation_candidate_drafting_web_contract.py`;
- `tools/audit_recommendation_candidate_drafting.py`;
- an eighth adversarial death test in CI;
- `node --check apps/nutev-web/recommendation-candidates.js`.

## Interpretation boundary

```text
RecommendationCandidate != validated recommendation
RecommendationCandidate != clinical recommendation
EvidenceSet count != evidence strength
EvidenceSet membership != consensus
readiness = not_evaluated
RecommendationCandidate != certainty / GRADE
RecommendationCandidate != canonical scientific synthesis
RecommendationCandidate != meta-analysis
RecommendationCandidate != PRISMA
```
