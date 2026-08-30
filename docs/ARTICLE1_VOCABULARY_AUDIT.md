# Article 1 route vocabulary audit

Status: deterministic, read-only strategy audit over the rank-blind `B-NORM` and `C-STRUCT` reading queues.

## Purpose

The audit helps a human search-methods reviewer inspect whether the current candidate query architecture is missing recurring terminology present in the discovery corpus. It does **not** validate the formal search and does not automatically add terms to any query.

The discovery corpus cannot retroactively validate a formal search strategy built from that same corpus. Any candidate term surfaced here requires an independent human decision and later PRESS/protocol review.

## Inputs

The tool requires a passing Article 1 route queue manifest and verifies the SHA-256 of both rank-blind route files before reading them.

```text
project_output_reference/scientific/review_routes/<search_id>/article1/
  ROUTE_QUEUE_MANIFEST.json
  B-NORM.jsonl
  C-STRUCT.jsonl
```

If a route row exposes `reference_rank`, `reference_score`, `reference_tier`, `machine_relevance_score`, or `machine_relevance_band`, the audit fails closed.

## Command

```bash
python tools/audit_article1_route_vocabulary.py \
  --search-id <search_id> \
  --output-root project_output_reference
```

## Method

For each route the audit:

1. verifies the route manifest and route-file hashes;
2. mines document-frequency counts for 2- to 4-token phrases from article titles only;
3. reports title-level coverage of the current candidate baseline terms;
4. flags recurring phrases not represented by that baseline for **manual query review**;
5. reports the route's machine-class and operational-domain distributions.

The phrase flag is deliberately conservative and is not a recommendation to add the phrase.

## Baseline interpretation

`B-NORM` mirrors the current candidate normative architecture (`nutrition/diet/food-based/dietary pattern` plus guideline/guidance/recommendation/consensus/statement/standard families). This file does not freeze or version a database-specific search string.

`C-STRUCT` contains a candidate lexicon for framework/model, competencies, food/nutrition literacy, food skills, culinary medicine, Nutrition Care Process, implementation, assessment, counseling, prescription, monitoring/follow-up, and lifestyle medicine. It is explicitly **not** a frozen formal query.

## Output

```text
project_output_reference/scientific/review_routes/<search_id>/article1/
  VOCABULARY_AUDIT.json
```

The report records baseline coverage, top title phrases, manual-review candidates, route distributions, source hashes, and guardrails.

## Scientific boundary

This stage does not:

- include or exclude any document;
- create a `ScreeningDecision`;
- create a PRISMA event;
- establish search sensitivity or specificity;
- establish completeness of the evidence base;
- assign quality, risk of bias, certainty, causal interpretation, or recommendation;
- modify a formal query automatically;
- call an external LLM.

The intended next step is human review of the vocabulary audit, followed by explicit versioned query drafting and PRESS-style review before any formal route-specific search is frozen or executed.
