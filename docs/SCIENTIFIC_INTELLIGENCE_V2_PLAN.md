# NutEV Scientific Intelligence Workspace v2 — audit and plan

Status: **Phase 0–2 delivered** (audit, architecture, data contracts) and **Phase 3–5 implemented**
(Evidence Map, dashboard drill-down, Review Control Center, Scientific Dossier v2).
Phase 6–8 (Strategy Lab, Quality Observatory, Presentation Mode v2, Snapshots, Export, Ask NutEV)
are **not** implemented and are specified here only as the next increments.

This document is an evolution plan for the existing system. It is not a rewrite proposal and it does
not create a second source of scientific truth. `AI_CONTEXT.md`, `ARTICLE1_SEARCH_MASTER.md` and
`config/nutev/article1_search_master_v1.json` remain canonical.

---

## 1. Current architecture

```text
tools/*.py  ──▶  project_output_reference/           ──▶  apps/nutev-web/server.py  ──▶  static pages
(pipeline)       scientific/workbench/*.sqlite            (stdlib http.server)          (vanilla ES modules)
                 scientific/deepening/<search>/
                 scientific/review_queue/<search>/
                 scientific/review_routes/<search>/
                 agent_context/article1/*
```

**Backend.** `apps/nutev-web/server.py` is a `ThreadingHTTPServer` subclass of
`SimpleHTTPRequestHandler`. API paths are matched literally in `do_GET`/`do_POST`; everything else
falls through to `translate_path`, which serves `apps/nutev-web/` (and `apps/nutev-validation/`
under `/validation`). Coordinator-grade mutations are gated by `_require_loopback()`.

**Data access.** `article_workbench_data.py` opens the Workbench SQLite **read-only**
(`mode=ro`), after verifying `WORKBENCH_MANIFEST.json` (`status == PASS`) and the recorded
SHA-256 of the database file. Paging is server-side and cursor-based, capped at 100 rows.
`radar_data.py` does the equivalent for the Radar state.

**Rank-blind bundle.** `src/nutev/science/article1_agent_context.py` materializes
`agent_context/article1/{CONTEXT_MANIFEST.json, SEARCH_STATE.json, SEARCH_SUMMARY.md,
ARTICLE_SUMMARIES.jsonl}`. `ARTICLE_SUMMARIES.jsonl` covers the Tier A deepened set and carries
`routes`, `review_profile.primary_document_class`, `review_profile.operational_domains`
(+ the matched terms), `year`, `source_provider`, `full_text_status` and excerpt/bundle counts.
The builder refuses to emit `reference_rank`, `reference_score`, `reference_tier`,
`machine_relevance_score` or `machine_relevance_band`. The Docker image symlinks
`apps/nutev-web/agent-context/article1` at the canonical bundle, which is how the browser reads it.

**Frontend.** One static page per workspace (`index.html`, `search.html`, `articles.html`,
`evidence.html`, `radar.html`, `review-routes.html`, `review-qa.html`, `press-review.html`,
`ai-context.html`) plus the validation app. Shared tokens live in `styles.css`; the v1 dashboard
language lives in `dashboard.css`.

## 2. Existing reusable components

| Asset | Reused as |
| --- | --- |
| `article_workbench_data.load_article_page/_detail` | corpus paging + dossier payload (extended, not replaced) |
| verified-SHA + `mode=ro` loading pattern | copied verbatim into the new context index |
| `agent_context/article1/*` bundle | the only input for Evidence Map / drill-down aggregates |
| `dashboard.css` tokens, `.card`, `.kpi-grid`, `.mini-pill`, `.status-pill` | Evidence Map, Review Control Center, Dossier v2 |
| `_require_loopback()` | write-path gate for human review events |
| `radar_data.load_radar_state` | provider operations panel (unchanged) |

## 3. Existing endpoints (pre-upgrade)

`GET` `/api/health`, `/api/providers`, `/api/radar`, `/api/articles/status`, `/api/articles`,
`/api/articles/{document_id}`, `/api/searches`, `/api/searches/{id}`, `/api/search/jobs/{id}`,
`/api/validation/{readiness,round,adjudication,gold,metrics,decision,reviewer}`.
`POST` `/api/query/compile`, `/api/search`, `/api/search/jobs`, and the validation write paths.

Nothing in that set aggregates the corpus by domain × document class, exposes route membership as a
filter, or records a human review state for an Article 1 document. Those three gaps are what this
upgrade closes.

