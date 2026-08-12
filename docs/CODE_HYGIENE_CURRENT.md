# Current code hygiene inventory

Status: **active cleanup record for the pre-release development tree**.

The goal is to keep the canonical NutEV runtime and documentation small, current and auditable without deleting live behavior or required provenance.

## Removed from the active tree

Historical Local Deep Research application/runtime surfaces are no longer present in the current working tree:

- `src/local_deep_research/**`;
- inherited legacy `tests/**`;
- LDR-specific console entry points;
- old frontend/Docker/cookiecutter tooling;
- historical runtime compatibility shims.

Git history remains intact.

## Obsolete documentation removed

The following point-in-time plans/audits were removed from the active tree after being superseded by current canonical governance, PLAY, release and hygiene documents:

- `docs/AUDIT_COMPLETE_PIPELINE_2026.md`;
- `docs/LEGACY_CLEANUP_AUDIT.md`;
- `docs/LEGACY_DEPENDENCY_MAP.md`;
- `docs/LEGACY_MIGRATION_PLAN.md`;
- `docs/OPEN_PR_TRIAGE_2026-08-09.md`;
- `docs/P0_AUDIT_CLOSURE_2026-08-09.md`;
- `docs/P0_REMEDIATION_RECORD_2026-08-09.md`;
- `docs/COMPLETE_CODE_SCIENTIFIC_AUDIT_2026-08-09.md`;
- `docs/REFACTOR_GLOBAL_WATCH_UNIFICATION.md`;
- `docs/REFACTOR_RUNTIME_COMPAT_MIGRATION.md`;
- `docs/RELEASE_CANDIDATE_v0.3.0.md`;
- `docs/PROMPT_OTIMIZACAO.md`.

Their historical contents remain available through Git history. Current release planning belongs in `docs/RELEASE_PLAN_v0.3.0.md`; current PLAY behavior belongs in `docs/PLAY.md`; current scientific execution rules belong in `docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md` and `docs/SCIENTIFIC_GOVERNANCE.md`.

## Compatibility runtime still awaiting coordinated retirement

The following surfaces are historical/non-canonical for Article 1, but still have runtime or test references and therefore are not safe blind-deletion targets:

- `src/nutev/pipelines/master_pipeline.py`;
- historical workstream vocabulary such as `busca1`, `busca2a`, `busca2b`, `a3`;
- querypack/domain modules consumed by the compatibility pipeline;
- related compatibility/offline tests and configuration.

Their controlled retirement is tracked in #1015. The removal must migrate or deliberately retire the remaining behavior, update CLI/docs/tests, and pass the canonical gates. The end state is one canonical PLAY/global-search runtime rather than two competing scientific execution paths.

## Canonical replacement direction

```text
registered/versioned global strategy
        ↓
provider execution + attempt ledger
        ↓
master corpus
        ↓
full-text resolution/download/OCR
        ↓
human-review queues
        ↓
extraction/codebook/quality/synthesis
```

`nutev play` is the one-command computational orchestrator for this path.

## Deletion acceptance rule

A source/config file is safe to delete when all are true:

- no supported runtime imports it, or the importing legacy behavior is intentionally retired in the same change;
- canonical tests are migrated or removed together with the retired behavior;
- no normative scientific path requires it;
- replacement behavior exists where required;
- required attribution/provenance is preserved;
- Python 3.12/3.13, Windows smoke, blocking lint/compile, build and release-artifact checks remain green.

## License/provenance boundary

`LICENSE`, `NOTICE.md`, Git history and the provenance records are **not cleanup trash**. The inherited-code/license boundary is tracked separately in #1014 and must be resolved before the next Zenodo archive without erasing required upstream attribution or misattributing current NutEV code.

## Release boundary

Deleting files from the current tree does not shrink Git history. Do not rewrite history merely to make the repository look smaller before Zenodo. A citable release should instead archive a clean reviewed snapshot that excludes obsolete active-tree material, protected full texts, credentials and generated/local outputs.
