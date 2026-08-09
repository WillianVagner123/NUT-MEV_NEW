# P0 Remediation Record — 2026-08-09

## Scope

This record tracks remediation of the P0 findings identified in `docs/COMPLETE_CODE_SCIENTIFIC_AUDIT_2026-08-09.md` after publication of the immutable `v0.2.0` release.

The published `v0.2.0` tag is not modified or repointed by this work. The post-release source tree identifies itself as **`0.3.0.dev0`** so development code cannot be mistaken for the exact published `0.2.0` software object. Public citation/archive metadata remains on the latest real release until a future release candidate is deliberately synchronized.

## Current branch / pull request

- Branch: `agent/p0-scientific-provenance-remediation`
- Pull request: `#976` — `Fix P0 scientific provenance and readiness gates`
- Base: `main`
- Published release tag preserved: `v0.2.0`
- Development package line: `0.3.0.dev0`

## Status matrix

| Finding | Remediation state | Evidence / implementation |
|---|---|---|
| Generated queries could be labeled as executed | **REMEDIATED IN PR #976** | Generated query packs are preserved as `*_generated`; `query_execution_ledger.json/.csv` is derived from actual provider attempt records; compatibility `*_executed` artifacts are finalized from the execution ledger only. |
| Methods writer could consume generated rather than actually attempted expressions | **REMEDIATED IN PR #976** | Methods docs now use finalized attempt evidence and explicitly name the JSON/CSV execution ledgers. |
| Definitive providers/search mechanisms were split across paths without one explicit manuscript contract | **REMEDIATED AT CONTRACT LEVEL IN PR #976** | `docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md` defines frozen indexed-database, official-source/institutional, and supplementary discovery tracks with minimum provenance requirements. |
| Provider/pipeline completion could be conflated with scientific readiness | **REMEDIATED IN PR #976** | `run_summary.json` receives separate `execution_status` and `scientific_readiness` semantics. `manuscript_ready` requires explicit human-review and manuscript-gate flags. |
| Dependency review could appear green without running | **CODE REMEDIATED / REPOSITORY SETTING BLOCKED** | `continue-on-error` was removed and the action is SHA-pinned. The check now fails honestly because GitHub Dependency Graph is disabled. |
| Public docs contained pre-release/stale provider statements | **REMEDIATED IN PR #976** | README, Code Availability, Reproducibility, Search Providers, Zenodo setup, validation/release records and release/settings checklists were reconciled. |
| Search-source registry lagged implemented providers | **REMEDIATED IN PR #976** | `source_registry.json` is the canonical search/evidence-source registry with an explicit crosswalk to `provider_registry.json`; a regression test requires full search-provider coverage. |
| No coverage regression gate | **HARDENED IN PR #976** | Branch-aware baseline measured at 73.16%; CI floor set conservatively at 70%. |
| Linux-only canonical verification | **HARDENED IN PR #976** | Added Windows Python 3.12 install, CLI-help and zero-key-demo smoke job. |
| No type-check gate on provenance-critical code | **HARDENED IN PR #976** | Added incremental mypy gate for logs/methods writer/strategy executor/strategy ledger. |
| Python syntax depended on indirect tooling | **HARDENED IN PR #976** | Added explicit `python -m compileall -q src/nutev` gate. |
| Critical official Actions referenced mutable release lines | **HARDENED IN PR #976** | Validated revisions of `actions/checkout`, `actions/setup-python`, `github/codeql-action` and `actions/dependency-review-action` are pinned to full commit SHAs. |
| SHA-pinned Actions could become stale | **HARDENED IN PR #976** | `.github/dependabot.yml` now schedules weekly `github-actions` update PRs for review. |
| Old PR backlog was not methodologically triaged | **TRIAGED IN PR #976** | `docs/OPEN_PR_TRIAGE_2026-08-09.md` groups historical July proposals by scientific family and forbids stale as-is merges. |

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

The software distinguishes:

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

## CodeQL extraction investigation

The earlier advanced CodeQL workflow could complete successfully while retaining a Python extractor diagnostic for `src/nutev/analysis/article1_coding.py`. Canonical tests, Ruff and an explicit Python `compileall` gate all accepted the module.

The investigation found that the module's original first docstring line contained `coding: tracks`, which the CodeQL extractor could interpret like an encoding marker. That wording was changed to `coding for tracks`; the PR diff changes only the docstring line and does not alter Article 1 coding logic.

