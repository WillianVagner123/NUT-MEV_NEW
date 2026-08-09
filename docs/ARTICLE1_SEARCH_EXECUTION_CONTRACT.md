# Article 1 search execution contract

Status: **normative for future definitive Article 1 executions**.

This document defines how NutEV Evidence Engine proves what was actually searched. It intentionally separates search tracks whose sampling logic is different instead of pretending that every source is one homogeneous database.

## Non-negotiable rule

> No query, navigation rule, provider, result count, or source may be described in the manuscript as executed unless it maps to execution evidence for the exact run.

Generated strategy space is not execution evidence.

## Track A — frozen indexed-database search

Use the immutable strategy registry and `nutev.search.strategy_executor` for provider expressions that are frozen before execution.

Current primary formal providers are PubMed, Europe PMC, Crossref and OpenAlex when present in the frozen strategy version.

Minimum provenance:

- strategy id and immutable version id;
- breadth (`specific`/other declared breadth);
- exact provider expression;
- provider query and provider-specific filter;
- provider limit/pagination rule;
- execution timestamp;
- execution status;
- rows returned;
- provider-reported total when available;
- append-only raw provider snapshot;
- SHA-256 of the raw snapshot;
- run manifest and manifest SHA-256;
- whether the frozen strategy is formal or pilot;
- PRISMA eligibility.

A pilot strategy is auditable but must not enter formal PRISMA identification counts unless it is explicitly promoted/frozen as a formal strategy under the protocol.

## Track B — official guideline / institutional source search

Official organizations, food guidelines, society documents and institutional sources are a distinct search track because their discovery logic is not equivalent to a bibliographic database query.

Minimum provenance:

- exact source/organization manifest used by the run;
- configuration provenance and `config_digest` that identify that manifest;
- workstream and provider attempt in `query_execution_ledger.json/.csv`;
- retrieval date/time;
- source URL and resolved URL where available;
- download/extraction status;
- failure reason where retrieval failed;
- downloaded artifact path where redistribution is legally permitted locally;
- SHA-256 in `artifact_manifest.csv` for locally retained artifacts;
- human inclusion/exclusion/coding state downstream.

The official-source track must be reported separately from indexed-database identification in the manuscript/PRISMA accounting when the identification mechanism differs.

## Track C — supplementary discovery providers

Optional providers such as DOAJ, ClinicalTrials.gov, SciELO connector, Semantic Scholar, arXiv, Google PSE, SerpAPI or Brave may be used only according to the protocol version for the run.

For the generic pipeline, every actual attempt must be present in `provider_performance.csv` and the finalized `query_execution_ledger.json/.csv`. Missing credentials are recorded as `skipped`; provider errors remain visible rather than being converted into evidence absence.

A supplementary provider does not automatically become part of the definitive Article 1 search merely because the software can execute it. Its methodological role must be declared in the protocol before manuscript use.

### SciELO naming constraint

The current SciELO connector is prefix-scoped through Crossref (`10.1590`) rather than a comprehensive native SciELO platform free-text search. Outputs from this connector must therefore be described as **SciELO-prefix/Crossref retrieval** (or equivalent precise wording), not as a comprehensive search of the entire SciELO platform.

## Generated versus executed query artifacts

The canonical semantics are:

- `querypack_generated.json/.csv`: generated workstream query space before execution constraints;
- `provider_querypack_generated.json/.csv`: provider-rendered generated query space before execution constraints;
- `query_execution_ledger.json/.csv`: canonical attempt-level evidence from `provider_performance.csv`;
- `querypack_executed.json/.csv`: compatibility view containing only expressions with a real execution-attempt row;
- `provider_querypack_executed.json/.csv`: provider-specific compatibility view containing only expressions with a real execution-attempt row.

The two `*_generated` families may contain expressions removed by query budgets, routing, or provider availability. They must never be used as proof of execution.

## Scientific readiness contract

`run_status` / `execution_status` answer only whether the computational run completed, partially completed or failed.

`scientific_readiness` is separate:

- `blocked`: a detectable computational/scientific prerequisite failed;
- `computationally_ready_for_human_review`: computational gates detected by the software are satisfied, but human screening/adjudication/manuscript gates are not asserted;
- `manuscript_ready`: reserved for runs carrying explicit `human_review_complete=true` and `manuscript_gates_complete=true`, with no blocking computational condition.

The software must never infer human scientific approval from provider success or a completed pipeline.

## Definitive Article 1 freeze checklist

Before a run is cited as the definitive computational execution for Article 1, record and preserve:

1. software version, Git tag and exact commit SHA;
2. protocol/search-strategy version;
3. `config_digest` and per-config hashes;
4. retrieval date(s);
5. every declared provider/search track and its role;
6. every actual query/navigation attempt;
7. provider limits, pagination/truncation rules and provider-reported totals when available;
8. raw snapshots + SHA-256 for frozen indexed-database executions;
9. official-source manifest provenance plus downloaded-artifact hashes where applicable;
10. deduplication state and counts;
11. full-text/recoverability state;
12. coverage-loss events and unresolved failures;
13. human screening/adjudication state;
14. final PRISMA counts and manuscript-facing export identifiers.

If any required evidence is missing, the run may remain useful for development or pilot analysis, but it must not be described as the definitive manuscript execution.