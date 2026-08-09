# P0 Remediation Record — 2026-08-09

## Scope

This record tracks remediation of the P0 findings identified in `docs/COMPLETE_CODE_SCIENTIFIC_AUDIT_2026-08-09.md` after publication of the immutable `v0.2.0` release.

The published `v0.2.0` tag is not modified or repointed by this work.

## Current branch / pull request

- Branch: `agent/p0-scientific-provenance-remediation`
- Pull request: `#976` — `Fix P0 scientific provenance and readiness gates`
- Base: `main`
- Release tag preserved: `v0.2.0`

## Status matrix

| P0 finding | Remediation state | Evidence / implementation |
|---|---|---|
| Generated queries could be labeled as executed | **REMEDIATED IN PR #976** | Generated query packs are preserved as `*_generated`; `query_execution_ledger.json/.csv` is derived from actual provider attempt records; compatibility `*_executed` artifacts are finalized from the execution ledger only. |
| Methods writer could consume generated rather than actually attempted expressions | **REMEDIATED IN PR #976** | Methods docs now use finalized attempt evidence and explicitly name the JSON/CSV execution ledgers. |
| Definitive providers/search mechanisms were split across paths without one explicit manuscript contract | **REMEDIATED AT CONTRACT LEVEL IN PR #976** | `docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md` defines frozen indexed-database, official-source/institutional, and supplementary discovery tracks with minimum provenance requirements. |
| Provider/pipeline completion could be conflated with scientific readiness | **REMEDIATED IN PR #976** | `run_summary.json` now receives separate `execution_status` and `scientific_readiness` semantics. `manuscript_ready` requires explicit human-review and manuscript-gate flags. |
| Dependency review could appear green without running | **CODE REMEDIATED / REPOSITORY SETTING BLOCKED** | `continue-on-error` was removed. The check now fails honestly because GitHub Dependency Graph is disabled. Dependency Graph must be enabled before this gate can PASS. |
| Public docs contained pre-release/stale provider statements | **REMEDIATED IN PR #976** | README, Code Availability, Reproducibility, Search Providers, Zenodo setup, validation/release records and release/settings checklists were reconciled. |

## Query provenance contract after remediation

For the generic pipeline:

1. the pre-budget/pre-routing query space is preserved as `querypack_generated.*` and `provider_querypack_generated.*`;
2. each actual provider call produces a terminal record in `provider_performance.csv`;
3. the current/latest run is isolated by `run_id`;
4. `query_execution_ledger.json` and `query_execution_ledger.csv` contain the actual attempt-level execution evidence;
5. compatibility `querypack_executed.*` and `provider_querypack_executed.*` are rebuilt only from attempt records;
6. a generated expression truncated by an operational budget cannot appear in the executed methods evidence unless it has a matching attempt record;
7. query-audit finalization is idempotent for the same run and cannot overwrite the preserved generated query space on a second methods export.

## Scientific readiness contract after remediation

The software now distinguishes:

- `execution_status`: computational completion state;
- `scientific_readiness=blocked`: at least one detectable computational/scientific prerequisite failed;
- `scientific_readiness=computationally_ready_for_human_review`: no detected blocking computational condition, but no claim of human/manuscript approval;
- `scientific_readiness=manuscript_ready`: only when `human_review_complete=true` and `manuscript_gates_complete=true` are supplied explicitly and no blocker is detected.

The software therefore does not infer manuscript readiness from a completed provider/pipeline run.

## Article 1 multi-track search contract

`docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md` is normative for future definitive Article 1 executions and distinguishes:

### Track A — frozen indexed-database search

Uses frozen strategy versions and preserves exact provider expressions, execution timestamps/status, provider counts, raw snapshots, SHA-256 values and run-manifest hash.

### Track B — official guideline / institutional sources

Preserves source/organization manifest provenance, `config_digest`, attempt ledger, URLs, retrieval/download/extraction state, artifact hashes where applicable, and downstream human coding/review state.

### Track C — supplementary discovery

Optional providers are included only when declared by the protocol. Runtime capability is not treated as scientific inclusion.

The current SciELO connector is explicitly described as Crossref retrieval restricted to DOI prefix `10.1590`; it must not be represented as a comprehensive native SciELO platform free-text search.

## Automated validation on PR #976

After correcting the provenance regression test/document wording mismatch, the current P0 branch produced:

- canonical CI, Python 3.12: **PASS**;
- canonical CI, Python 3.13: **PASS**;
- blocking Ruff F/E9: **PASS**;
- security-scan: **PASS**;
- CodeQL: **PASS**;
- dependency-review: **FAIL — expected repository-setting blocker**.

The dependency-review failure is not a reported vulnerable dependency. The GitHub action explicitly reports that dependency review is unsupported because Dependency Graph is disabled.

## External/manual blocker

The repository owner must enable:

**GitHub repository Settings → Code security and analysis → Dependency graph**

After enabling it:

1. rerun the failed dependency-review job/check on PR #976;
2. verify that `actions/dependency-review-action` actually executes;
3. require a true PASS before merging the remediation PR;
4. do not restore `continue-on-error` merely to obtain a green badge.

## Merge decision

### Runtime/scientific code changes

**READY FOR MERGE BASED ON CI / SECURITY / CODEQL.**

### Repository security gate

**BLOCKED UNTIL DEPENDENCY GRAPH IS ENABLED AND DEPENDENCY REVIEW ACTUALLY PASSES.**

Therefore PR #976 should remain unmerged while that repository-setting blocker exists.

## Post-merge re-audit criteria

After Dependency Graph is enabled, dependency-review passes and PR #976 is merged:

1. run/observe CI, security-scan and CodeQL on the merged `main` SHA;
2. confirm `query_execution_ledger.*` invariants remain covered by canonical tests;
3. confirm `run_summary.json` readiness semantics remain separate from execution;
4. confirm public docs no longer describe `v0.2.0` as planned;
5. close the P0 audit as `AUDIT CLOSED FOR DEFINITIVE ARTICLE 1 EXECUTION`, subject to a real definitive run satisfying the execution contract;
6. address P1 hardening separately (source-registry semantics, open-PR governance, coverage/type/OS CI, action pinning and dependency-update policy).