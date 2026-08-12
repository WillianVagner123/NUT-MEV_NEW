# Repository Structure — NutEV canonical

## Canonical runtime

Use `src/nutev/` for current scientific work.

Key areas:

- `search/` — global strategy registry/execution, provider adapters, snapshots, corpus construction;
- `review/` — human screening, full-text assessment and adjudication support;
- `acquire/` and `download/` — lawful full-text resolution and document acquisition;
- `extract/` — native text extraction and OCR;
- `analysis/` — classification, relevance, PRISMA and synthesis helpers;
- `engine/` — run IDs, events, validation and artifact provenance;
- `pipelines/` — orchestration, including the canonical `play_pipeline.py`;
- `export/` — tables, logs, methods text, curation and manuscript-facing outputs;
- `ui/` — dashboard/control-center components;
- `global_watch/` — surveillance/monitoring, distinct from the definitive Article 1 search;
- `cli.py`, `settings.py`.

## Scientific execution path

The Article 1 canonical architecture is:

```text
versioned global strategy
        ↓
actual provider execution + immutable snapshots
        ↓
master corpus
        ↓
identity resolution / deduplication
        ↓
human screening
        ↓
full text
        ↓
extraction / codebook / quality / synthesis
```

Historical identifiers such as `busca1`, `busca2a`, `busca2b` and `a3` may remain in compatibility or downstream analysis modules. They are not separate canonical Article 1 searches.

## One-command orchestration

The supported one-command pilot path is:

```powershell
.\.venv\Scripts\nutev.exe play --project-root .\project_output_scientific
```

See `docs/PLAY.md`.

The first `nutev play` implementation is intentionally PILOT-only. Formal/PRISMA execution remains blocked until scientific gate/freeze authorization is represented in software.

## Configuration

Canonical configuration lives under `config/`, including provider/source registry, taxonomy, ontology, evidence lenses, scoring and official-source manifests.

Provider capability does not imply methodological inclusion.

## Tests

Canonical tests live under:

- `nutev_tests/`

Run:

```bash
PYTHONPATH=src python -m pytest -q nutev_tests
```

## Project outputs

Local project roots such as `project_output_scientific/` are ignored by Git.

Important layers include:

- `01_querypacks/` — search registry/version state;
- `03_corpus/search_raw/` — immutable provider snapshots;
- `03_corpus/search_processed/` — normalized/master corpus builds;
- `03_corpus/03B_public_downloads/` — lawful public downloads;
- `03_corpus/03C_official_docs/` — official documents;
- `04_ocr_text/` — OCR outputs;
- `05_extraction/` — extracted text;
- `06_tables/` — analysis/evidence tables;
- `07_logs/` — logs, ledgers and checkpoints;
- `10_curated/` — curated outputs;
- `12_play/` — one-command PLAY summaries and ledgers.

## Inherited Local Deep Research code

The inherited `src/local_deep_research/**`, old tests, frontend/Docker/tooling and LDR console entry points are not part of the current working tree. They remain in Git history for provenance.

Active provenance is documented in `NOTICE.md`. Historical cleanup status is summarized in `docs/LEGACY_CLEANUP_AUDIT.md` and `docs/LEGACY_MIGRATION_PLAN.md`.

Do not restore removed inherited runtime merely to preserve history.

## Compatibility pipeline

`src/nutev/pipelines/master_pipeline.py` and old workstream vocabulary remain compatibility/downstream surfaces while `nutev play` is matured. Do not use the legacy workstream command as the definitive methodological representation of the Article 1 formal search.

## Scientific guardrail

`RecommendationCandidate` is not a clinical recommendation. Machine assistance does not replace human inclusion/exclusion, PRESS, freeze authorization or scientific adjudication.