CodeQL was upgraded from Action v3 to v4. Because pull-request analysis can use an incremental/overlay database based on the target branch, a **fresh standalone CodeQL database** was also created from only the current `article1_coding.py`. A blocking diagnostic searched the fresh extractor logs for `parse error`, `Could not process`, or an encoding diagnostic and completed successfully with no match.

Conclusion:

- the current Python source is syntactically valid (`compileall` PASS);
- the current Article 1 coding module is processable in a fresh CodeQL database;
- any residual diagnostic carried by the normal PR overlay belongs to the old base/overlay analysis state, not to a parse failure reproduced from the current file;
- the temporary diagnostic workflow/PR was removed/closed after this proof; the production workflow remains CodeQL Action v4.

A full post-merge CodeQL run on the new `main` SHA remains part of final audit closure so the base database itself is refreshed.

## Supply-chain hardening

The remediation branch now pins the critical **official GitHub/Actions** revisions used by the validated paths to full immutable commit SHAs:

- `actions/checkout`;
- `actions/setup-python`;
- `github/codeql-action`;
- `actions/dependency-review-action`.

The chosen SHAs correspond to revisions already exercised in the remediation validation path rather than untested tag movement. `.github/dependabot.yml` schedules weekly `github-actions` update PRs so these pins remain reviewable and maintainable.

The third-party `gitleaks/gitleaks-action` remains on its reviewed v2 release line pending a separate upstream/runtime review and is not misrepresented as SHA-pinned.

## Automated validation established during PR #976 development

The remediation branch has demonstrated across its validation cycles:

- canonical CI, Python 3.12: **PASS**;
- canonical CI, Python 3.13: **PASS**;
- focused provenance/readiness regression tests: **PASS**;
- measured branch-aware total coverage: **73.16%**;
- blocking coverage floor: **70%**;
- Windows Python 3.12 installation/CLI/zero-key demo: **PASS**;
- provenance-core mypy gate: **PASS**;
- full `src/nutev` Python compile gate: **PASS**;
- blocking Ruff F/E9: **PASS**;
- security-scan: **PASS**;
- CodeQL v4 workflow: **PASS in validation cycles**;
- fresh standalone CodeQL parse/extraction diagnostic for current `article1_coding.py`: **PASS**;
- dependency-review: **FAIL — expected repository-setting blocker**.

The exact final PR-head SHA must pass the same non-external gates after the last documentation/supply-chain commit; old green runs are not substituted for validation of a newer SHA.

The dependency-review failure is not a reported vulnerable dependency. The GitHub action explicitly reports that dependency review is unsupported because Dependency Graph is disabled, so dependency analysis cannot currently start.

## External/manual blocker

The repository owner must enable:

**GitHub repository Settings → Code security and analysis → Dependency graph**

After enabling it:

1. rerun the failed dependency-review job/check on PR #976;
2. verify that `actions/dependency-review-action` actually executes;
3. require a true PASS before merging the remediation PR;
4. do not restore `continue-on-error` merely to obtain a green badge.

The available GitHub connector does not expose a repository-setting action that can enable Dependency Graph, so this is the one P0 remediation gate that cannot be completed from the current tool surface.

## Merge decision

### Runtime/scientific remediation

**READY FOR FINAL SHA VALIDATION.**

### Repository security gate

**BLOCKED UNTIL DEPENDENCY GRAPH IS ENABLED AND DEPENDENCY REVIEW ACTUALLY PASSES.**

Therefore PR #976 must remain unmerged while that repository-setting blocker exists.

## Post-merge re-audit criteria

After Dependency Graph is enabled, dependency-review passes and PR #976 is merged:

1. observe CI, coverage, Windows smoke, mypy, security-scan and CodeQL on the merged `main` SHA;
2. confirm `query_execution_ledger.*` invariants remain covered by canonical tests;
3. confirm `run_summary.json` readiness semantics remain separate from execution;
4. confirm the new `main` package identity is not confused with the frozen `v0.2.0` release;
5. confirm public docs no longer describe `v0.2.0` as planned;
6. close the P0 audit as `AUDIT CLOSED FOR DEFINITIVE ARTICLE 1 EXECUTION`, subject to a real definitive run satisfying the execution contract;
7. continue the remaining P1 items separately: wheel/config packaging boundary, broader typing/coverage targets, third-party Action/runtime review, Python dependency-update policy and thematic scientific review of historical PR proposals.