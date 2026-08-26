# NutEV Scientific Export

Status: executable audited handoff from the Reference Engine into the additive scientific object layer.

This command does **not** perform scientific screening, claim extraction, risk of bias, GRADE, synthesis, PRISMA inference, or clinical recommendation.

## Command

After a successful reference ranking run:

```bash
nutev science-export
```

Default inputs:

```text
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/AUDIT_MANIFEST.json
```

Default output directory:

```text
project_output_reference/scientific/
```

Equivalent explicit invocation:

```bash
nutev science-export \
  --ranking-jsonl project_output_reference/reference_ranking/reference_ranking.jsonl \
  --audit-manifest project_output_reference/reference_ranking/AUDIT_MANIFEST.json \
  --output-dir project_output_reference/scientific
```

## Integrity gate

The export is fail-closed.

Before reading ranking rows it requires:

1. `AUDIT_MANIFEST.json` exists and is a JSON object;
2. `audit_type == REFERENCE_RANKING_AUDIT`;
3. reference audit `status == PASS`;
4. the manifest contains the recorded SHA-256 for `reference_ranking.jsonl`;
5. the current ranking file SHA-256 exactly matches that recorded hash.

A ranked row marked `audit_quarantined` is rejected.

The export never repairs the ranking or substitutes another input after integrity failure.

## Transformation

Each audited ranking row becomes exactly:

```text
DocumentCandidate
  + EvidenceRecord
```

Identity reuses the canonical Reference Engine rule:

```text
DOI -> PMID -> URL -> normalized title
```

The adapter preserves, when present:

- provider;
- source run ID;
- origin SHA-256;
- source master SHA-256;
- canonical taxonomy assignments;
- reference rank, score and tier as technical metadata only.

Ranking metadata is not promoted into scientific judgment.

## Outputs

```text
project_output_reference/scientific/document_candidates.jsonl
project_output_reference/scientific/evidence_records.jsonl
project_output_reference/scientific/scientific_events.jsonl
project_output_reference/scientific/SCIENTIFIC_EXPORT_MANIFEST.json
```

`document_candidates.jsonl` contains bibliographic candidates.

`evidence_records.jsonl` contains the auditable scientific-layer bridge back to provider/run/origin.

`scientific_events.jsonl` records `entered_scientific_layer`. This action is deliberately **not** a PRISMA identification/screening/inclusion event.

`SCIENTIFIC_EXPORT_MANIFEST.json` records source hashes, output hashes, counts, assertions and the interpretation guardrail.

## PRISMA rule

The export does not infer PRISMA counts from ranking.

Immediately after export, absent explicit downstream screening events, PRISMA-derived counts remain zero.

Future PRISMA counts must be derived from explicit actions such as:

```text
identified
duplicate_removed
screened
excluded_screening
sought_for_retrieval
not_retrieved
assessed_for_eligibility
excluded_full_text
included
```

## Scientific boundary

The scientific object flow is:

```text
REFERENCE RANKING
  -> audited science-export
  -> DocumentCandidate
  -> EvidenceRecord
  -> [future explicit screening]
  -> EvidenceClaim
  -> ClaimEvaluation
  -> EvidenceSet
  -> RecommendationCandidate
  -> HumanValidation
```

A document entering the scientific layer means only that its audited reference record was handed off successfully. It does not mean that the document was included in a review or supports a recommendation.

See also `docs/SCIENTIFIC_OBJECT_MODEL.md`.
