# NutEV Article Workbench

## Purpose

The Workbench is the operational library for large NutEV corpora. It is designed for tens of thousands of articles without loading the corpus into the browser.

It consumes the low-token outputs from `science-excerpts`:

```text
EvidenceExcerpt
ResultBundle
ArticleEvidenceCard
        ↓
science-workbench-index
        ↓
evidence_workbench.sqlite
        ↓
read-only paged API
        ↓
/articles.html
```

## Build

```bash
nutev science-workbench-index
```

Default inputs:

```text
project_output_reference/scientific/excerpts/evidence_excerpts.jsonl
project_output_reference/scientific/excerpts/result_bundles.jsonl
project_output_reference/scientific/excerpts/article_evidence_cards.jsonl
project_output_reference/scientific/excerpts/EXCERPT_MANIFEST.json
```

Default output:

```text
project_output_reference/scientific/workbench/evidence_workbench.sqlite
project_output_reference/scientific/workbench/WORKBENCH_MANIFEST.json
```

The index is derived only after the `EXCERPT_MANIFEST` and all three source hashes are verified.

## Scale contract

The browser never receives the whole corpus.

```text
80,000+ article cards
      ↓
SQLite index on server
      ↓
server-side query / filters
      ↓
50 cards by default
      ↓
browser
      ↓
click one card
      ↓
load only that article detail
```

API page size is hard-capped at 100.

The first implementation supports server-side filtering by:

- free-text search over compact article identity/reference/study snapshot;
- provider;
- document class;
- full-text status.

Pagination uses an opaque keyset cursor based on year + document ID. It does not use client-side slicing of the full corpus.

## SQLite projection

`article_cards`

- document ID;
- record ID;
- title;
- year;
- DOI;
- PMID;
- provider;
- document class;
- full-text status;
- cache key;
- reference stub;
- compact LLM context size;
- searchable compact text;
- complete ArticleEvidenceCard JSON.

`evidence_excerpts`

- excerpt ID;
- document ID;
- kind;
- section;
- locator;
- priority;
- short verbatim source excerpt;
- complete excerpt JSON.

`result_bundles`

- result ID;
- document ID;
- main/secondary kind;
- priority;
- complete ResultBundle JSON.

## Read-only web API

### `GET /api/articles/status`

Returns whether a hash-verified Workbench index exists and its counts.

### `GET /api/articles`

Parameters:

- `q`;
- `limit` (1-100, default 50);
- `cursor`;
- `source_provider`;
- `document_class`;
- `full_text_status`.

List responses intentionally omit full ArticleEvidenceCard JSON, excerpts, bundles, and full text. They contain only fields needed to render the current page.

### `GET /api/articles/{document_id}`

Loads on demand:

- one ArticleEvidenceCard;
- its selected EvidenceExcerpts;
- its ResultBundles.

The endpoint explicitly returns `full_text_in_response=false`.

The API opens SQLite in read-only mode and verifies the database against `WORKBENCH_MANIFEST.json`. The verification result is cached only while file size, mtime, and expected hash remain unchanged.

There are no Article Workbench POST endpoints in this contract.

## UI

`/articles.html` presents:

- search box;
- provider filter;
- study/document-class filter;
- full-text filter;
- server-reported article count;
- a paged article list;
- `Carregar mais 50` cursor pagination;
- sticky article dossier on desktop;
- one-column layout on smaller screens.

Selecting an article opens the dossier in the same view. It displays:

1. identity/reference;
2. compact study snapshot;
3. principal/secondary ResultBundles, including effect estimates/CI/p-values when available;
4. short source-linked excerpts for objective, methods, conclusion and limitations;
5. provenance/cache/token policy.

## Quotes / source excerpts

Displayed quotes are short source-linked machine candidates retained by `science-excerpts`.

The Workbench must show section/locator and reference identifiers where available. It must not reconstruct or display the entire copyrighted article body through this API.

## Token policy

Opening/browsing the Workbench costs no external LLM tokens.

The UI uses precomputed compact cards. A future synthesis action should query selected ArticleEvidenceCards and feed only their curated `llm_context` into a model by default.

The Workbench therefore separates:

```text
expensive source acquisition once
        ↓
deterministic extraction/cache
        ↓
compact reusable article object
        ↓
cheap repeated browsing / filtering / synthesis context
```

## Guardrails

Workbench status, filters, ResultBundles, EvidenceExcerpts and machine classifications are operational/scientific-reading aids.

They are not automatically:

- eligibility decisions;
- EvidenceClaims;
- risk-of-bias judgments;
- certainty assessments;
- causal conclusions;
- recommendations;
- PRISMA events.

Human validation and formal review remain explicit downstream workflows when required.
