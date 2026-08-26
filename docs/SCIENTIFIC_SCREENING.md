# NutEV Scientific Screening Contract

Status: explicit import of **final resolved** screening decisions.

NutEV does not decide inclusion/exclusion in this stage. It validates externally resolved decisions, links them to known `DocumentCandidate` IDs, emits lifecycle events, and derives PRISMA counts from those events.

## Command

After `nutev science-export`, prepare:

```text
project_output_reference/scientific/screening_decisions_input.jsonl
```

Then run:

```bash
nutev science-screening
```

Equivalent explicit invocation:

```bash
nutev science-screening \
  --documents-jsonl project_output_reference/scientific/document_candidates.jsonl \
  --science-manifest project_output_reference/scientific/SCIENTIFIC_EXPORT_MANIFEST.json \
  --decisions-jsonl project_output_reference/scientific/screening_decisions_input.jsonl \
  --output-dir project_output_reference/scientific/screening
```

## Decision schema

One JSON object per line:

```json
{
  "id": "ta-doi-10.1000-example",
  "document_id": "doi:10.1000/example",
  "stage": "title_abstract",
  "decision": "include",
  "adjudicator": "reviewer-final",
  "reason": null,
  "decided_at": "2026-08-26T20:00:00-03:00",
  "metadata": {}
}
```

Required fields:

```text
id
document_id
stage
decision
decided_at
```

Stages:

```text
title_abstract
full_text
```

Decisions:

```text
include
exclude
uncertain
```

Every final exclusion requires an explicit `reason`.

## Final-decision rule

This input represents the **resolved final decision**, not each assessor vote.

For a two-reviewer workflow:

```text
reviewer A assessment
reviewer B assessment
        -> agreement/adjudication
        -> one final ScreeningDecision
        -> PRISMA events
```

The importer rejects multiple final decisions for the same `document_id + stage` in one input set. This prevents two reviewer votes from being counted as two screened studies.

## Event semantics

### Title/abstract

`include` or `uncertain`:

```text
screened
```

`exclude`:

```text
screened
excluded_screening
```

A title/abstract `include` does **not** mean final study inclusion.

### Full text

`include`:

```text
assessed_for_eligibility
included
```

`exclude`:

```text
assessed_for_eligibility
excluded_full_text
```

`uncertain`:

```text
assessed_for_eligibility
```

The importer does not infer retrieval events. `sought_for_retrieval` and `not_retrieved` require their own future explicit events.

## Integrity gates

Before importing decisions, NutEV verifies:

1. `SCIENTIFIC_EXPORT_MANIFEST.json` is a passing NutEV scientific export manifest;
2. the current `document_candidates.jsonl` SHA-256 matches the manifest;
3. every decision references a known document ID;
4. decision IDs are unique;
5. there is at most one final decision per document/stage;
6. exclusions have reasons;
7. stage and decision tokens are valid.

## Outputs

```text
project_output_reference/scientific/screening/screening_decisions.jsonl
project_output_reference/scientific/screening/screening_events.jsonl
project_output_reference/scientific/screening/PRISMA_COUNTS.json
project_output_reference/scientific/screening/SCREENING_IMPORT_MANIFEST.json
```

`PRISMA_COUNTS.json` is a derived view of the explicit imported final decisions. It is not an independently maintained source of truth.

## Current boundary

This stage does not yet implement:

- blinded reviewer-level screening assessments;
- conflict detection/adjudication UI for article screening;
- full-text retrieval state;
- automated claim extraction;
- risk of bias;
- GRADE;
- evidence synthesis.

Those are separate downstream contracts.
