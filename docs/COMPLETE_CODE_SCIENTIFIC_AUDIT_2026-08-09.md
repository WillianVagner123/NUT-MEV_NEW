# Complete Code and Scientific Audit — 2026-08-09

## Executive conclusion

**Repository state: CONDITIONALLY READY.**

The NutEV Evidence Engine core runtime is substantially cleaner, better separated from the historical Local Deep Research codebase, and technically stable on the currently declared Python versions. The citation-grade `v0.2.0` release was built from a tested commit and the current `main` has not changed runtime code after that release.

However, the repository is **not yet fully closed as the definitive computational record for the Article 1 search/methods**. The main remaining risks are not basic runtime breakage; they are scientific provenance semantics, incomplete supply-chain validation, documentation drift, and repository governance.

### Decision

- **Software release / public research-software object:** **GO**.
- **Core runtime stability:** **GO** based on current automated evidence.
- **Definitive Article 1 search execution + manuscript methods provenance:** **NO-GO until the P0 items below are resolved.**
- **Zenodo DOI metadata closure:** pending external Zenodo archival/verification.

---

## 1. Audit identity and scope

- Repository: `WillianVagner123/NutEV-Evidence-Engine`
- Public release: `v0.2.0`
- Release SHA: `bd4191a4dbc1a71cddf34911033078acc5165bb9`
- Post-release `main` audited: `b3b86d90fd63b3a9282a8fd6ee6fd49de8b97cd4`
- Audit date: `2026-08-09`
- Scientific maturity: `alpha`

Immediately after publication, `v0.2.0` and `main` were verified as identical. The only subsequent `main` change before this audit was post-release housekeeping: a release record, retirement of the one-shot publisher, and conversion of the release validator to a manual archived-release check. No `src/nutev/**` runtime change was introduced after the tagged release.

### Audit limitation

This audit inspected the current repository directly through the GitHub integration and used GitHub Actions execution evidence. A local clone could not be performed in the auditing runtime because outbound DNS access to GitHub was unavailable. Therefore, this report does **not** claim an independent local re-execution beyond the GitHub Actions evidence described below.

---

## 2. Status dashboard

| Domain | Status | Audit conclusion |
|---|---|---|
| Package/version identity | PASS | `0.2.0` / `v0.2.0` is reconciled and immutable |
| Canonical automated tests | PASS | Python 3.12 and 3.13 passed during release preparation |
| Build / distribution metadata | PASS | wheel + sdist + `twine check` passed |
| Clean-wheel zero-key demo | PASS | release validation passed |
| Secret / forbidden-file hygiene | PASS | latest hygiene scan found no forbidden tracked files; gitleaks passed |
| Legacy runtime isolation | PASS | historical runtime removed from current source tree; attribution preserved |
| Evidence-vs-decision boundary | PASS | explicit throughout scientific governance and traceability docs |
| Formal search execution ledger | PASS / PARTIAL | strong immutable ledger for currently supported formal providers |
| Generic master-pipeline executed-query provenance | **FAIL — P0** | generated querypack can be labeled as executed before budget/provider slicing |
| Definitive provider-path unification | **PARTIAL — P0** | formal executor currently covers only a subset of declared search sources |
| Run completion vs scientific readiness | **PARTIAL — P0** | provider execution success can coexist with downstream scientific-stage errors |
| Dependency supply-chain review | **NOT VALIDATED — P0** | workflow appears green but actual dependency-review action reported unsupported because Dependency Graph is disabled |
| Public documentation consistency | **PARTIAL — P0/P1** | several post-release and provider documents are stale |
| Source/provider registry consistency | PARTIAL | `source_registry.json` lags current provider inventory |
| Wheel-only full scientific reproduction | PARTIAL / documented | repository checkout is correctly documented as canonical full-run route |
| Static quality gates | PARTIAL | objective Ruff errors block; broader lint is advisory; no coverage threshold or mypy gate |
| OS portability CI | PARTIAL | canonical CI is Ubuntu-only |
| Repository PR hygiene | **PARTIAL** | at least 30 open PRs remain; many are old/divergent methodological experiments |
| Zenodo DOI | PENDING | no DOI should be claimed until the real archive is observed |

