# Changelog

All notable changes to this project are documented here. The format is based on Keep a Changelog and the project uses Semantic Versioning for software releases. Methodological changes are additionally tracked in `docs/CHANGELOG_METODOLOGICO.md`.

## [Unreleased]

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

The release-reconciliation PR passed the repository CI on both Python 3.12 and 3.13 with **703 passed, 8 skipped and 1 xpassed** on each interpreter, together with successful security-scan, dependency-review and CodeQL runs. The final `v0.2.0` candidate must additionally pass the dedicated release-validation workflow on its exact SHA.

### Known limitations / pending before DOI

- ORCID and exact institutional affiliation remain human-confirmed metadata and must not be invented.
- The exact upstream derivation point should be confirmed if it is to be stated publicly in release metadata/provenance.
- Full scientific pipeline reproduction is canonical from a repository checkout while `config/` remains repository-root configuration; do not claim a wheel-only full-pipeline path unless separately verified.
- Development dependencies are version-ranged; the release workflow captures a release-specific environment snapshot.
- The software remains at **alpha maturity** despite the semantic software version `0.2.0`.

[Unreleased]: https://github.com/WillianVagner123/NutEV-Evidence-Engine/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/WillianVagner123/NutEV-Evidence-Engine/releases/tag/v0.2.0
