# Release Record — NutEV Evidence Engine v0.2.0

## Immutable software identity

- **Software:** NutEV Evidence Engine
- **Version:** `0.2.0`
- **Git tag:** `v0.2.0`
- **Scientific maturity:** alpha
- **Release date:** 2026-08-09
- **Validated/tagged commit SHA:** `bd4191a4dbc1a71cddf34911033078acc5165bb9`
- **GitHub Release:** `https://github.com/WillianVagner123/NutEV-Evidence-Engine/releases/tag/v0.2.0`

The tag and `main` were verified as **identical** immediately after publication (`ahead_by=0`, `behind_by=0`). Historical tags `v0.1.0`–`v0.1.8` remain unchanged.

This record is post-release documentation. It does not move or rewrite the immutable `v0.2.0` tag.

## Validation evidence before publication

The citation-grade release process validated:

- canonical tests on Python 3.12 and 3.13;
- blocking Ruff F/E9 checks;
- CodeQL;
- security-scan/gitleaks/repository hygiene;
- release identity and unused-tag check;
- wheel and sdist build;
- `twine check`;
- clean-wheel installation;
- zero-key demo from the installed wheel;
- relative documentation links;
- release environment snapshot and build artifacts.

The canonical CI baseline recorded **703 passed, 8 skipped and 1 xpassed** on both Python 3.12 and Python 3.13 during release preparation.

### Dependency-review correction discovered post-release

The `dependency-review` workflow appeared green during release preparation, but the complete 2026-08-09 audit inspected the action result and found that GitHub dependency review was **not actually supported/executed because the repository Dependency Graph was disabled**. The step was configured with `continue-on-error: true`, so the workflow conclusion did not prove that dependency analysis had occurred.

Accordingly:

- **dependency review for `v0.2.0`: NOT VALIDATED**;
- this is a supply-chain validation gap, not evidence of a known vulnerable dependency;
- it does not rewrite or invalidate the immutable software tag;
- future release/security gates must enable Dependency Graph and require the action to execute successfully before dependency review may be reported as PASS.

See `docs/COMPLETE_CODE_SCIENTIFIC_AUDIT_2026-08-09.md`.

## Scientific boundary

This release is a research Evidence Engine. It supports reproducible identification, organization, deduplication, extraction, audit, assistive coding, screening workflow and scientific exports. It does not provide diagnosis, individualized prescription or final clinical recommendations. `RecommendationCandidate` remains a non-final object and human methodological review remains required.

The post-release P0 remediation also makes explicit that computational completion is not equivalent to manuscript readiness and that generated queries are not execution evidence. Those corrections belong to later commits/releases and do not retroactively alter the `v0.2.0` tree.

See:

- `docs/ARTICLE1_SOFTWARE_TRACEABILITY.md`;
- `docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md`;
- `docs/COMPLETE_CODE_SCIENTIFIC_AUDIT_2026-08-09.md`.

## Release artifacts

The publication workflow was designed to attach release-validation artifacts to the GitHub Release, including:

- `nutev_nutmev-0.2.0-*.whl`;
- `nutev_nutmev-0.2.0.tar.gz`;
- `release_environment_python312.txt`;
- `release_validation_record_v0.2.0.txt`.

## Zenodo status

**Zenodo Version DOI: pending public verification.**

The GitHub Release has been published. A public Zenodo record/DOI must be observed before any DOI is written into `CITATION.cff`, README, or the manuscript.

Once the record exists, append here:

- **Zenodo record ID:** `PENDING`
- **Version DOI:** `PENDING`
- **Concept DOI:** `PENDING`
- **Zenodo metadata verification:** `PENDING`

Do not alter or move tag `v0.2.0` to add DOI metadata. DOI/documentation updates belong to later commits on `main`; the archived release remains immutable.