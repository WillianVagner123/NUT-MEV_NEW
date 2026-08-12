# Repository Structure — NutEV canonical

## Canonical runtime

Use `src/nutev/` for current scientific work.

Key areas:

- `search/` — global strategy registry/execution, provider adapters, snapshots and corpus construction;
- `review/` — human screening, full-text assessment and adjudication support;
- `acquire/` and `download/` — lawful full-text resolution and document acquisition;
- `extract/` — native text extraction and OCR;
- `analysis/` — classification, relevance, identity/deduplication, PRISMA and synthesis helpers;
- `engine/` — run IDs, events, validation and artifact provenance;
- `pipelines/` — current orchestration, including `play_pipeline.py` and the official-guides pipeline;
- `export/` — tables, logs, methods text, curation and manuscript-facing outputs;
- `ui/` — dashboard/control-center components;
- `global_watch/` — surveillance/monitoring, distinct from the definitive Article 1 search;
- `cli.py`, `settings.py`.

The old parallel `master_pipeline.py` + `querypacks/**` + default `--workstreams` runtime has been retired from the active tree. Git history preserves it for provenance.

## Scientific execution path

```text
versioned global strategy
        ↓
actual provider execution + immutable snapshots
        ↓
master corpus
        ↓
identity resolution / deduplication
        ↓
full-text resolution / download / OCR
        ↓
human screening and eligibility
        ↓
extraction / codebook / quality / synthesis
```

Article assignment happens after recovery. Historical labels such as `busca1`, `busca2a`, `busca2b` or `a3` may still occur in downstream taxonomy/scoring/history where they carry analytical meaning; they are not executable canonical search streams.

## One-command orchestration

```powershell
.\.venv\Scripts\nutev.exe play --project-root .\project_output_scientific
```

See `docs/PLAY.md`.

The automatic full PLAY remains PILOT-only until the scientific gate/freeze state required for a formal execution is implemented and satisfied.

## Configuration

Canonical configuration lives under `config/`, including provider/source registries, taxonomy/ontology, evidence lenses, scoring and official-source manifests.

Provider capability does not imply methodological inclusion.

Obsolete workstream-specific domain-rule configs were removed with the retired pipeline. Current configuration must be consumed by a supported runtime or documented scientific workflow.

## Tests

Canonical tests live under `nutev_tests/`.

```bash
PYTHONPATH=src python -m pytest -q nutev_tests
```

Tests that existed solely to preserve the retired querypack/workstream runtime were removed. Current tests should protect supported global-search, PLAY, provider, corpus, review, full-text/OCR, export and governance behavior.

## Project outputs

Local roots such as `project_output_scientific/` are ignored by Git.

Important layers include:

- `01_querypacks/` — strategy registry/version state (directory name retained for output compatibility; not the deleted source-code `querypacks` package);
- `03_corpus/search_raw/` — immutable provider snapshots;
- `03_corpus/search_processed/` — normalized/master corpus builds;
- `03_corpus/03B_public_downloads/` — lawful public downloads;
- `03_corpus/03C_official_docs/` — official documents;
- `04_ocr_text/` — OCR outputs;
- `05_extraction/` — extracted text;
- `06_tables/` — analysis/evidence tables;
- `07_logs/` — logs, ledgers and checkpoints;
- `10_curated/` — curated outputs;
- `12_play/` — PLAY summaries and ledgers.

## Inherited Local Deep Research history

The inherited `src/local_deep_research/**`, old tests, frontend/Docker/tooling and LDR console entry points are not part of the current working tree. They remain in Git history for provenance.

Active provenance is documented in `NOTICE.md` and `docs/PROVENANCE_AND_LICENSE.md`. Do not restore removed inherited runtime merely to preserve history, and do not remove required upstream attribution merely because the files are no longer in the active tree.

## Hygiene rule

A file belongs in the active tree only when it supports current runtime behavior, current scientific governance, reproducibility, current testing, release/provenance requirements or a deliberately retained downstream analytical function.

Superseded point-in-time migration plans, obsolete demos and dead compatibility code belong in Git history rather than the release snapshot.

## Scientific guardrail

`RecommendationCandidate` is not a clinical recommendation. Machine assistance does not replace human inclusion/exclusion, PRESS, freeze authorization or scientific adjudication.
