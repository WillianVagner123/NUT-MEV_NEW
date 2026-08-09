# Reproducibility

NutEV Evidence Engine is designed so that a person with no API keys and no protected data can reproduce a demonstration of the pipeline shape, while scientific runs remain traceable to code, configuration, execution evidence and human-review decisions.

## Zero-key demonstration

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
python -m pip install -e ".[dashboard]"
nutev demo-data --project-root ./project_output_demo
nutev dashboard --project-root ./project_output_demo
```

This runs without OpenAI, Google, SerpAPI, Brave, real data or protected PDFs. It produces synthetic metadata, scored tables and reports under `project_output_demo/`. These artifacts are demonstration data, **not scientific evidence**.

## What makes a scientific run reproducible

- **Versioned software:** identify software version, Git tag and exact commit SHA.
- **Declared Python support:** the package declares Python `>=3.12,<3.14`, matching canonical CI on Python 3.12 and 3.13.
- **Dependency evidence:** project files define supported ranges/minima; release validation records the exact resolved validation environment via `pip freeze`. The range files are not an immutable lock by themselves.
- **Deterministic configuration provenance:** methodology/config inputs under `config/` are versioned and methodology changes are recorded in `docs/CHANGELOG_METODOLOGICO.md`.
- **Config digest:** scientific runs record effective configuration inputs and `config_digest`.
- **Generated-versus-executed search provenance:** generated query space is preserved separately from expressions actually attempted.
- **Attempt ledger:** `07_logs/query_execution_ledger.json/.csv` is the canonical generic-pipeline evidence that a provider expression was actually attempted.
- **Frozen formal search provenance:** strategy-registry executions preserve exact expressions, raw snapshots, snapshot SHA-256 values and a run-manifest SHA-256.
- **Artifact hashes:** downloaded/local artifacts retained by the run are represented in `artifact_manifest.csv` with SHA-256 where applicable.
- **Failure visibility:** provider failures, extraction failures and coverage-loss events remain explicit instead of being silently converted into evidence absence.
- **Human decisions remain explicit:** no automatic output is equivalent to final scientific or clinical approval.

## Generated queries are not executed queries

The canonical artifact semantics are:

- `querypack_generated.json/.csv`: generated workstream query space before execution constraints;
- `provider_querypack_generated.json/.csv`: provider-rendered generated query space before execution constraints;
- `provider_performance.csv`: terminal record for each actual provider call;
- `query_execution_ledger.json/.csv`: current/latest-run attempt-level execution evidence;
- `querypack_executed.json/.csv`: compatibility view finalized only from actual attempts;
- `provider_querypack_executed.json/.csv`: provider-specific compatibility view finalized only from actual attempts.

Query budgets, provider routing, availability and credentials can make the generated set larger than the executed set. Manuscript methods must use execution evidence, never the generated query space alone.

## Scientific readiness is separate from execution

`run_status` / `execution_status` describe computational completion. The run summary also exposes a separate `scientific_readiness` state:

- `blocked`: a detectable prerequisite failed;
- `computationally_ready_for_human_review`: computational gates detected by the software passed, but human approval is not inferred;
- `manuscript_ready`: reserved for a run with explicit `human_review_complete=true` and `manuscript_gates_complete=true`, with no detected blocker.

A completed pipeline therefore cannot become manuscript-ready automatically.

## Article 1 search tracks

The definitive Article 1 execution follows `docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md` and distinguishes at least:

1. frozen indexed-database execution;
2. official guideline/institutional source execution;
3. supplementary discovery providers when explicitly included by protocol.

Different tracks may use different retrieval mechanisms, but each must preserve evidence of what was actually executed. A provider being implemented is not equivalent to it being included in the definitive search.

## Config provenance (`config_digest`)

Taxonomy and scoring configs are assembled by deterministic merge rules under `config/`. A scientific run records, as applicable:

- source config paths;
- per-file SHA-256 values;
- merged config digests;
- one overall `config_digest`;
- software version and commit SHA.

The digest is provenance only; recording it must not alter scientific output.

## Reproducing the Article 1 pilot

See `examples/article1_pilot/` for a small key-free example using synthetic/public metadata and clearly labeled demonstration outputs.

For a manuscript-quality run, additionally preserve:

1. research question/protocol version;
2. exact search-strategy version;
3. retrieval dates;
4. software version/tag/SHA;
5. `config_digest`;
6. every provider/search track and its declared role;
7. exact execution ledger;
8. provider limits/pagination/truncation rules;
9. raw snapshots/hashes for frozen indexed searches;
10. deduplication state;
11. full-text/recoverability state;
12. coverage-loss and failure state;
13. human screening/adjudication state;
14. final PRISMA and manuscript-facing export identifiers.

## Release versioning

The citation-grade reconciled release is:

- **software version:** `0.2.0`;
- **published Git tag:** `v0.2.0`;
- **release date:** `2026-08-09`;
- **scientific maturity:** alpha.

Historical tags `v0.1.0` through `v0.1.8` remain immutable. They are not reused, moved or silently repointed. `v0.2.0` begins the reconciled citation-grade release line after historical tag/package version drift was identified.

`alpha` describes maturity; it is not a second competing version identifier.

The published `v0.2.0` tag remains frozen. Post-release remediation occurs on later commits/releases and must never rewrite that tag.

## Repository checkout vs wheel-only reproduction

The repository checkout is currently the canonical route for complete scientific reproduction because method/configuration files live at repository level under `config/`.

Differentiate explicitly:

- **zero-key demonstration from an installed package** — validated for the release workflow;
- **full scientific pipeline from a repository checkout**;
- **wheel-only full-pipeline execution** — must not be claimed unless separately validated with all required configuration assets available.

## Release validation record

For every citable release, preserve:

- operating system;
- Python version;
- exact dependency snapshot;
- commit SHA;
- tag;
- build command/results;
- canonical pytest results;
- zero-key demo result;
- documentation-link validation;
- security/gitleaks result;
- known limitations.

The `v0.2.0` release was validated before publication. Future candidate SHAs must be validated independently; an old test count or old workflow result is not evidence for a newer candidate.

## Known environment and method caveats

- Optional document/OCR features may require `tesseract`; PyMuPDF provides the primary PDF rendering path and poppler may be used as a fallback where configured.
- External bibliographic services may change availability, rate limits or response behavior; retrieval dates and provider failures must therefore be logged.
- The inherited Local Deep Research runtime is not part of the current canonical source tree.
- The project remains alpha and requires human methodological oversight.
- The current SciELO connector is prefix-scoped via Crossref (`10.1590`) and must not be described as comprehensive native SciELO platform coverage.
- GitHub dependency review is only a valid security gate when the repository Dependency Graph is enabled and the action actually executes successfully.