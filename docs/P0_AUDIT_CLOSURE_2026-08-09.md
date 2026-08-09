# P0 Audit Closure — 2026-08-09

## Scope

This record closes the P0 **research-software infrastructure** findings identified in `docs/COMPLETE_CODE_SCIENTIFIC_AUDIT_2026-08-09.md` after remediation in PR #976.

It does **not** declare Article 1 scientifically complete and does **not** substitute for a definitive Article 1 execution under `docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md`.

## Closure identity

- remediation PR: `#976` — `Fix P0 scientific provenance and readiness gates`;
- validated PR head: `7604a7e9ee52f8207ab3bb523afbc4e03985ab44`;
- squash merge commit on `main`: `9633b63db76fbb08d6c73ce5faab9377aa21a8ac`;
- merge date: `2026-08-09`;
- source-tree development version after merge: `0.3.0.dev0`;
- immutable published release preserved: `v0.2.0` / package `0.2.0`.

## P0 findings and disposition

### 1. Generated vs executed query provenance

**Status: CLOSED.**

The system now distinguishes generated query space from expressions actually attempted. Canonical attempt-level evidence is represented by `query_execution_ledger.json/.csv`, derived from provider-attempt records. Compatibility `*_executed` outputs are restricted to real attempts; `*_generated` artifacts remain pre-execution strategy space.

Manuscript-facing methods must use execution evidence rather than treating generated querypacks as proof of execution.

### 2. Providers split across execution paths without a common scientific contract

**Status: CLOSED AT GOVERNANCE/PROVENANCE LEVEL.**

`docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md` defines distinct but auditable tracks for indexed databases, official/institutional/guideline sources and supplementary discovery providers.

This closure does not imply that every technically available provider belongs in the definitive Article 1 protocol. Protocol inclusion remains a scientific decision.

### 3. Operational completion conflated with scientific readiness

**Status: CLOSED.**

Computational `execution_status` is separated from `scientific_readiness`. `manuscript_ready` is reserved for explicit human-review completion and manuscript-gate completion with no blocking computational condition.

### 4. Dependency review false-green behavior

**Status: CLOSED.**

`continue-on-error` was removed from the dependency-review action. GitHub Dependency Graph was enabled on 2026-08-09 and workflow run `31341721192` was rerun on the validated PR head. The `Dependency Review` step completed successfully rather than being bypassed.

### 5. Stale release/provider/reproducibility documentation

**Status: CLOSED FOR THE P0 REMEDIATION SCOPE.**

Documentation was reconciled around the immutable `v0.2.0` public release and the post-release `0.3.0.dev0` source-tree development identity. Provider scope and the SciELO-prefix/Crossref limitation were clarified.

## Automated validation on the exact PR head

The exact validated head `7604a7e9ee52f8207ab3bb523afbc4e03985ab44` had:

- `ci`: PASS;
- Python 3.12 canonical suite + branch-aware coverage gate: PASS;
- Python 3.13 canonical suite: PASS;
- Windows Python 3.12 install/CLI/zero-key demo smoke: PASS;
- provenance-core mypy: PASS;
- `compileall`: PASS;
- blocking Ruff F/E9: PASS;
- `security-scan`: PASS;
- Gitleaks: PASS;
- forbidden/large-file hygiene: PASS;
- CodeQL: PASS;
- dependency-review: PASS after Dependency Graph enablement.

## Post-merge verification

After squash merge:

- PR #976 is merged and closed;
- `main` contains source-tree package version `0.3.0.dev0`;
- `docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md` is present on `main` and normative for future definitive Article 1 executions;
- `.github/workflows/dependency-review.yml` remains blocking and contains no `continue-on-error` bypass;
- ref `v0.2.0` still resolves to package version `0.2.0` and is not repointed by this remediation.

The GitHub connector used for this audit exposes PR-triggered workflow lookup for a commit but does not provide a complete push-triggered post-merge run listing. Therefore this record does not invent a post-merge CI PASS claim that was not directly observed. The merged content is the squash of the exact pre-merge head whose four principal gates were observed green.

## Current scientific status

### Research-software infrastructure

**P0 AUDIT: CLOSED.**

The previously identified P0 infrastructure defects no longer block proceeding to a definitive scientific execution.

### Article 1 definitive execution

**NOT YET CLOSED / NOT YET MANUSCRIPT-READY.**

The next scientific phase is to freeze the Article 1 protocol/search strategy and execute the definitive run under the normative execution contract.

At minimum, preserve:

1. software version and exact SHA used for the run;
2. protocol/search-strategy version;
3. configuration digests;
4. declared search tracks/providers;
5. every actual attempt;
6. raw snapshots/hashes where required;
7. limits/pagination/truncation and errors;
8. deduplication and recovery state;
9. human screening/adjudication state;
10. PRISMA/manuscript-facing output identifiers.

## Release status

No `0.3.x` public release is authorized merely by closing this audit. `0.3.0.dev0` remains a development identity.

A future `0.3.x` candidate should be frozen only when there is a clearly defined scientific software object to preserve — preferably tied to the definitive Article 1 execution or another explicitly identified research milestone.

## Final disposition

**Infrastructure remediation: GO.**

**Definitive Article 1 manuscript execution: GO TO EXECUTION PHASE, subject to the Article 1 execution contract and subsequent human scientific gates.**