## 4. Existing scientific states

- **Master status** — `DISCOVERY_CLOSED_FORMAL_SEARCH_PENDING_PRESS_FREEZE`.
- **Formal-search gate** — `press_status`, `gf10_authorized`, `query_freeze_complete`,
  `formal_provider_search_executed`, `prisma_search_event_emitted`. All read-only for the web tier.
- **Machine states** — Bank tier/rank/score, `machine_relevance_band`, route membership,
  `full_text_status`, extraction method, review profile v2.
- **Human states** — previously only inside the validation app (assessor decisions, adjudication,
  decision lock), with nothing for Article 1 reading queues. That is the new `review_event` log.

## 5. UX problems found

1. Every dashboard chart was a dead end: no chart answered "which documents are these?".
2. Domain × document-class structure existed only implicitly; a researcher had to read
   `evidence.html` and `review-routes.html` and mentally intersect them.
3. Dashboard, Evidence Explorer and Review Routes each re-downloaded `ARTICLE_SUMMARIES.jsonl` and
   re-aggregated it in the browser — three client-side implementations of the same counts.
4. Filters were page-local and invisible in the URL, so a view could not be shared.
5. The article dossier mixed machine profile, provenance and evidence in one scroll, with the
   machine relevance band rendered next to the title as if it were a verdict.
6. There was no human review state at all for Article 1 — progress was untracked.

## 6. Missing data contracts

- domain × document-class aggregate with route/full-text distribution per cell;
- filtered document list for one cell;
- per-series timeline;
- route comparison (exclusive/overlap/unrouted);
- human review event log and the derived per-document / per-route status;
- one dashboard aggregate so the browser stops recomputing corpus statistics.

## 7. Proposed pages

| Page | Status | Purpose |
| --- | --- | --- |
| `/evidence-map.html` | **implemented** | domain × document-class matrix, filters, drill-down to Corpus |
| `/review.html` | **implemented** | Review Control Center: KPIs, per-route progress, queue, conflicts |
| `/articles.html` | **upgraded** | Dossier v2 tabs + URL-driven filters (`domain`, `route`, `year_from`…) |
| `/` | **upgraded** | drill-down on every chart, global filter bar, URL state |
| `/routes-compare.html` | deferred (P1) | B-NORM × C-STRUCT comparator — `/api/routes/compare` already ships |
| `/quality.html` | deferred (P1) | System & Corpus Quality observatory |
| Strategy Lab, Presentation v2, Snapshots, Export, Ask NutEV | deferred (P1/P2) | see §10 |

## 8. Proposed endpoints

Implemented in this increment (all read-only except the last):

| Endpoint | Contract |
| --- | --- |
| `GET /api/dashboard/overview` | KPIs, class/domain/full-text/route/timeline aggregates, provenance |
| `GET /api/evidence-map` | matrix cells with counts, route distribution, full-text coverage |
| `GET /api/evidence-map/cell` | paged documents for one `domain` × `document_class` cell |
| `GET /api/timeline` | per-year counts for up to 6 named series |
| `GET /api/routes/compare` | B-NORM / C-STRUCT / overlap / exclusive / unrouted breakdowns |
| `GET /api/review/status` | review KPIs by route, document class and reviewer |
| `GET /api/review/queue` | paged review queue, rank-blind, with human status |
| `GET /api/review/document/{id}` | full human event history for one document |
| `POST /api/review/event` | append one human review event (loopback-only) |

`GET /api/articles` gains `domain`, `route`, `year_from`, `year_to` and `review_status`. These are
resolved server-side to a document-id restriction from the verified bundle and the review log, so
the Corpus Explorer keeps its cursor paging and its 100-row cap.

Deferred, and deliberately **not** stubbed: `/api/quality`, `/api/strategy/versions`,
`/api/snapshots`.

## 9. Proposed persistence changes

One new store, `project_output_reference/scientific/human_review/article1/human_review_events.sqlite`,
written by `apps/nutev-web/human_review_store.py`:

```text
review_event(review_id PK, document_id, reviewer_id, route, stage, status, decision,
             reason_code, reason_text, created_at, updated_at, supersedes, provenance_json)
```

Rules enforced in code and in tests:

- **append-only** — the module issues no `UPDATE` and no `DELETE`; a correction is a new event whose
  `supersedes` points at the event it replaces, and the superseded row stays readable;