---

## 3. What is already well organized

### 3.1 Canonical package and versioning

`src/nutev/__version__.py` is the canonical package-version source and the release line is consistently `0.2.0`. The project metadata in `pyproject.toml`, `.zenodo.json`, and `CITATION.cff` is substantially reconciled.

Historical `v0.1.0`–`v0.1.8` tags were not overwritten. The citable reconciled line starts at `v0.2.0`, preserving repository history.

### 3.2 Legacy runtime removal

The inherited `src/local_deep_research/**` runtime is not present in the current tree. Attribution and provenance are retained in `LICENSE`, `NOTICE.md`, and Git history. The current runtime is `src/nutev/**`.

### 3.3 Explicit error and coverage-loss handling

The runtime contains typed error classes in `src/nutev/errors.py` and structured coverage-loss telemetry in `src/nutev/telemetry/coverage.py`. Provider, extraction, OCR, parsing, and related failures are generally represented rather than silently converted into evidence absence.

### 3.4 PDF/OCR extraction design

`src/nutev/extract/pdf_text.py` and `src/nutev/extract/smart_extract.py` implement layered extraction/OCR handling, cache validation, content-quality checks, and explicit unusable-document states. This is materially stronger than a pipeline that silently treats extraction failure as a negative scientific finding.

### 3.5 Human scientific decision boundary

The repository consistently distinguishes computational support from scientific/clinical judgment. `RecommendationCandidate` is not treated as a final recommendation, and Article 1 coding/screening remain human-adjudicated where specified.

### 3.6 Formal search execution ledger

The frozen-strategy path is one of the strongest parts of the repository. The strategy registry / executor / execution ledger can persist:

- exact provider;
- exact search expression;
- formal/pilot role;
- configured provider limit;
- rows returned;
- provider-reported total when available;
- execution status;
- immutable raw snapshot path;
- SHA-256 checksum;
- timestamps and run identity.

This is suitable as the foundation for manuscript-grade search provenance once all definitive source tracks are reconciled.

---

## 4. P0 — executed-query provenance in the generic master pipeline

### Finding

`src/nutev/pipelines/master_pipeline.py` builds a querypack and writes:

- `querypack_executed.json`
- `querypack_executed.csv`

before the per-provider execution code applies the operational query budget and slices provider queries.

The same pipeline later applies limits such as:

```text
busca1  -> QUERY_BUDGET 32
busca2a -> QUERY_BUDGET 36
busca2b -> QUERY_BUDGET 36
a3      -> QUERY_BUDGET 28
```

and uses a provider-level slice equivalent to:

```python
queries_for_provider = provider_queries.get(provider, [])[:query_budget]
```

The query builders can generate more expressions than those budgets. Therefore, an artifact named **`querypack_executed` can contain generated expressions that were not actually sent to a provider**.

### Why this matters

`src/nutev/export/methods_writer.py` consumes these artifacts as executed-search evidence. If such an artifact is used to write the manuscript methods, the software can overstate what was actually executed.

This is a **scientific provenance defect**, not merely a naming/style issue.

### Required correction

Before a definitive search is described from this path:

1. rename the pre-execution artifact to `querypack_generated.*`;
2. persist actual post-budget, post-provider routing expressions separately;
3. record attempt/result status for each actually submitted expression;
4. make `methods_writer.py` consume the true execution ledger, not the generated querypack;
5. test the invariant: **every query reported as executed has an execution attempt record**;
6. test the reverse invariant: **no generated-but-budget-truncated query appears in executed methods output**.

### Release impact

This does not invalidate the software release as a research-software object. It **does block using the generic pipeline audit artifact as definitive evidence of exactly what was searched** until fixed.

---

## 5. P0 — definitive search providers are split across execution paths

