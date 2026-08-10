# Changelog

All notable changes to this project are documented here. The format is based on Keep a Changelog and the project uses Semantic Versioning for public software releases. Methodological changes are additionally tracked in `docs/CHANGELOG_METODOLOGICO.md`.

## [0.3.0] — release candidate: unified global-search and provenance architecture

This candidate freezes the current NutEV Evidence Engine research-software architecture for reproducible evidence identification, provenance, corpus construction and human-review workflows. It remains **alpha scientific maturity** and does not imply completed human screening, manuscript readiness or final clinical recommendations.

### Scientific architecture and provenance

- Made the merged one-global-search architecture the canonical scientific workflow: one article-independent frozen strategy, provider-specific rendering, one `run_id`, one master corpus, deduplication once, then article-specific screening/eligibility/extraction.
- Separated generated query space from expressions actually attempted.
- Added canonical `query_execution_ledger.json/.csv` derived from real provider-attempt records.
- Finalized compatibility `*_executed` artifacts only from actual attempts and preserved pre-execution space as `*_generated`.
- Made query-audit finalization idempotent per run.
- Made manuscript methods consume actual execution evidence rather than generated querypacks.
- Separated computational `execution_status` from `scientific_readiness`.
- Reserved `manuscript_ready` for explicit human-review and manuscript-gate completion rather than provider/pipeline success alone.
- Added `docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md` with distinct indexed-database, official/institutional and supplementary-discovery tracks.
- Clarified that the current SciELO connector is Crossref retrieval scoped to DOI prefix `10.1590`, not a comprehensive native SciELO platform free-text search.

### Precision and current-main hardening

- Added boundary-aware matching in classifier, relevance/scoring and curation paths to avoid short-term substring false positives such as `dash` inside `dashboard`.
- Required a real NutEV/NutMEV thematic anchor before operational curated priority; evidence type alone cannot prioritize unrelated clinical content.
- Reconciled UPF/NOVA, adherence/access and dietary-pattern signals in downstream curation/ontology without turning them into automatic inclusion criteria.
- Aligned Global Watch CKM scope and lexical precision.
- Expanded the downstream NutEV ontology to match current evidence domains without widening the frozen global search.
- Hardened metadata-only versus full-text status handling and preserved explicit failure states.
- Made checkpoint JSON deterministic.
- Hardened schema-bound CSV exports, Global Watch zero-row exports and operational empty manifests.

### Validation, build and supply chain

- Added branch-aware coverage measurement with a blocking floor of 70%; the release-candidate predecessor measured 73.19% on Python 3.12.
- Added Windows Python 3.12 installation/CLI/zero-key-demo smoke validation.
- Added incremental mypy checking for critical provenance modules.
- Added an explicit `compileall` syntax gate for `src/nutev` and blocking Ruff objective-error checks.
- Added `release-artifact-validation` for wheel/sdist build, metadata checking, clean-wheel installation, CLI startup and zero-key demo from the installed artifact.
- Kept dependency review blocking and required it to execute successfully with GitHub Dependency Graph enabled.
- Refreshed GitHub Actions to reviewed Node 24-compatible releases while preserving full-SHA pinning.
- Reconciled the current Python dependency boundary, removed an unused third-party arXiv client and raised the `pypdf` security floor.

### Governance and documentation

- Added durable root `AGENTS.md` scientific-agent governance and current scientific governance documentation.
- Closed the P0 infrastructure audit after generated/executed provenance, readiness semantics and dependency-review gates were fixed.
- Made README and local-run documentation canonical for the one-global-search workflow; legacy `--workstreams` execution is explicitly non-canonical for definitive scientific review.
- Reconciled provider, reproducibility, code-availability, validation, Zenodo and release documentation with the immutable `v0.2.0` history and current development state.
- Historical thematic PRs are being archived as superseded against canonical scientific backlog tickets rather than merged into the old workstream architecture.

### Release boundary

- `RecommendationCandidate` remains a candidate requiring human adjudication, not a clinical recommendation.
- NutEV Evidence Engine remains separate from any clinical Decision Engine.
- Definitive Article 1 scientific executions remain governed by `docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md` and may be only `computationally_ready_for_human_review` until human/manuscript gates are explicitly completed.
- ORCID, affiliation and Zenodo DOI are intentionally omitted unless independently confirmed.
- Published historical tags/releases, especially `v0.2.0`, remain immutable.

## [0.2.0] — first citable reconciled NutEV Evidence Engine release (alpha maturity)

This release consolidates the NutEV Evidence Engine as a reproducible, auditable research-software object supporting the evidence layer of the NutEV project. It is **not** the separate clinical Decision Engine and does not produce final clinical recommendations.

### Release identity and history

