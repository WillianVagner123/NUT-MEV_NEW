# Human Synthesis Brief

The Human Synthesis Brief is the presentation/export layer that follows the Human Synthesis Review.

It does **not** generate scientific conclusions from the machine corpus. It only renders a human-review draft after that draft passes local integrity and context checks.

## Flow

```text
Scientific Intelligence
  -> Human Synthesis Review
     -> exported noncanonical human-review draft
        -> Human Synthesis Brief
```

The source review artifact remains:

```text
NUTEV_HUMAN_SYNTHESIS_REVIEW_DRAFT_V1
canonical: false
```

The brief export is:

```text
NUTEV_HUMAN_SYNTHESIS_BRIEF_V1
canonical: false
```

Neither export changes canonical scientific state.

## Source-review verification

The brief processes the imported JSON entirely in the browser.

Before any reviewed relationship is rendered, the following conditions must all pass:

1. artifact type is exactly `NUTEV_HUMAN_SYNTHESIS_REVIEW_DRAFT_V1`;
2. source artifact is `canonical: false`;
3. at least one human decision is present;
4. every decision has a known relation, named reviewer and rationale of at least 20 characters;
5. every decision has valid comparability values for population, construct/intervention, outcome and timeframe;
6. pair identifiers match the two source document IDs and duplicate decision IDs are rejected;
7. source snapshots contain document IDs, result-bundle IDs and result text;
8. the source-review guardrails explicitly state that convergence/divergence was human-entered and that no EvidenceClaims, screening, RoB, certainty, PRISMA event or formal-search mutation was created;
9. the deterministic content SHA-256 recomputed by the browser matches `content_sha256`;
10. the review context fingerprint is internally consistent and matches the current Article 1 context.

Any failure blocks the brief, print and export controls.

## Strong context binding

`search_id` and `context_version` alone are insufficient to prove that a human review belongs to the current materialized Workbench.

The Human Synthesis Review therefore now derives a deterministic context source object from safe runtime state:

```text
search_id
context_version
question
workbench database SHA-256
Article 1 route manifest SHA-256
review-profile version
agent article-summary count
```

The SHA-256 of this object becomes `context_fingerprint`.

Browser-local review storage is also namespaced by this fingerprint. A rebuilt Workbench/context therefore does not silently reuse a local review draft created against a previous materialization.

The exported review carries both:

```text
context_source
context_fingerprint
```

The Brief recomputes the fingerprint from the current `SEARCH_STATE.json` and fails closed if the imported review does not match.

## What SHA-256 means here

SHA-256 verifies content consistency against the digest carried by the artifact and helps detect accidental or untracked modification after export.

It does **not** prove:

- who authored the artifact;
- that the reviewer identity is authentic;
- that the judgment is scientifically correct;
- that the review process was complete;
- that the evidence is high quality;
- that the conclusions are certain.

There is no cryptographic signature or trusted identity-attestation layer in this phase.

Therefore:

```text
content hash match != authorship/authenticity
context fingerprint match != scientific validation
```

## Presentation semantics

After verification, the brief can show:

- number of human pairwise decisions;
- number of unique source-linked documents represented;
- domains represented in the imported review;
- descriptive counts of `CONVERGENT`, `DIVERGENT`, `COMPLEMENTARY`, `NOT_COMPARABLE` and `UNCLEAR`;
- comparability profile across population, construct/intervention, outcome and timeframe;
- reviewer rationale for each pair;
- source result text plus result-bundle/source-sentence provenance when present.

These are descriptive summaries of a human-review artifact.

They are not pooled statistical estimates.

## Relationship-count boundary

A count of human relation labels must never be interpreted as evidence strength or certainty.

Examples:

```text
8 CONVERGENT pairs != high certainty
3 DIVERGENT pairs != proven contradiction
2 NOT_COMPARABLE pairs != scientific exclusion
```

Pairwise decisions are not statistically independent by definition: a document may appear in multiple pairs, and pair counts are not a denominator for meta-analysis.

## Export

`Exportar brief` creates `NUTEV_HUMAN_SYNTHESIS_BRIEF_V1` only after source integrity and current-context matching pass.

The exported content includes:

- source review type;
- source review content SHA-256;
- source context fingerprint;
- search/context identifiers;
- question and reviewer;
- descriptive relation/domain/comparability counts;
- the reviewed pairwise decisions;
- explicit scientific guardrails;
- a deterministic SHA-256 for the brief content itself.

The brief remains `canonical: false`.

## Print / PDF

The browser print layout hides file-import/verification controls and preserves the scientific boundary in the rendered presentation.

Print/PDF is a presentation operation only. It does not freeze, approve or publish a canonical synthesis.

## Explicit non-goals

The Human Synthesis Brief does not:

- accept machine result bundles as EvidenceClaims;
- assess risk of bias;
- assess certainty;
- perform meta-analysis;
- compute pooled effect sizes;
- infer causal conclusions;
- create screening decisions;
- emit PRISMA events;
- modify PRESS/GF-10/query-freeze state;
- authenticate reviewer identity;
- call an external LLM.

## Death-test contract

`tools/audit_scientific_workspace_v2.py` fails if the brief loses any of the following protections:

- noncanonical semantics;
- fail-closed verification;
- content SHA verification;
- strong current-context fingerprint verification;
- validation of human-review guardrails;
- explicit authorship/authenticity disclaimer;
- relationship-count/certainty boundary;
- no scientific-state creation;
- rank-blind behavior;
- no external LLM endpoint or scientific POST mutation.

The CI also runs `node --check apps/nutev-web/synthesis-brief.js`.
