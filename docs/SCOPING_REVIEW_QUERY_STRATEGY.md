# NutEV — Scoping Review Query Strategy

Status: **CANONICAL FOR WEB REVIEW SEARCH**

## Purpose

This document defines how NutEV turns an approved scoping/systematic-review concept strategy into provider-specific search queries while preserving auditability.

The web interface supports `PCC`, `PICO`, and `PECO` frameworks. The framework is organizational metadata; retrieval is driven by explicit concept blocks and terms.

## Scientific rule

**NutEV must not silently invent controlled vocabulary.**

A review-grade strategy must distinguish:

- `free:` — free-text term/synonym;
- `mesh:` — explicitly approved MeSH descriptor;
- `decs:` — explicitly approved DeCS descriptor.

A line without a prefix is treated as `free:`.

Terms inside the same concept block are combined with `OR`. Non-empty concept blocks are combined with `AND`.

Example:

```text
Population
free:adult*
mesh:Adult

Concept
free:lifestyle medicine
decs:Medicina do Estilo de Vida

Context
free:nutrition
mesh:Diet
```

## Provider compilation

### PubMed

- `mesh:` -> `"Term"[Mesh]`
- `free:` -> `"Term"[Title/Abstract]` (single-token truncation is preserved)
- `decs:` -> free-text Title/Abstract projection; DeCS semantics are not fabricated in PubMed

Dialect ID: `pubmed_mesh_title_abstract`.

### Europe PMC

- `mesh:` -> `MESH:"Term"`
- `free:` / `decs:` -> `TITLE_ABS:"Term"`

Dialect ID: `europepmc_mesh_title_abstract`.

### LILACS / BVS

- `decs:` and `mesh:` -> `mh:"Term"`
- `free:` -> `tw:"Term"`

Dialect ID: `bvs_decs_mesh_tw`.

### SciELO / DOAJ

Terms are projected into an explicit Boolean free-text query. Controlled-vocabulary labels remain visible as text, but NutEV does not claim that the provider executed MeSH/DeCS semantics.

### OpenAlex / Crossref / Semantic Scholar

Terms are projected into a provider-safe Boolean free-text representation. NutEV records the dialect as `generic_boolean_free_text`; this is not represented as controlled-vocabulary execution.

## Preview gate

The user can request `Visualizar estratégia por base` before retrieval.

Canonical endpoint:

```text
POST /api/query/compile
```

The response includes:

- original review question;
- framework;
- normalized concept blocks;
- exact query for every selected provider;
- dialect identifier;
- number of explicit controlled-vocabulary terms;
- warnings.

The server recompiles the strategy when the search starts. The browser preview is not trusted as the scientific source of truth.

## Execution

Structured strategies are executed through the progressive job endpoint:

```text
POST /api/search/jobs
```

The search request contains the human-readable review question plus the structured strategy. The backend compiles provider queries and passes the exact provider query to each connector.

`Busca global` can be combined with structured review mode. In that case:

- all connected providers are selected;
- no NutEV internal result ceiling is applied;
- provider-imposed limits remain visible as coverage gaps;
- the provider-specific strategy remains unchanged.

## Audit trail

Every structured run persists:

```text
query
query_plan
query_plan.provider_queries.<provider>.query
query_plan.provider_queries.<provider>.dialect
providers[].provider_query
providers[].query_dialect
results[].provider_query
search_mode
```

The exact strategy therefore remains inspectable in `result.json` under the persisted web search run.

Structured modes are:

```text
structured_review_bounded
structured_review_global_exhaustive
```

## Guardrails

The system must fail closed when:

- the framework is unsupported;
- a term type is unsupported;
- there are no usable concept terms;
- a compiled provider query exceeds the implementation safety limit;
- no provider is selected.

The system must not:

- fabricate MeSH/DeCS descriptors;
- silently convert a guessed synonym into controlled vocabulary;
- claim that a provider executed MeSH/DeCS when it received free text;
- rewrite an approved concept strategy after the search begins;
- hide provider-specific queries from the persisted audit record.

## PRISMA / review reporting boundary

This component creates and executes auditable search strategies. It does not itself complete PRISMA/PRISMA-ScR reporting, study eligibility screening, risk-of-bias assessment, or final evidence synthesis.

Search dates, provider status, exact query, returned counts, deduplication outputs and coverage gaps should be preserved for downstream review reporting.
