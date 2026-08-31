# NutEV Scientific Dashboard

The NutEV web home is a scientific overview, not the search form.

## Information architecture

```text
OVERVIEW
  Dashboard

EVIDENCE
  Search
  Corpus
  Evidence Map
  Evidence Explorer
  Evidence Radar

REVIEW
  Review Control Center
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

The dashboard does not hardcode production counts. It reads only verified server-side aggregates:

- `/api/health`;
- `/api/articles/status`;
- `/api/radar`;
- `/api/dashboard/overview`;
- `/api/timeline`.

`/api/dashboard/overview` and `/api/timeline` aggregate the verified `agent_context/article1` bundle
inside the server (`apps/nutev-web/article1_context_index.py`), after checking the
`ARTICLE_SUMMARIES.jsonl` SHA-256 against `CONTEXT_MANIFEST.json`. The browser therefore receives
counts, never the corpus, and never the full Workbench.

`press_status` is treated as PASS only when the recorded value *is* `PASS`. The live master records
`NOT_YET_RECORDED_AS_PASS`; a substring match would render that as a passed gate.

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

Every chart segment, KPI and funnel stage is a link: it answers "which documents form this number?"
by navigating to the Corpus Explorer, the Evidence Map or the Review Control Center with the current
filters applied. Filters live in the URL (`?route=B-NORM&domain=social_context&year_from=2020`), so a
view can be copied and sent to another researcher.

## Evidence Map

`/evidence-map.html` renders an operational-domain x document-class matrix as a real HTML table with
a sticky header and row axis, backed by `/api/evidence-map`. Clicking a cell opens the exact document
list through `/api/evidence-map/cell` and links onward into the Corpus Explorer.

Heatmap intensity encodes a document count and nothing else — never quality, certainty, effect
magnitude or evidence strength. Documents with no detected operational domain get their own explicit
row instead of being dropped. Row totals are distinct documents in a domain and column totals are
distinct documents in a class; because a document can carry several domains, the sum of the cells is
reported separately as `cell_assignments` and never as a document total.

On narrow viewports the matrix is replaced by a domain -> classes list rather than a squeezed grid.

## Review Control Center

`/review.html` is the operating surface for human reading. It separates machine state from human
review state and never presents a machine signal as a decision: the queue exposes no Bank
rank/score/tier and no machine relevance band.

Human states are `NOT_STARTED`, `IN_REVIEW`, `REVIEWED`, `CONFLICT`, `ADJUDICATION_REQUIRED` and
`RESOLVED`. `REVIEWED` means a human has read the document; it is not inclusion. Events are appended
to `project_output_reference/scientific/human_review/article1/human_review_events.sqlite` through
`POST /api/review/event`, which is loopback-only and rejects eligibility, screening and PRISMA
vocabulary in `status`, `decision` and `reason_code`.

The log is append-only: corrections are new events carrying `supersedes`, and the superseded event
stays readable.

## Article dossier v2

The Corpus Explorer detail panel is a tabbed dossier: Overview, Methods, Evidence, Domains,
Recommendations, Provenance and Human review. Fields the pipeline does not extract render as
"Not extracted" rather than being invented. Machine excerpts stay labelled *candidate evidence
excerpt*, extracted recommendation-like text is kept separate from any accepted NutEV
recommendation (there are none), and Bank/machine signals live in the Provenance tab, apart from the
human review trail.

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
