# Changelog

All notable changes to this project are documented here. The format is based on Keep a Changelog and the project uses Semantic Versioning for software releases. Methodological changes are additionally tracked in `docs/CHANGELOG_METODOLOGICO.md`.

## [Unreleased]

### Release reconciliation

- Standardized the first citable software release identity as **`0.1.0` / `v0.1.0`**.
- Kept **alpha** as the scientific/software maturity designation rather than as a competing version identifier.
- Reconciled Zenodo/CFF metadata, provenance documentation and release instructions.
- Final DOI, release date, ORCID and exact institutional affiliation remain human-confirmed post-validation fields.

## [0.1.0] — first citable release candidate (alpha maturity)

This release candidate consolidates the NutEV Evidence Engine as a reproducible, auditable research-software object supporting the evidence layer of the NutEV project. It is **not** the separate clinical Decision Engine and does not produce final clinical recommendations.

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

### Changed

- Package identity and runtime were decoupled from the inherited Local Deep Research codebase.
- Inherited `local_deep_research` runtime code and legacy test tree were removed from the current working tree; provenance remains in Git history and attribution is preserved in `LICENSE`/`NOTICE.md`.
- The runtime compatibility monkey-patch layer was retired and its behavior moved into first-class modules with parity gates.
- Provider configuration was centralized and reconciled with implemented connectors.
- Retrieval connectors gained bounded/explicit deeper pagination options while retaining reproducible default behavior.
- Scientific output failures and coverage loss are surfaced in structured telemetry rather than silently swallowed.
- Audit CSV location and UI/read contracts were reconciled; derived convergence/gap/readiness matrices are produced on real runs.
- Python support declaration was tightened to match tested CI versions (`>=3.12,<3.14`).

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

### Known limitations / pending before DOI

- A **fresh validation run on the final release-candidate SHA** is still required before publication: full canonical tests, build, `twine check`, zero-key demo, documentation-link check and security scan.
- ORCID and exact institutional affiliation must be confirmed by a human before DOI minting.
- The exact upstream derivation point should be confirmed if it is to be stated publicly in release metadata/provenance.
- Full scientific pipeline reproduction is canonical from a repository checkout while `config/` remains repository-root configuration; do not claim a wheel-only full-pipeline path unless separately verified.
- Development dependencies are version-ranged; a release-specific dependency snapshot/constraints record should be captured for the archived version.
- The software remains at **alpha maturity** despite using the semantic software version `0.1.0`.

[Unreleased]: https://github.com/WillianVagner123/NutEV-Evidence-Engine/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/WillianVagner123/NutEV-Evidence-Engine/releases/tag/v0.1.0
