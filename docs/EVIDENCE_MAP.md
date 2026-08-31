# NutEV Article 1 Evidence Map

The Evidence Map is a read-only visual layer over the verified, rank-blind Article 1 agent context.

## Data source

The page reads only:

```text
/agent-context/article1/ARTICLE_SUMMARIES.jsonl
```

It does not query or download the full 33k Workbench corpus.

## Views

### Matrix

Crosses operational domains with detected document shape. Cells display document counts and can drill into the matching Evidence Explorer intersection.

A zero cell means only:

> no documents mapped by the current deterministic profile

It must never be rendered or interpreted automatically as an evidence gap, absence of literature, absence of effect, lack of certainty, or recommendation.

### Route

Shows domain counts across B-NORM, C-STRUCT, overlap and unrouted records. Route membership remains navigation only.

### Timeline

Shows publication-year counts for the current visual subset. Volume over time is descriptive only and does not imply trend strength, causal direction or certainty.

## URL state

The map supports shareable state through:

- `view`;
- `domain`;
- `document_class`;
- `route`.

Evidence Explorer accepts the `domain`, `document_class` and B-NORM/C-STRUCT `route` intersection for safe drill-down. Corpus Explorer is used only when the requested filter exists canonically on its server-side API.

## Scientific boundary

The Evidence Map is not:

- a PRISMA diagram;
- a risk-of-bias visualization;
- a certainty map;
- a proof of evidence absence;
- an inclusion/exclusion decision surface.

Document count remains a navigation and descriptive quantity only.