- the Workbench SQLite is never written to — it stays `mode=ro` and SHA-verified;
- `status` is restricted to `NOT_STARTED | IN_REVIEW | REVIEWED | CONFLICT |
  ADJUDICATION_REQUIRED | RESOLVED`;
- `decision` is restricted to operational reading outcomes
  (`READ`, `NEEDS_FULL_TEXT`, `NEEDS_SECOND_REVIEWER`, `OPERATIONAL_SIGNAL_CONFIRMED`,
  `NO_OPERATIONAL_SIGNAL`, `DEFER`);
- eligibility/PRISMA vocabulary (`INCLUDE`, `EXCLUDE`, `ELIGIBLE`, `SCREENED_IN`, `PRISMA_*`, …) is
  rejected with HTTP 400 in any of `status`, `decision` or `reason_code`.

## 10. Migration plan

| Phase | Content | State |
| --- | --- | --- |
| 0 | audit | this document |
| 1 | architecture | §1–§9 |
| 2 | data contracts | `article1_context_index.py`, `human_review_store.py` |
| 3 | Evidence Map + drill-down | done |
| 4 | Review Control Center | done |
| 5 | Scientific Dossier v2 | done |
| 6 | Strategy Lab + Quality Observatory | next |
| 7 | Presentation Mode v2 + Snapshots + Export | after 6 |
| 8 | Ask NutEV | last, and only over the contracts above |

Phase 6 needs a versioned query-draft history that does not exist yet
(`config/nutev/article1_query_draft_v1.json` holds one version, not a lineage); building the Strategy
Lab before that history exists would mean inventing it, so it is deliberately not started.

## 11. Risks

| Risk | Mitigation |
| --- | --- |
| Aggregates read as scientific findings | every payload carries a `guardrail` string, rendered in the UI |
| Evidence Map mistaken for full-corpus coverage | every response states its universe: the Tier A profiled set, not the ~33k Bank |
| Client-side aggregation creeping back | dashboard/map/review read aggregate endpoints; tests forbid corpus-wide client aggregation |
| Human review confused with screening | separate store, restricted vocabulary, rejected eligibility terms, tests |
| Stale bundle presented as live | `context_stale`/`not_ready` states surfaced instead of empty charts |
| Bundle drift vs. manifest | SHA-256 of `ARTICLE_SUMMARIES.jsonl` verified against `CONTEXT_MANIFEST.json` on every load |
| Review write path abuse | `POST /api/review/event` is loopback-only; a remote reviewer flow needs the private-link model the validation app already has, and is out of scope here |

## 12. Scientific guardrails

Preserved, and asserted by tests:

```text
DISCOVERY != FORMAL SEARCH          BANK PRESENCE != SCIENTIFIC INCLUSION
TIER != QUALITY                     RANK != QUALITY
MACHINE RELEVANCE != ELIGIBILITY    ROUTE != INCLUSION
FULL TEXT RETRIEVAL != ELIGIBILITY  EVIDENCE EXCERPT != ACCEPTED EVIDENCE CLAIM
PROFILE != RISK OF BIAS             DOCUMENT COUNT != EVIDENCE STRENGTH
PROVIDER GAP != ABSENCE OF LITERATURE
PRESS DRAFT != APPROVED QUERY       REVIEWED != INCLUDED
```

The web tier cannot approve PRESS, authorize GF-10, freeze a query, execute a formal search or emit
a PRISMA event. No endpoint added here writes to `config/nutev/article1_search_master_v1.json`, and
heatmap intensity encodes document count only — never quality, certainty or effect magnitude.

## 13. Acceptance criteria

1. Dashboard → Evidence Map → `Social context × Clinical practice guideline` → the exact document
   list → one dossier → human review state → back to the macro view with progress updated.
2. Every dashboard chart segment navigates to the documents behind its number.
3. Filters survive in the URL and can be pasted to another researcher.
4. No production count is a literal anywhere in `apps/nutev-web/*.js`.
5. The corpus stays server-paged; no page downloads the ~33k Bank.
6. Review status never renders as inclusion, and eligibility vocabulary is rejected server-side.
7. Machine profile and human decision are visually and structurally separate in the dossier.
8. Empty / partial / stale / error states are distinguishable from "no literature exists".
9. `python -m pytest nutev_tests` is green on 3.12 and 3.13.
