# Reproducibility

NutEV Evidence Engine is designed so that a person with no API keys and no protected data can reproduce a demonstration of the software shape, while scientific runs remain traceable to code, configuration, execution evidence and human-review decisions.

## Zero-key demonstration

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
python -m pip install -e ".[dashboard]"
nutev demo-data --project-root ./project_output_demo
nutev dashboard --project-root ./project_output_demo
```

The demo uses synthetic data and **is not scientific evidence**.

## What makes a scientific run reproducible

- **Versioned software:** identify software version, Git tag and exact commit SHA.
- **Declared Python support:** Python `>=3.12,<3.14`, with canonical CI on 3.12 and 3.13.
- **Dependency evidence:** validation records the resolved environment; version ranges are not an immutable lock by themselves.
- **Deterministic configuration provenance:** methodology/config inputs are versioned and methodological changes are recorded.
- **Immutable strategy identity:** scientific search versions are saved in the strategy registry rather than edited retrospectively.
- **Generated-versus-executed distinction:** a rendered expression is not execution evidence until a real attempt exists.
- **Attempt/run provenance:** provider, exact expression, status, timestamps, limits/pagination/truncation, counts and errors are preserved by the registered execution path.
- **Raw snapshots and hashes:** frozen indexed-database runs preserve immutable raw snapshots and SHA-256 values where required by the Article 1 contract.
- **Corpus provenance:** master-corpus builds identify the source search run and deduplication state.
- **Artifact hashes:** acquired artifacts and PLAY summary outputs carry hashes where applicable.
- **Failure visibility:** provider, download, extraction and OCR failures remain explicit rather than being converted into evidence absence.
- **Human decisions remain explicit:** no computational output is equivalent to PRESS approval, FREEZE, INCLUDE/EXCLUDE or final clinical/scientific approval.

## Canonical search provenance

The obsolete parallel workstream/querypack runtime has been retired. The canonical path is:

```text
registered immutable global strategy
        ↓
provider-specific rendering
        ↓
real provider execution
        ↓
execution ledger + snapshots/hashes
        ↓
master corpus build
        ↓
deduplication / identity review
        ↓
full text / OCR / human review
```

A strategy JSON or UI rendering is a **generated** object. Manuscript methods may only describe a provider expression as executed when corresponding run/attempt evidence exists.

## PLAY reproducibility

`nutev play` orchestrates the currently authorized PILOT path and writes a dedicated audit package under `12_play/`.

Typical artifacts include:

- `play_state.json`;
- `play_summary.json`;
- `play_summary.sha256`;
- `play_summary.md`;
- `search_providers.csv`;
- `fulltext_ledger.jsonl`;
- `download_manifest.jsonl`;
- `download_failures.jsonl`;
- `extraction_manifest.jsonl`.

PLAY reports provider truncation rather than calling capped retrieval exhaustive. Its automatic complete path remains PILOT-only until formal scientific gates are represented and satisfied.

## Scientific readiness is separate from execution

Computational completion does not imply scientific readiness. In particular:

- PILOT execution does not enter formal PRISMA identification counts;
- PRESS cannot be inferred by software;
- GF-06 date/filter decisions must reflect the actual formal method;
- R1/R2/adjudication setup is a human gate;
- FREEZE requires explicit authorization;
- `manuscript_ready` cannot be inferred merely from successful provider calls.

## Article 1 search tracks

The definitive Article 1 execution follows `docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md` and distinguishes:

1. frozen indexed-database execution;
2. official guideline/institutional source execution;
3. supplementary discovery only when explicitly included by protocol.

Different tracks may use different retrieval mechanisms, but each must preserve evidence of what was actually executed. Provider capability is not equivalent to methodological inclusion.

## Config provenance

A scientific run should preserve, as applicable:

- source config paths;
- per-file SHA-256 values;
- merged/effective configuration digest;
- software version and exact commit SHA;
- strategy/version identity;
- provider/runtime settings actually used.

Recording provenance must not alter scientific output.

## Reproducing an Article 1 PILOT

1. install the repository checkout;
2. create/open a scientific project root;
3. register an immutable PILOT global strategy;
4. run:

```bash
nutev play --project-root ./project_output_scientific
```

For a metadata-only smoke test:

```bash
nutev play --project-root ./project_output_scientific --metadata-only
```

A manuscript-quality/formal run additionally requires preservation of:

1. protocol/method version;
2. exact frozen strategy version;
3. GF-02 validation evidence;
4. PRESS record;
5. definitive retrieval dates and filters (GF-06);
6. screening-team/calibration setup (GF-07);
7. FREEZE authorization (GF-10);
8. every provider/search track and declared role;
9. exact execution evidence;
10. provider limits/pagination/truncation state;
11. raw snapshots/hashes;
12. master-corpus/deduplication state;
13. full-text/recoverability state;
14. failures/coverage loss;
15. human screening/adjudication state;
16. final PRISMA/manuscript-facing export identifiers.

## Release versioning

The latest public/citable release remains:

- **software version:** `0.2.0`;
- **published Git tag:** `v0.2.0`;
- **release date:** `2026-08-09`;
- **scientific maturity:** alpha.

Historical tags remain immutable. Current development is `0.3.0.dev1`; no `v0.3.0` release or DOI should be claimed before an exact candidate passes the release/provenance gates and the real Zenodo record is observed.

## Repository checkout vs wheel-only reproduction

The repository checkout remains the canonical route for complete scientific reproduction because methodological/configuration assets live at repository level.

Differentiate explicitly:

- zero-key demonstration from an installed package;
- scientific execution from a repository checkout;
- wheel-only full scientific execution, which must not be claimed unless separately validated.

## Release validation record

For every citable release preserve:

- operating system;
- Python version;
- dependency snapshot;
- exact SHA and tag;
- build results;
- canonical test results;
- Windows/zero-key smoke results;
- security/dependency-review results;
- release-artifact validation;
- known limitations;
- licensing/provenance decision for that exact release object.

## Known environment and method caveats

- OCR may require Tesseract; failure/absence is explicit.
- External bibliographic services may change availability, rate limits or response behavior; retrieval dates and failures must therefore be logged.
- Paywalls are not bypassed.
- The inherited Local Deep Research runtime is not part of the current canonical source tree; attribution/provenance is handled separately.
- The project remains alpha and requires human methodological oversight.
- The current SciELO connector is prefix-scoped via Crossref (`10.1590`) and must not be described as comprehensive native SciELO coverage.
- GitHub dependency review is valid only when the action actually executes successfully.
