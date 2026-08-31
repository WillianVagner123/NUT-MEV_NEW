# NutEV Scientific Dashboard

The NutEV web home is a scientific overview, not the search form.

## Information architecture

```text
OVERVIEW
  Dashboard

EVIDENCE
  Search
  Corpus
  Evidence Explorer
  Evidence Radar

REVIEW
  Review Routes (B-NORM / C-STRUCT)

STRATEGY
  QA
  PRESS

VALIDATION
  Scientific validation

SYSTEM
  Search runs
  AI Context
```

Legacy operational pages remain available; the redesign is incremental and does not change scientific contracts to simplify UI.

## Dashboard data contract

The dashboard does not hardcode production counts. It reads only existing verified surfaces:

- `/api/health`;
- `/api/articles/status`;
- `/api/radar`;
- `/agent-context/article1/SEARCH_STATE.json`;
- `/agent-context/article1/ARTICLE_SUMMARIES.jsonl`;
- `/agent-context/article1/CONTEXT_MANIFEST.json`.

`ARTICLE_SUMMARIES.jsonl` is intentionally Tier-A-sized and rank-blind. The dashboard must never download the full Workbench corpus simply to render charts.

## Visualizations

The initial overview includes:

- bank/Tier A/routing KPI cards;
- scientific pipeline;
- operational evidence-processing funnel;
- full-text coverage donut;
- extraction-method bars;
- B-NORM/C-STRUCT route summary;
- document-type bars;
- operational-domain bars;
- publication timeline;
- provider operational state;
- formal-search readiness;
- provenance/context metadata.

Charts use semantic HTML/CSS and provide numeric labels. No chart is allowed to imply evidence quality from volume.

## Scientific guardrails

The UI must preserve these boundaries:

- discovery is not a formal systematic-review search;
- Bank tier/rank/score are operational priority, not quality or eligibility;
- route membership is not inclusion;
- full-text retrieval is not eligibility;
- machine review profile is not risk of bias, certainty or recommendation;
- provider gap is not absence of literature;
- PRESS draft is not query approval;
- the frontend cannot authorize GF-10, freeze a query, execute a formal search or emit a PRISMA event;
- evidence excerpts/result bundles remain machine/index artifacts until accepted through the appropriate human scientific workflow.

## Presentation mode

The dashboard includes a presentation view that collapses the sidebar and enlarges the analytical surface. It changes presentation only and never changes data or methodological state.

## Agent context lifecycle

The Hetzner container attempts to rebuild the verified Article 1 agent-context bundle before starting the web service. Failure to refresh the context does not block the web server: analytical pages show a partial/error state instead of using sample data.

The persistent context remains under:

```text
project_output_reference/agent_context/article1/
```

and is exposed through the existing safe static symlink under `/agent-context/article1/`.
