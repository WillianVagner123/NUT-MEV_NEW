# P0 Remediation Record — 2026-08-09

## Scope and identity

This record tracks remediation of `docs/COMPLETE_CODE_SCIENTIFIC_AUDIT_2026-08-09.md` after publication of the immutable `v0.2.0` release.

- PR: `#976` — `Fix P0 scientific provenance and readiness gates`
- Branch: `agent/p0-scientific-provenance-remediation`
- Base: `main`
- Published object preserved: `v0.2.0`
- Post-release development package identity: `0.3.0.dev0`

The published tag is never moved or rewritten. Citation/archive metadata remains on the latest real release until a future release candidate is explicitly synchronized.

## Remediation status

| Finding / hardening item | State | Implementation |
|---|---|---|
| Generated queries could be labeled as executed | **REMEDIATED** | Generated space is preserved as `*_generated`; `query_execution_ledger.json/.csv` is derived from actual provider-attempt records; compatibility `*_executed` views are rebuilt only from those attempts. |
| Methods could consume generated rather than attempted expressions | **REMEDIATED** | Methods writer uses actual execution evidence and names the canonical ledger explicitly. |
| Query audit could be rewritten on repeated methods export | **REMEDIATED** | Finalization is idempotent per run. |
| Search providers/tracks lacked one manuscript contract | **REMEDIATED AT CONTRACT LEVEL** | `docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md` defines indexed-database, official/institutional and supplementary discovery tracks with minimum provenance. |
| Pipeline completion could imply scientific readiness | **REMEDIATED** | `execution_status` and `scientific_readiness` are separate; `manuscript_ready` requires explicit human/manuscript gates. |
| Dependency review could appear green without running | **CODE REMEDIATED / EXTERNAL SETTING BLOCKED** | `continue-on-error` removed; action SHA-pinned; workflow now fails honestly while GitHub Dependency Graph is disabled. |
| Public documentation drift | **REMEDIATED** | README, provider, reproducibility, code-availability, Zenodo, validation/release and GitHub-settings docs reconciled. |
| Search-source registry drift | **REMEDIATED** | `source_registry.json` is canonical for search/evidence sources and is regression-tested against `provider_registry.json`. |
| No coverage regression gate | **HARDENED** | Branch-aware baseline measured at 73.16%; blocking floor = 70%. |
| Linux-only verification | **HARDENED** | Windows Python 3.12 install/CLI/zero-key-demo smoke added. |
| No type-check gate on provenance core | **HARDENED** | Incremental mypy gate added to provenance-critical modules. |
| No explicit full-source syntax gate | **HARDENED** | `python -m compileall -q src/nutev` added. |
| Mutable Action references | **HARDENED** | Critical Actions are pinned to full immutable commit SHAs. |
| SHA pins could become stale | **HARDENED** | `.github/dependabot.yml` schedules weekly `github-actions` update PRs. |
| Gitleaks v2 Node-20 runtime | **HARDENED** | Migrated to signed `gitleaks-action v3.0.0` commit `e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e` (Node 24) and pinned by SHA. |
| Old PR backlog | **TRIAGED** | `docs/OPEN_PR_TRIAGE_2026-08-09.md` groups historical proposals by scientific family and forbids stale as-is merges. |

## Query provenance contract

For the generic pipeline:

1. `querypack_generated.*` and `provider_querypack_generated.*` preserve pre-budget/pre-routing space;
2. every actual provider call creates a terminal record in `provider_performance.csv`;
3. the current/latest run is isolated by `run_id`;
4. `query_execution_ledger.json/.csv` is the canonical attempt-level evidence;
5. compatibility `*_executed` artifacts are rebuilt only from attempt records;
6. a generated expression truncated by budget/routing cannot appear as executed without a matching attempt;
7. repeated methods export cannot relabel already-finalized execution artifacts as generated input.

## Scientific-readiness contract

- `execution_status`: computational completion only;
- `scientific_readiness=blocked`: a detectable prerequisite failed;
- `scientific_readiness=computationally_ready_for_human_review`: computational gates passed but human/manuscript approval is not inferred;
- `scientific_readiness=manuscript_ready`: only with explicit `human_review_complete=true` and `manuscript_gates_complete=true`, with no detected blocker.

