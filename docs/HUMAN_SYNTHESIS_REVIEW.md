# Human Synthesis Review

`/synthesis-review.html` turns the comparison queues produced by Scientific Intelligence into explicit, traceable human judgments without changing canonical scientific state.

The page is deliberately a **local draft workspace**. It does not perform formal screening, risk-of-bias assessment, certainty assessment, PRESS review, GF-10 authorization or PRISMA actions.

## Why this layer exists

The current deterministic `result_bundles` provide source-linked result candidates with structured outcomes, effect measures, confidence intervals, p-values and short result text. They do not provide a validated scientific direction/stance field that can support automatic claims of agreement or contradiction.

For that reason NutEV does not infer convergence/divergence from wording, p-values or repeated outcome labels. A human reviewer must inspect two source-linked findings and record the relationship explicitly.

## Inputs

The workspace uses the same rank-blind surfaces as Scientific Intelligence:

- `agent-context/article1/ARTICLE_SUMMARIES.jsonl`;
- `agent-context/article1/SEARCH_STATE.json`;
- lazy `GET /api/articles/{document_id}` detail requests.

The detail batch is capped at 18 finding-ready documents for the selected domain with at most four requests in flight. Only materialized result bundles are used; full text integral is not returned to the page.

## Review dimensions

Before assigning a relationship, the reviewer records comparability in four dimensions:

1. population;
2. construct/intervention/exposure;
3. outcome;
4. timeframe/follow-up.

Each dimension can be marked:

- `SIMILAR`;
- `DIFFERENT`;
- `UNCLEAR`;
- `NOT_AVAILABLE`.

These fields are descriptive reviewer judgments. They are not automated eligibility criteria.

## Human relationship labels

The reviewer can assign one of five pairwise labels:

- `CONVERGENT`;
- `DIVERGENT`;
- `COMPLEMENTARY`;
- `NOT_COMPARABLE`;
- `UNCLEAR`.

NutEV does not preselect any of these values. The reviewer name, a relationship label and a rationale of at least 20 characters are required before a judgment can be saved.

The labels are intentionally pairwise and local to the reviewed findings:

- `CONVERGENT` does not mean high certainty or meta-analytic consistency;
- `DIVERGENT` does not prove scientific contradiction;
- `NOT_COMPARABLE` is not an exclusion decision;
- `UNCLEAR` is a valid review outcome and is not silently resolved by machine inference.

## Local draft persistence

Draft decisions are stored in browser `localStorage` under a key scoped to the Article 1 `search_id` and Agent Context version.

This persistence exists only to let the reviewer continue the current browser session/workflow. It is not a canonical scientific registry, server write or repository mutation.

Changing or clearing browser storage can remove the local draft. Therefore a review that needs to circulate must be exported.

## Export artifact

`Exportar revisão` creates:

```text
NUTEV_HUMAN_SYNTHESIS_REVIEW_DRAFT_V1
```

The export contains:

- search/context identity;
- scientific question;
- reviewer identity;
- pairwise decisions;
- comparability dimensions;
- reviewer rationale;
- timestamps;
- source snapshots for both findings, including document id, bundle id, source-sentence SHA-256 when available, result text and structured quantitative fields;
- explicit scientific guardrails.

A deterministic SHA-256 is computed over the scientific content before `generated_at` is added. The digest is stored as `content_sha256` and included in the filename.

The export remains:

```text
canonical: false
```

Exporting the file does not make the judgments canonical. A later governance layer may validate/import reviewed artifacts into a canonical synthesis registry; this phase does not do that.

## Guardrails

The Human Synthesis Review layer must not:

- infer pairwise relation automatically;
- save a judgment without reviewer identity;
- save a judgment without reviewer rationale;
- treat convergence as certainty;
- treat divergence as proven contradiction;
- treat non-comparability as exclusion;
- create accepted EvidenceClaims;
- assess RoB or certainty;
- mutate PRESS, GF-10, query-freeze or formal-search state;
- emit PRISMA events;
- send data to an external LLM endpoint;
- POST scientific decisions to the public NutEV web server.

The Scientific Workspace death test and dedicated UI tests enforce these boundaries.
