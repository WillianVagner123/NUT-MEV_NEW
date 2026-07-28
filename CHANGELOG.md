# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Methodological changes are additionally tracked in
`docs/CHANGELOG_METODOLOGICO.md`.

## [Unreleased]

### Added
- Scientific search connectors: DOAJ, ClinicalTrials.gov, SciELO (via Crossref
  prefix 10.1590), Semantic Scholar and arXiv. Each follows the shared connector
  contract (timeout + exponential backoff, reproducible single-page default with
  opt-in bounded pagination via `NUTEV_<PROVIDER>_MAX_RESULTS`, cross-page dedup,
  normalization to the shared row schema, fully mockable network).
- Search Strategy page in the dashboard: authors a PICOS/PECO question into the
  exact per-base expression grid (PubMed/Europe PMC/Crossref/OpenAlex ×
  broad/balanced/specific), surfacing the existing `nutev strategy` builder (C4).
  Runnable `examples/picos.json` added.
- Optional olmOCR extraction backend (`NUTEV_OCR_BACKEND=olmocr`) for scanned
  PDFs, off by default. Non-deterministic and GPU-bound, so it is strictly
  opt-in and always falls back to the deterministic Tesseract path; NutEV ships
  no model weights.

### Changed
- SciELO and DOAJ are now part of the default `source_priority` of the search
  workstreams (versioned in `docs/CHANGELOG_METODOLOGICO.md`); default runs stay
  single-page/reproducible.

### Fixed
- The master pipeline now dispatches every provider a workstream opts into via
  `source_priority` (previously gated on a stale hardcoded map, silently dropping
  opted-in providers). `_provider_map()` derives from the orchestrator registry.
- Reconciled `source_priority` with executable providers: removed phantom
  `google_cse`/`ddg_web` entries (renamed to the real `google_pse`; dropped the
  unimplemented `ddg_web`) so every declared provider is dispatchable.

## [0.1.0-alpha] — first organized public release

First public, organized alpha focused on making the repository reproducible,
safe, easy to install and centered on NutEV/NutMEV.

### Added
- `docs/PUBLIC_RELEASE_AUDIT.md` — pre-change public-release audit.
- `src/nutev/__version__.py` — canonical version source (0.1.0).
- Minimal core dependencies + optional extras (`search`, `documents`,
  `dashboard`, `api`/`platform`, `llm`, `watch`, `mcp`, `dev`, `legacy`, `all`);
  `requirements/nutev-core.txt`; `docs/DEPENDENCY_ARCHITECTURE.md`.
- `docs/LEGACY_MIGRATION_PLAN.md` — sequenced legacy isolation.
- Provenance & citation: `NOTICE.md`, `CITATION.cff`, `CODE_OF_CONDUCT.md`.
- Open-science governance: `docs/SCIENTIFIC_GOVERNANCE.md`,
  `docs/AI_USE_AND_HUMAN_OVERSIGHT.md`, `docs/DATA_GOVERNANCE.md`,
  `docs/COPYRIGHT_AND_FULL_TEXT_POLICY.md`, `docs/REPRODUCIBILITY.md`,
  `docs/ROADMAP.md`.
- Community templates: `.github/PULL_REQUEST_TEMPLATE.md` and issue forms
  (`bug`, `feature`, `methodology`, `new-source`).
- Security workflows: gitleaks + repo-hygiene guard, dependency-review, CodeQL.
- Sanitized CI artifact builder `.github/scripts/build-safe-artifact.sh`.
- Reproducible examples: `examples/article1_pilot/`, `examples/minimal/`.
- `docs/GITHUB_PUBLIC_SETTINGS_CHECKLIST.md`, `docs/RELEASE_CHECKLIST.md`.

### Changed
- Package version now sourced from `src/nutev/__version__.py` instead of the
  legacy `local_deep_research` package.
- `[project.dependencies]` reduced to a minimal core; heavy/legacy stacks moved
  to optional extras (Flask, Elasticsearch, FAISS, Playwright, SQLCipher and the
  LangChain ecosystem are no longer installed for a basic run).
- Canonical test location standardized to `nutev_tests/` with test-group markers.
- Public README reorganized (status banner, does/does-not, zero-key demo,
  citation, license & provenance).
- Hardened public workflows: `/nutev-tests` gated on author association;
  artifact uploads sanitized (no raw captures/PDFs/HTML/webhook payloads).

### Removed
- **Inherited `local_deep_research` engine** (`src/local_deep_research/`, 768
  files) and the **legacy test suite** (`tests/`, 1905 files) removed from the
  tree (kept in Git history; provenance preserved in `LICENSE`/`NOTICE.md`).
- Legacy examples, Docker/compose, cookiecutter, unraid templates,
  `package.json`/`package-lock.json`, `README_old.md`, `bearer.yml`,
  `.grype.yaml`, the web-frontend workflow, `constraints/`,
  `community_benchmark_results/`, orphaned `.pre-commit-hooks/`, `changelog.d/`
  and the stale `pdm.lock`.
- The `legacy` extra and legacy packaging references (`[tool.setuptools]`
  package-data, torch pdm source); dependabot npm/docker ecosystems.
- Legacy `ldr`, `ldr-web`, `ldr-mcp` console scripts from the main install.
- Superseded `.github/ISSUE_TEMPLATE/*.md` (replaced by issue forms).

### Known issues / pending
- Two pre-existing scoring-threshold test failures in
  `nutev_tests/test_global_watch_query_builder.py` (unrelated to packaging).
- `.gitleaksignore` (57 KB) still needs manual re-triage.
- `pdm.lock` was removed; regenerate if pinned installs are needed (pip installs
  unaffected).
- The wheel does not bundle `config/`; full pipeline runs need the repo checkout
  (`git clone` + `pip install -e .`). Packaging `config/` is a tracked follow-up.
- `dependency-review` CI requires the repository's Dependency Graph to be enabled
  (repo setting); the workflow is non-blocking until then.

[Unreleased]: https://github.com/WillianVagner123/NutEV-Evidence-Engine/compare/v0.1.0-alpha...HEAD
[0.1.0-alpha]: https://github.com/WillianVagner123/NutEV-Evidence-Engine/releases/tag/v0.1.0-alpha
