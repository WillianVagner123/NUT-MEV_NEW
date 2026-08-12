# Current code hygiene inventory

Status: **canonical runtime cleanup in progress for the pre-release development tree**.

The goal is to keep the NutEV runtime and documentation small, current and auditable without deleting live scientific behavior or required provenance.

## Removed from the active tree

Historical Local Deep Research application/runtime surfaces are no longer present in the working tree:

- `src/local_deep_research/**`;
- inherited legacy `tests/**`;
- LDR-specific console entry points;
- old frontend/Docker/cookiecutter tooling;
- historical runtime compatibility shims.

The former NutEV parallel workstream/querypack runtime has also been retired in the current cleanup branch:

- `src/nutev/pipelines/master_pipeline.py`;
- `src/nutev/querypacks/**`;
- `src/nutev/analysis/domains_busca1.py`;
- `src/nutev/analysis/domains_busca2a.py`;
- `src/nutev/analysis/domains_busca2b.py`;
- `src/nutev/analysis/prisma.py` (old generic/workstream PRISMA helper);
- `src/nutev/analysis/synthesis.py` (old workstream synthesis/export layer);
- `src/nutev/export/methods_writer.py` (old workstream methods/querypack writer);
- `src/nutev/export/qualification_writer.py` (old workstream qualification writer);
- `config/domain_rules_busca1.json`;
- `config/domain_rules_busca2a.json`;
- `config/domain_rules_busca2b.json`;
- the default CLI `--workstreams` mode;
- parity/tests that existed only to preserve that retired runtime;
- the obsolete `examples/article1_pilot/**` workstream-era demonstration.

Where a mixed test also covered still-supported behavior, that coverage was moved to canonical modules instead of restoring the old runtime. The canonical replacement is the registered global-search path plus `nutev play`. Git history remains intact.

## Obsolete documentation removed

Point-in-time audit/migration/refactor material that no longer described the canonical architecture was removed from the active tree, including:

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
- `docs/PROMPT_OTIMIZACAO.md`;
- `docs/NUTEV_PILOT_REAL_PROTOCOL.md`;
- `docs/AUDITORIA_PEGAR_TUDO.md`;
- `docs/PUBLIC_RELEASE_AUDIT.md`;
- `docs/AUDITORIA_CRUZADA_DRIVE_GITHUB_ARTIGO1.md`;
- `docs/NUTEV_REAL_RUN_READINESS_AND_LIMITATIONS.md`.

Historical contents remain available through Git history. Current PLAY/full-text behavior is documented in `docs/PLAY.md`; current release planning is in `docs/RELEASE_PLAN_v0.3.0.md`; current scientific rules are in `docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md`, `docs/SCIENTIFIC_GOVERNANCE.md` and `docs/REPRODUCIBILITY.md`.

## Canonical runtime

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

Independent current capabilities such as Global Watch, official-guide acquisition, dashboard/API, scoring/classification and export modules remain only when they still have supported downstream use; they are not a second canonical Article 1 search pipeline.

## What is not cleanup trash

Do not delete merely because a file is old or inherited:

- `LICENSE` / required MIT notices;
- `NOTICE.md` and provenance records;
- immutable release records for `v0.2.0`;
- scientific governance/contract documents;
- current taxonomy/scoring/codebook material still used downstream;
- tests for supported current behavior.

The inherited-code/license boundary is tracked separately in #1014.

## Deletion acceptance rule

A source/config/test file is safe to delete when all are true:

- no supported runtime imports it, or the importing legacy behavior is intentionally retired in the same change;
- canonical tests are migrated or removed together with the retired behavior;
- no normative scientific path requires it;
- replacement behavior exists where required;
- required attribution/provenance is preserved;
- Python 3.12/3.13, Windows smoke, blocking lint/compile, build and release-artifact checks remain green.

## Current validation gate

The workstream/querypack retirement is tracked by #1015 and PR #1019. It must remain unmerged if CI reveals a supported dependency on the deleted surface. Any such dependency must be migrated to the canonical path or explicitly retained before merge.

## Release boundary

Deleting files from the current tree does not rewrite or shrink Git history. Do not rewrite history merely to make the repository look smaller before Zenodo. A citable release should archive a clean reviewed snapshot that excludes obsolete active-tree material, protected full texts, credentials and generated/local outputs.
