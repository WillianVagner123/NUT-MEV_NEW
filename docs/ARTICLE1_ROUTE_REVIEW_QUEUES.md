# Article 1 route review queues

Status: deterministic, rank-blind human-reading navigation over the technically deepened Tier A corpus.

This layer is **not scientific screening**. It does not emit eligibility, inclusion/exclusion, PRISMA events, quality, risk-of-bias, certainty, causal interpretation, or recommendations.

## Purpose

The Article 1 discovery corpus is split into two reading routes that reflect the planned formal search architecture without pretending that the discovery corpus is already a formal PRISMA set:

- `B-NORM`: normative/guidance documents;
- `C-STRUCT`: operational structures, competencies, literacy, care-process and implementation material.

Documents may appear in both routes. Documents in neither route remain in the evidence bank and are explicitly **unrouted, not excluded**.

## Source requirements

The queue builder requires:

1. a passing Tier A `REVIEW_QUEUE_MANIFEST.json`;
2. review profile version `nutev_review_profile_rule_v2`;
3. matching SHA-256 for `review_profiles.jsonl`;
4. a passing Article Workbench manifest;
5. matching SHA-256 for the active Workbench SQLite database;
6. a 1:1 join from every review profile to a Workbench article.

## B-NORM routing

A document enters `B-NORM` when the reviewer profile classifies the document itself as one of:

- `food_based_dietary_guideline`;
- `clinical_practice_guideline`;
- `consensus_statement`;
- `position_statement`.

The v2 document-shape classifier is title-specific, so a study *about* a guideline is not routed as though it were the guideline itself.

## C-STRUCT routing

A document enters `C-STRUCT` when one or more operational signals are present:

- document class: `framework_model`, `implementation_evaluation`, or `competency_curriculum`;
- strong domain: `food_skills_competencies`, `food_literacy`, `nutrition_care_process`, or `implementation_practice`;
- `lifestyle_medicine` together with at least one care-process domain;
- at least two care-process domains among assessment, counseling, prescription and monitoring/follow-up;
- `social_context` together with an operational/food-guidance signal.

These rules are intentionally broad enough for human reading and intentionally **do not assert relevance or eligibility**.

## Blindness

The emitted reviewer queues do not expose:

- Bank NutEV `reference_rank`;
- `reference_score`;
- Tier label;
- `machine_relevance_score`;
- `machine_relevance_band`.

Queue order is a deterministic SHA-256 order derived from search ID + route + document ID, not Bank rank.

Route identity is visible because it defines the reading task; route assignment remains a machine navigation aid.

## Command

```bash
python tools/build_article1_route_queues.py \
  --search-id '<search-id>' \
  --output-root project_output_reference \
  --tier A
```

## Outputs

```text
project_output_reference/scientific/review_routes/<search-id>/article1/B-NORM.jsonl
project_output_reference/scientific/review_routes/<search-id>/article1/C-STRUCT.jsonl
project_output_reference/scientific/review_routes/<search-id>/article1/ROUTE_QUEUE_MANIFEST.json
```

The manifest records route counts, overlap, unrouted documents, class/domain distributions, source hashes and blindness assertions.

## Boundary with formal screening

The canonical scientific screening contract remains unchanged:

```text
verified ReviewerDossier
  -> human review / adjudication
  -> final resolved ScreeningDecision
  -> science-screening
  -> PRISMA events
```

Route queues must not be passed to `science-screening` as if route assignment were a final reviewer decision.
