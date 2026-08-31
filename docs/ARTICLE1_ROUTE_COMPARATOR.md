# Article 1 Route Comparator

The Route Comparator is a read-only analytical view over the rank-blind Article 1 context. It compares B-NORM and C-STRUCT without converting routing into scientific inclusion.

## Data source

`/agent-context/article1/ARTICLE_SUMMARIES.jsonl`

The comparator derives all counts at runtime and never uses Bank rank, score, machine relevance, quality, RoB or certainty fields.

## Metrics

It describes B-NORM, C-STRUCT, overlap, exclusive routing, unrouted records, document-class distributions, full-text retrieval state, provider distribution, publication year and operational domains.

`Exclusive B-NORM` and `Exclusive C-STRUCT` mean only exclusive route membership. They do not mean inclusion/exclusion.

## Drill-down

Route and domain links open the Evidence Explorer with the matching rank-blind navigation filters.

## Boundary

The comparator must not infer that one route is scientifically stronger from having more records. Full-text availability, publication volume and route membership remain operational/descriptive quantities only.