### Finding

The formal frozen-strategy executor currently declares executable providers:

- PubMed;
- Europe PMC;
- Crossref;
- OpenAlex.

The broader project configuration and source priorities also include sources such as:

- DOAJ;
- SciELO;
- official web / society / institutional sources;
- optional Google PSE discovery.

These additional sources are not all executed through the same formal strategy-executor ledger.

### Why this matters

This can be scientifically valid **only if the protocol explicitly defines separate search tracks** and each track has equivalent provenance controls. It is not acceptable to imply that one formal executor is the universal execution path if it is not.

### Required correction

Choose and document one of two models:

**Model A — unified executor**

Extend the formal executor/ledger to all definitive providers.

**Model B — explicit multi-track protocol**

Keep separate execution components, but require each track to store the same minimum provenance contract:

`strategy version -> exact expression/navigation rule -> source -> date/time -> limit/pagination rule -> returned/total -> raw snapshot -> checksum -> status -> reviewer decision`

For Article 1, the indexed-database track and official-guideline/site track should remain distinguishable in PRISMA/methods where their sampling logic differs.

---

## 6. P0 — provider completion is not the same as scientific readiness

### Finding

The generic pipeline records downstream errors such as Article 1 report/export or full-text coverage errors. However, the top-level `run_status` is substantially driven by provider execution events.

A run can therefore be operationally `completed` while an important downstream scientific artifact failed or remains scientifically incomplete.

### Required correction

Separate at least two state dimensions:

- `execution_status`: did the computational workflow execute?
- `scientific_readiness`: are all required scientific gates satisfied for the intended use?

For a manuscript-grade run, scientific readiness should require explicit gates for, as applicable:

- frozen search strategy;
- complete execution ledger;
- raw snapshot/checksum presence;
- deduplication completion;
- recoverability/full-text status;
- two-reviewer/adjudication status;
- export contract completion;
- PRISMA readiness;
- configuration provenance;
- no blocking coverage-loss event.

### Related semantic issue

Fields currently resembling `resume_used` / `checkpoint_resume_used` should represent whether a checkpoint was **actually consumed**, not merely whether execution was called with `resume=True`. If they represent capability/configuration, rename them to `resume_enabled`.

---

## 7. P0 — dependency review is green but was not actually performed

### Finding

`.github/workflows/dependency-review.yml` uses `continue-on-error: true` around the dependency review action.

The actual latest workflow log reported that dependency review is **not supported on the repository because Dependency Graph is disabled**. Because the step was allowed to continue on error, the overall workflow still appeared successful.

### Audit classification

**Dependency review = NOT VALIDATED.**

It must not be reported as a true security PASS merely because the workflow conclusion is green.

### Required correction

1. enable GitHub Dependency Graph for the repository;
2. verify dependency review executes successfully;
3. remove `continue-on-error: true` for the release/security gate;
4. rerun on `main`;
5. record the real result in the release/audit documentation.

---

## 8. Documentation drift that must be reconciled

### 8.1 `docs/SEARCH_PROVIDERS.md`

This document still contains obsolete statements, including a statement that the historical `src/local_deep_research` package remains in the repository. It has been removed.

The same document describes DOAJ/SciELO behavior in a way that no longer fully reflects the current default source priorities and methodology changelog.

### 8.2 `docs/CODE_AVAILABILITY.md`

Still describes `v0.2.0` as a planned tag and retains a pending release-date field even though the release was published on 2026-08-09.

### 8.3 `docs/REPRODUCIBILITY.md`

Still contains pre-publication wording such as a planned `v0.2.0` tag.

### 8.4 `docs/VALIDATION_REPORT.md`

This is the most important stale document. It still says validation has not yet been executed, retains `PENDING`/`HUMAN INPUT REQUIRED` release fields, and concludes `NOT READY FOR ZENODO`, despite the citation-grade GitHub release having been validated and published.

This must be converted from a pre-release template into the actual release validation record, while clearly leaving only true external/personal metadata pending.