- The citable release identity is **`0.2.0` / `v0.2.0`**.
- Scientific/software maturity remains **alpha**; alpha is a maturity label, not a competing version suffix.
- The repository already contains historical tags `v0.1.0` through `v0.1.8`. Those tags are preserved as immutable history and are **not** reused or moved.
- Historical tag/version alignment was not reliable: for example, the `v0.1.8` tree still declared the NutEV package version as `0.1.0`. `v0.2.0` starts the reconciled citation-grade release line without rewriting that history.

### Added

- Canonical NutEV package and CLI under `src/nutev/`.
- Reproducible search, normalization, deduplication, retrieval, extraction and audit pipelines.
- Article 1 support for guideline/document discovery, A/B/C/D domain coding, page-linked evidence snippets, document/version/family registries and denominator handling.
- Two-reviewer screening structures, conflict/adjudication logic and screening-agreement reporting.
- PRISMA-oriented exports, evidence matrices, reference exports (BibTeX/RIS) and audit/convergence artifacts.
- Configuration provenance with per-file hashes and `config_digest` records.
- Zero-key synthetic demonstration data and documented local dashboard/API paths.
- Scientific governance, copyright/full-text policy, AI/human-oversight policy, data governance and reproducibility documentation.
- `CITATION.cff`, `.zenodo.json`, `NOTICE.md`, code-availability and Zenodo release documentation.
- Canonical CI on Python 3.12 and 3.13, plus blocking Ruff F/E9 checks.
- Security workflows including gitleaks and repository-hygiene checks.
- Dedicated release-validation workflow covering identity, tag collision, tests, build, `twine check`, clean-wheel demo, documentation links and environment snapshot.
- Article 1 software traceability matrix linking method claims to implementation, tests, outputs and human-decision boundaries.

### Changed

- Package identity and runtime were decoupled from the inherited Local Deep Research codebase.
- Inherited `local_deep_research` runtime code and legacy test tree were removed from the current working tree; provenance remains in Git history and attribution is preserved in `LICENSE`/`NOTICE.md`.
- The runtime compatibility monkey-patch layer was retired and its behavior moved into first-class modules with parity gates.
- Provider configuration was centralized and reconciled with implemented connectors.
- Retrieval connectors gained bounded/explicit deeper pagination options while retaining reproducible default behavior.
- Scientific output failures and coverage loss are surfaced in structured telemetry rather than silently swallowed.
- Audit CSV location and UI/read contracts were reconciled; derived convergence/gap/readiness matrices are produced on real runs.
- Python support declaration was tightened to match tested CI versions (`>=3.12,<3.14`).
- Release metadata, citation metadata, README, validation and Zenodo instructions were reconciled around one citation-grade release identity.

### Removed

- Inherited `src/local_deep_research/**` runtime tree and legacy `tests/**` tree from the current source tree.
- Legacy frontend/Docker/cookiecutter and other unused inherited infrastructure.
- Dead/orphan LLM and compatibility modules that were not part of the canonical NutEV execution path.
- Dependabot configuration from the current tree after the earlier public-release setup phase.

### Scientific safeguards

- `RecommendationCandidate` is never equivalent to a final recommendation.
- Machine coding and extraction remain assistive and require human review where defined by protocol.
- Missing full text/OCR limitations are surfaced rather than treated as evidence absence.
- Protected third-party PDFs/full texts and personal/clinical data are not intended for redistribution in the repository or release artifacts.

### Validation evidence

The release-reconciliation flow passed canonical CI on Python 3.12 and 3.13 with **703 passed, 8 skipped and 1 xpassed** on each interpreter, together with successful blocking lint, security-scan/gitleaks, CodeQL, build/distribution and zero-key release validation. A post-release audit established that the dependency-review action had **not actually executed** because GitHub Dependency Graph was disabled and the workflow allowed the error to continue. Dependency review for `v0.2.0` is therefore **NOT VALIDATED**, not PASS; see `docs/RELEASE_RECORD_v0.2.0.md`.

### Known limitations / pending after publication

- ORCID and exact institutional affiliation remain human-confirmed metadata and must not be invented.
- The exact upstream derivation point should be confirmed if it is to be stated publicly in release metadata/provenance.
- Full scientific pipeline reproduction is canonical from a repository checkout while `config/` remains repository-root configuration; do not claim a wheel-only full-pipeline path unless separately verified.
- Development dependencies are version-ranged; the release workflow captures a release-specific environment snapshot.
- The software remains at **alpha maturity** despite the semantic software version `0.2.0`.
- Zenodo DOI metadata remains pending until a real public archive record is verified.

[0.3.0]: https://github.com/WillianVagner123/NutEV-Evidence-Engine/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/WillianVagner123/NutEV-Evidence-Engine/releases/tag/v0.2.0
