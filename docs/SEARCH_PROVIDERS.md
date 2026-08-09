# NutEV search providers

`src/nutev` is the canonical NutEV Evidence Engine runtime. The historical `src/local_deep_research` runtime is **not present in the current source tree**; its attribution/provenance is retained in `NOTICE.md`, `LICENSE`, and Git history.

For the Article 1 manuscript contract, also read `docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md`.

## Provider roles are methodological, not merely technical

A provider being implemented does not automatically make it part of a definitive Article 1 search. The protocol/search-strategy version must declare its role. Distinguish:

1. **frozen indexed-database track** — immutable strategy versions executed through the strategy executor where supported;
2. **official guideline/institutional track** — organizations, food guidelines, society documents and official sources;
3. **supplementary discovery track** — optional providers used only when declared by the protocol.

Different tracks may remain separate, but no source/query may be described as executed without run-level evidence.

## PubMed / NCBI

PubMed is executed through NCBI E-utilities with `esearch.fcgi` and `esummary.fcgi`. The canonical client uses `usehistory=y`, `WebEnv`, `query_key`, paginated `retstart`/`retmax` batches, retry/backoff for transient errors, and per-query checkpoints in `07_logs/checkpoints/pubmed/`.

Recommended variables:

- `NCBI_EMAIL`: recommended by NCBI. If absent, NutEV warns and uses conservative rate limiting.
- `ENTREZ_EMAIL`: fallback accepted by NutEV.
- `NCBI_API_KEY`: optional; increases allowed NCBI rate.
- `NCBI_TOOL`: defaults to `nutev_pipeline`.

Without an API key, NutEV uses conservative request pacing; with a key, a shorter interval is permitted by the client configuration.

## Europe PMC, OpenAlex and Crossref

These scientific providers are independent of Google. Each provider has timeout/retry protection and failures are converted into provider failure events instead of crashing the whole pipeline. Use `OPENALEX_MAILTO` and `CROSSREF_MAILTO` where possible.

## DOAJ

DOAJ uses the public DOAJ REST API and requires no API key. It is implemented in the orchestrator but is not automatically part of every definitive run. Enable it only through the relevant workstream/protocol configuration. Rows are normalized to the shared schema and can carry open-access state.

## ClinicalTrials.gov

ClinicalTrials.gov uses the v2 REST API. It provides registry evidence distinct from journal articles. Rows carry the NCT identifier where available and are normalized to the shared provider schema. It is optional unless the protocol explicitly includes it.

## SciELO connector

The current SciELO connector is **not a comprehensive native SciELO platform free-text search**. It retrieves SciELO-associated content through Crossref restricted to DOI prefix `10.1590`.

Therefore manuscript wording must describe this precisely (for example, `SciELO-prefix/Crossref retrieval`) and must not claim comprehensive SciELO platform coverage unless a future implementation and execution record support that claim.

## Semantic Scholar and arXiv

Both are optional supplementary providers:

- **Semantic Scholar** — public Graph API, with an optional `S2_API_KEY` for higher rate limits;
- **arXiv** — public export API using Atom XML and no API key.

Their presence in the runtime is capability, not proof they were included in a scientific run.

## Official sources

Official organization/guideline discovery is a separate methodological track. The executed run should preserve:

- source/organization manifest state;
- `config_digest` and config provenance;
- provider attempt in the query execution ledger;
- URL/resolved URL where available;
- retrieval/download/extraction state;
- failure reason when applicable;
- artifact SHA-256 for locally retained downloaded documents.

When identification logic differs from bibliographic databases, official-source identification should remain distinguishable in methods/PRISMA reporting.

## Optional web / gray-literature providers

Google Programmable Search Engine, SerpAPI and Brave are optional. Missing credentials produce an explicit `skipped` provider result rather than silently pretending that the provider was searched.

A quota/configuration failure for an optional provider does not erase results from other providers, but it remains visible in the execution/failure logs and can block scientific readiness when that provider was declared as required by the protocol.

## Checkpoint / resume

Provider checkpoints are written under `07_logs/checkpoints/<provider>/`. Checkpoint use is recorded at the provider-attempt level. `resume_used` must mean that a checkpoint was actually consumed; enabling resume capability alone is not scientific evidence that resume occurred.

## Generated versus executed query evidence

The canonical semantics are:

- `querypack_generated.json/.csv`: generated workstream query space before execution constraints;
- `provider_querypack_generated.json/.csv`: provider-rendered generated query space before execution constraints;
- `provider_performance.csv`: terminal record produced for each actual provider call;
- `query_execution_ledger.json/.csv`: canonical current-run attempt ledger derived from provider performance records;
- `querypack_executed.json/.csv`: compatibility view containing only expressions with a real attempt record;
- `provider_querypack_executed.json/.csv`: provider-specific compatibility view containing only expressions with a real attempt record.

Query budgets, routing and provider availability can make the generated set larger than the executed set. Generated artifacts must never be used as proof that a query was submitted.

## Logs

Important provider observability files under `07_logs` include:

- `run_events.jsonl`: provider lifecycle events;
- `provider_failures.csv`: recoverable provider failures and skip reasons;
- `provider_performance.csv`: provider attempts, status, query hash, query, counts and timing;
- `query_execution_ledger.json/.csv`: canonical attempt-level query evidence for the current/latest run;
- `config_provenance.json`: configuration inputs/hashes and overall `config_digest`;
- `artifact_manifest.csv`: locally retained artifact hashes where applicable;
- `run_summary.json`: computational status plus a separate `scientific_readiness` state.

Provider performance fields include `run_id`, `provider`, `workstream`, `query_hash`, `query`, `status`, `total_found`, `rows_returned`, `duration_seconds`, `resume_used`, and `checkpoint_path`.

## Frozen strategy executor

For immutable indexed-database searches, the strategy registry/executor additionally stores exact frozen provider expressions, provider filters, raw result snapshots, snapshot SHA-256 values, run manifests and manifest SHA-256 values. This is the preferred manuscript-grade provenance layer for the providers covered by a frozen formal strategy.

A completed provider execution remains distinct from scientific approval. See `scientific_readiness` and the Article 1 execution contract before treating any run as definitive.