### 8.5 `docs/RELEASE_CHECKLIST.md`

Still reads like a pre-release checklist with unchecked items and manual tag instructions. It should either:

- be frozen/renamed as the historical checklist used for v0.2.0 and filled with evidence, or
- be converted to a reusable release template and linked to `docs/RELEASE_RECORD_v0.2.0.md` for the completed release.

### 8.6 `docs/GITHUB_PUBLIC_SETTINGS_CHECKLIST.md`

Contains pre-release language and references that should be reviewed after the one-shot publisher was retired.

---

## 9. Source/provider registry drift

`config/source_registry.json` does not currently represent the complete provider inventory implied by the taxonomy/provider configuration and search implementation.

This creates semantic ambiguity about whether it is:

- the authoritative source registry;
- a limited provenance registry;
- or a historical/partial configuration artifact.

### Required correction

Either expand the registry to the full supported provider/source model or rename/document its narrower role. Do not maintain two files that appear authoritative but disagree.

---

## 10. Search-depth and recall controls

The project intentionally contains query and download budgets and bounded provider retrieval. These are operational controls, not automatically methodological defects.

They become a scientific risk when:

- a pilot limit is reused in a definitive search without explicit justification;
- truncation is not visible in provenance;
- a provider reports more hits than were retrieved and this is not flagged;
- the methods section describes the generated search space instead of the executed/retrieved space.

### Specific caution

SciELO-related retrieval must not be described as a comprehensive SciELO platform search unless the implementation and execution evidence truly support that statement. Any Crossref-prefix or bounded connector behavior must be described precisely.

---

## 11. CI and code-quality hardening

### Already strong

- full canonical tests on Python 3.12 and 3.13;
- objective Ruff `F` / `E9` errors are blocking;
- CodeQL is active;
- gitleaks/repository-hygiene workflow is active;
- release validation proved build, distribution metadata, wheel install, zero-key demo, and documentation links.

### Remaining quality debt

1. Broader Ruff/style checks are advisory (`|| true`) rather than blocking.
2. `pytest-cov` is available but there is no enforced coverage threshold.
3. `mypy` is a development dependency but there is no CI type-check gate.
4. Canonical CI currently runs on Ubuntu; no Windows/macOS smoke installation is part of the main gate.
5. GitHub Actions are referenced by version tags such as `@v5` / `@v6`, not immutable full commit SHAs.
6. Dependabot update automation is not currently configured.

These are **hardening items**, not evidence of a currently failing runtime.

Recommended order:

- add coverage reporting first, observe baseline, then define a justified threshold;
- introduce mypy incrementally rather than blocking the entire historical codebase immediately;
- add a Windows smoke install + `nutev --help` + zero-key demo;
- pin security/release-critical actions to commit SHAs;
- decide whether dependency-update automation should be re-enabled after Dependency Graph is fixed.

---

## 12. Packaging boundary

The wheel does not currently carry the complete repository-root `config/` scientific configuration contract. The documentation correctly states that a repository checkout is the canonical route for a complete scientific run.

### Audit classification

This is **not a release blocker because the limitation is explicitly documented**, and the clean-wheel zero-key demo passed.

### Future decision

Choose explicitly between:

- packaging all required scientific configs as package resources; or
- retaining repository-checkout reproduction as the formal manuscript contract.

Do not claim wheel-only full scientific reproduction unless it is tested.

---

## 13. Repository governance — open PR backlog

The audit query returned the maximum requested set of **30 open PRs**, meaning at least 30 PRs remain open. Many are July-era drafts or methodological/query experiments based on substantially older `main` states.

They do not contaminate `main`, but they create governance and scientific-interpretation noise: a reader can encounter multiple competing search-strategy proposals that are no longer canonical.

### Required triage

For every open PR, classify it as one of:

