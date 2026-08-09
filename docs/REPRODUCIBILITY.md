# Reproducibility

NutEV/NutMEV is designed so that a person with no API keys and no protected data can reproduce a demonstration of the pipeline shape, while scientific runs remain traceable to code, configuration and human-review decisions.

## Zero-key demonstration

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
python -m pip install -e ".[dashboard]"
nutev demo-data --project-root ./project_output_demo
nutev dashboard --project-root ./project_output_demo
```

This runs without OpenAI, Google, SerpAPI, Brave, real data or protected PDFs. It produces synthetic metadata, scored tables and reports under `project_output_demo/` and those artifacts are demonstration data, **not scientific evidence**.

## What makes a run reproducible

- **Versioned software:** every citable run must identify the software version, Git tag and exact commit SHA.
- **Declared Python support:** the current package declares Python `>=3.12,<3.14`, matching the canonical CI matrix (3.12 and 3.13).
- **Version-ranged development dependencies:** `pyproject.toml` and `requirements/nutev-*.txt` describe supported dependency ranges/minima; they are not, by themselves, an immutable environment lock.
- **Release-specific dependency snapshot:** a citable release should record the exact resolved environment used for validation (for example via a constraints/lock or `pip freeze` artifact) so the archived version can be reconstructed more precisely.
- **Deterministic config provenance:** rules/ontology/scoring/taxonomy under `config/` are versioned and methodology changes are recorded in `docs/CHANGELOG_METODOLOGICO.md`.
- **Config digest:** every scientific run should record the effective configuration inputs and `config_digest`.
- **Traceability:** claims and coding outputs should retain source/document identifiers and verifiable locators when the method requires them.
- **Run artifacts:** logs/snapshots under `07_logs/`, derived matrices/tables under `06_tables/`, metadata/audit artifacts under their canonical output locations, and curated outputs under `10_curated/`.
- **Human decisions remain explicit:** no automatic output is equivalent to final scientific or clinical approval.

## Config provenance (`config_digest`)

Taxonomy and scoring configs are assembled by deep-merging a base file under `config/` with sibling supplement layers. The merge order is deterministic and changes to any input file change the effective configuration.

Each scientific run records configuration provenance so the result can be tied back to the exact rule/taxonomy state. The provenance record should contain, as applicable:

- source config file paths;
- per-file SHA-256 values;
- merged config digests;
- one overall `config_digest`;
- software version and commit SHA.

The digest is provenance only; recording it must not alter the scientific output.

## Reproducing the Article 1 pilot

See `examples/article1_pilot/` for a small key-free example using synthetic/public metadata and clearly labeled demonstration outputs.

For a manuscript-quality run, additionally record:

1. research question/protocol version;
2. exact search-strategy version;
3. retrieval dates;
4. software version/tag/SHA;
5. `config_digest`;
6. database/source parameters;
7. external service versions/limitations where relevant;
8. human screening/adjudication state;
9. final export artifact identifiers.

## Release versioning

The first citable software release is being reconciled as:

- **software version:** `0.1.0`;
- **planned Git tag:** `v0.1.0`;
- **scientific maturity:** alpha.

`alpha` describes maturity; it is not a second competing version identifier for the same release.

Before DOI minting, the final candidate SHA must pass `docs/RELEASE_CHECKLIST.md`.

## Repository checkout vs wheel-only reproduction

The repository checkout is currently the canonical route for complete scientific reproduction because method/configuration files live at repository level under `config/`.

Differentiate explicitly:

- **zero-key demonstration from an installed package**;
- **full scientific pipeline from a repository checkout**;
- **wheel-only full-pipeline execution**, which must not be claimed unless separately validated with all required configuration assets available.

## Release validation record

For every citable release, record:

- operating system;
- Python version;
- exact dependency snapshot;
- commit SHA;
- tag;
- build command/results;
- canonical pytest command/results;
- zero-key demo result;
- documentation-link validation;
- security/gitleaks result;
- known limitations.

Do not reuse an old validation count as evidence for a newer candidate SHA.

## Known environment caveats

- Optional document/OCR features may require `tesseract`; PyMuPDF provides the primary PDF rendering path and poppler may be used as a fallback where configured.
- External bibliographic services may change availability, rate limits or response behavior over time; retrieval dates and provider errors must therefore be logged.
- The inherited Local Deep Research runtime is not part of the current canonical source tree.
- The project remains alpha and requires human methodological oversight.