Provider success therefore cannot automatically become manuscript readiness.

## Article 1 search tracks

`docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md` is normative for future definitive runs:

- **Track A — frozen indexed databases:** exact provider expressions, timestamps/status, counts, raw snapshots, SHA-256 and run-manifest hash;
- **Track B — official/institutional sources:** source manifest/config provenance, `config_digest`, attempt ledger, URLs, retrieval/extraction state, artifact hashes where applicable and downstream human state;
- **Track C — supplementary discovery:** included only when declared by protocol; runtime capability is not scientific inclusion.

The current SciELO connector is explicitly Crossref retrieval restricted to DOI prefix `10.1590`, not a comprehensive native SciELO platform free-text search.

## CodeQL investigation

A pre-existing PR-overlay CodeQL diagnostic affected `src/nutev/analysis/article1_coding.py` while pytest, Ruff and Python compilation succeeded. The ambiguous first docstring phrase `coding: tracks` was changed to `coding for tracks`; the PR diff alters only that docstring line, not Article 1 coding logic.

CodeQL was upgraded from Action v3 to v4. A fresh standalone CodeQL database built only from the current `article1_coding.py` was checked with a blocking diagnostic for `parse error`, `Could not process` and encoding errors and passed with no match. The temporary diagnostic workflow/PR was removed afterward. A post-merge CodeQL run on the new `main` SHA remains part of final audit closure so the base database itself is refreshed.

## Supply-chain hardening

The active development paths now pin full immutable SHAs for:

- `actions/checkout`;
- `actions/setup-python`;
- `github/codeql-action`;
- `actions/dependency-review-action`;
- `gitleaks/gitleaks-action`.

The official Action pins were selected from revisions exercised by the remediation validation path. Gitleaks was separately reviewed and migrated to the signed v3.0.0 Node-24 release commit. Weekly Dependabot `github-actions` PRs provide a reviewable update path for these pins.

## Validation evidence established during PR #976

Across validation cycles the branch has demonstrated:

- Python 3.12 canonical suite: **PASS**;
- Python 3.13 canonical suite: **PASS**;
- provenance/readiness regression tests: **PASS**;
- branch-aware coverage: **73.16%**;
- blocking coverage floor: **70%**;
- Windows Python 3.12 smoke: **PASS**;
- provenance-core mypy: **PASS**;
- full `src/nutev` compile gate: **PASS**;
- blocking Ruff F/E9: **PASS**;
- security-scan: **PASS**;
- CodeQL v4: **PASS in validation cycles**;
- fresh standalone CodeQL extraction of current Article 1 coding module: **PASS**.

The **exact final PR-head SHA** must pass the same non-external gates after the final supply-chain/documentation commit; earlier green runs are not substituted for final-SHA validation.

## One external/manual P0 blocker

Dependency review is not reporting a vulnerable dependency. It cannot start because GitHub Dependency Graph is disabled.

Required repository setting:

**GitHub repository → Settings → Code security and analysis → Dependency graph → Enable**

Then:

1. rerun dependency-review on PR #976;
2. verify the action actually executes;
3. require a true PASS before merge;
4. never reintroduce `continue-on-error` merely to obtain a green badge.

The available GitHub connector does not expose a setting action that can enable Dependency Graph.

## Merge decision

- Runtime/scientific remediation: **READY FOR FINAL SHA VALIDATION**.
- Repository dependency-review gate: **BLOCKED UNTIL DEPENDENCY GRAPH IS ENABLED AND THE ACTION ACTUALLY PASSES**.
- PR #976 therefore remains draft/unmerged.

## Post-merge audit closure

After the external gate passes and PR #976 is merged:

1. observe CI, coverage, Windows smoke, mypy, security-scan and CodeQL on the merged `main` SHA;
2. confirm the execution-ledger and scientific-readiness invariants remain covered;
3. confirm `main` is identified as post-release development and is not confused with frozen `v0.2.0`;
4. close the P0 audit as `AUDIT CLOSED FOR DEFINITIVE ARTICLE 1 EXECUTION`, subject to a real definitive run satisfying the execution contract.

Remaining non-P0 work can continue separately: wheel/config packaging boundary, broader typing/coverage goals, Python dependency-update policy and scientific consolidation of historical methodology PR proposals.