- `MERGE CANDIDATE — rebase + rerun current tests`;
- `SUPERSEDED — close with link to canonical replacement`;
- `HISTORICAL METHODOLOGY REFERENCE — close and retain discussion link`;
- `EXPERIMENTAL — retain only if there is an explicit owner and next decision`.

Do not mass-delete historical evidence; close/supersede transparently.

---

## 14. Security/privacy/copyright state

The latest repository-hygiene workflow reported no tracked forbidden file classes and no tracked file larger than 5 MB. Gitleaks passed. The current `.gitleaksignore` does not contain active suppressing fingerprints.

This supports a **PASS for the automated repository-content hygiene controls that were actually executed**.

It does **not** prove every possible privacy/copyright property of every text field by inspection; it means the defined automated gates found no violation.

The repository correctly preserves the MIT attribution/provenance boundary for the historical upstream code.

---

## 15. Zenodo and citation metadata

`CITATION.cff` currently carries:

- version `0.2.0`;
- release date `2026-08-09`;
- no fabricated DOI.

`.zenodo.json` also identifies version `0.2.0` and contains public-facing metadata without internal release TODO text.

ORCID, exact affiliation, and the Zenodo DOI must remain absent/pending until verified from real human/external records.

---

## 16. Priority remediation backlog

### P0 — before definitive Article 1 search/methods freeze

- [ ] Fix generated-vs-executed query provenance in `master_pipeline.py` and `methods_writer.py`.
- [ ] Define one auditable provenance contract for every definitive search track/provider.
- [ ] Separate computational `execution_status` from manuscript-grade `scientific_readiness`.
- [ ] Enable Dependency Graph and make dependency review genuinely blocking.
- [ ] Reconcile the stale release/search-provider/validation documentation with current reality.

### P1 — next hardening cycle

- [ ] Reconcile or redefine `config/source_registry.json`.
- [ ] Triage and close/rebase the 30+ open PR backlog.
- [ ] Add test coverage measurement and a justified threshold.
- [ ] Introduce incremental mypy/type-checking.
- [ ] Add Windows smoke CI.
- [ ] Pin release/security-critical GitHub Actions to immutable commit SHAs.
- [ ] Decide on automated dependency-update policy.
- [ ] Decide whether full scientific configs should be packaged in the wheel.

### P2 — maintainability

- [ ] Narrow broad exception catches where typed errors can replace them without reducing resilience.
- [ ] Continue decomposing large orchestration modules where it improves testability without changing scientific outputs.
- [ ] Preserve compatibility only where it has an explicit migration/removal plan.

---

## 17. Acceptance criteria for `AUDIT CLOSED`

The repository may be marked **AUDIT CLOSED FOR DEFINITIVE ARTICLE 1 EXECUTION** only when all of the following are true:

1. Every query described as executed maps to a real execution-attempt record.
2. Every definitive provider/search track has a frozen strategy and immutable execution evidence.
3. Provider truncation/pagination/limits are explicit and auditable.
4. Scientific readiness cannot be `ready` when a blocking downstream stage failed.
5. Dependency review actually executes and passes.
6. Public methods/reproducibility/validation documents describe the current implementation and release state.
7. The definitive search run records code SHA, strategy checksum, config digest, retrieval date, provider counts, raw snapshots/checksums, deduplication state, reviewer state, and exact manuscript-facing exports.
8. No manuscript statement attributes capability or final scientific judgment to the software beyond what the tagged/executed version implements.

---

## Final audit verdict

**Is the code organized?**  
**Mostly yes.** The canonical runtime is coherent, tested, versioned, separated from legacy code, instrumented for failure visibility, and supported by meaningful scientific governance.

**Is everything fully fixed?**  
**No.** The remaining highest-risk items are not ordinary code-formatting defects; they affect how the research software proves **what search was actually executed**, how it declares scientific readiness, and whether supply-chain review truly ran.

**Current verdict:**

> **GO for continued development and for the published v0.2.0 research-software release.**  
> **NO-GO for freezing the definitive Article 1 computational methods until P0 remediation is completed and re-audited.**
