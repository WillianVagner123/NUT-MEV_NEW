# Scientific Intelligence / Synthesis Layer

`/intelligence.html` is the first NutEV layer dedicated to scientific synthesis support for Article 1.

It is deliberately narrower than an automated evidence synthesis engine. The page organizes the verified Tier A corpus into presentation-ready structural views and source-linked review queues while preserving human scientific judgment.

## Inputs

The structural layer uses the verified, rank-blind Agent Context:

- `agent-context/article1/ARTICLE_SUMMARIES.jsonl`;
- `agent-context/article1/SEARCH_STATE.json`.

These surfaces provide document identity, year, provider, document class, operational domains, Article 1 routes and counts of materialized excerpts/result bundles. They do not expose Bank rank/score or machine relevance scores.

For textual finding inspection the page loads article details lazily through:

```text
GET /api/articles/{document_id}
```

Only a bounded batch of up to 24 finding-ready documents is loaded for the selected domain, with at most four detail requests in flight. The page never fetches every article detail automatically and never receives full text integral.

## Domain synthesis

For each operational domain the page derives, from runtime data:

- number of mapped Tier A documents;
- document-class distribution;
- number of documents with materialized result bundles;
- B-NORM count;
- C-STRUCT count;
- B-NORM/C-STRUCT overlap;
- publication-year range.

These are corpus-organization signals. They are not evidence strength, certainty, eligibility or inclusion.

## Finding candidates

When a domain is selected, NutEV loads a bounded operational batch of documents that already have result bundles. For each loaded article the page shows one materialized result candidate, preferring the bundle already marked `main_result` by the deterministic extraction layer.

Displayed fields may include:

- result text candidate;
- structured outcome labels;
- effect measures;
- confidence intervals;
- p-values;
- route and bibliographic metadata.

A result bundle remains `machine_candidate_not_evidence_claim`. The synthesis UI does not convert it into an accepted EvidenceClaim.

The batch is sorted deterministically for navigation and is explicitly not a statistical sample or importance ranking.

## Recurrence is not convergence

The page can group exact normalized outcome labels that appear in two or more loaded documents. This only means the same structured label recurred in the bounded inspection batch.

It does **not** establish:

- agreement of direction;
- consistency of effect;
- clinical equivalence;
- meta-analytic compatibility;
- certainty;
- scientific consensus.

The current result-bundle schema does not contain a validated direction/stance field capable of supporting automatic convergence/divergence classification.

Therefore `/intelligence.html` creates a **human comparison queue**: source-linked result candidates are placed side by side, and the reviewer determines whether they converge, diverge, address different populations/outcomes or are not meaningfully comparable.

## Corpus coverage signals are not evidence gaps

The page highlights domains with fewer mapped documents or fewer result bundles to help reviewers decide where to inspect the corpus more closely.

Sparse mapping can arise from many causes, including:

- the discovery corpus itself;
- route/domain taxonomy;
- extraction availability;
- missing full text;
- classification limitations;
- actual literature distribution.

For that reason the UI calls these **corpus coverage signals** and never automatically labels them `evidence gap`.

## Export

`Exportar JSON` creates a browser-side `NUTEV_SCIENTIFIC_INTELLIGENCE_VIEW_V1` artifact containing:

- structural domain synthesis for the full loaded Agent Context;
- the currently selected domain;
- only the finding candidates that were lazily loaded in the current view;
- recurring outcome labels observed in that loaded batch;
- explicit guardrails.

The export is a view artifact, not a frozen scientific decision or PRISMA event. `Print / PDF` uses the browser print surface.

## Guardrails

The Scientific Intelligence layer must remain:

- read-only;
- rank-blind;
- free of direct external LLM endpoints;
- bounded/lazy for article detail loading;
- explicit that result bundles are not accepted EvidenceClaims;
- explicit that recurrence is not consensus;
- explicit that sparse mapping is not an evidence gap;
- explicit that convergence/divergence requires human review;
- unable to approve PRESS, authorize GF-10, freeze a query, execute a formal provider search or emit PRISMA.

`tools/audit_scientific_workspace_v2.py` enforces these contracts in CI.
