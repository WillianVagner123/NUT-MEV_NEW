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

## Validation evidence before publication

The citation-grade release process validated:

- canonical tests on Python 3.12 and 3.13;
- blocking Ruff F/E9 checks;
- CodeQL;
- security-scan/gitleaks/repository hygiene;
- dependency review;
- release identity and unused-tag check;
- wheel and sdist build;
- `twine check`;
- clean-wheel installation;
- zero-key demo from the installed wheel;
- relative documentation links;
- release environment snapshot and build artifacts.

The canonical CI baseline recorded **703 passed, 8 skipped and 1 xpassed** on both Python 3.12 and Python 3.13 during release preparation.

## Scientific boundary

This release is a research Evidence Engine. It supports reproducible identification, organization, deduplication, extraction, audit, assistive coding, screening workflow and scientific exports. It does not provide diagnosis, individualized prescription or final clinical recommendations. `RecommendationCandidate` remains a non-final object and human methodological review remains required.

See `docs/ARTICLE1_SOFTWARE_TRACEABILITY.md` for the method claim → implementation → test → output → human-decision map.

## Release artifacts

The publication workflow was designed to attach the release-validation artifacts to the GitHub Release, including:

- `nutev_nutmev-0.2.0-*.whl`;
- `nutev_nutmev-0.2.0.tar.gz`;
- `release_environment_python312.txt`;
- `release_validation_record_v0.2.0.txt`.

## Zenodo status

**Zenodo Version DOI: pending public verification.**

The GitHub Release has been published. Zenodo's GitHub integration only archives releases for repositories enabled in the user's Zenodo GitHub settings. The public Zenodo record/DOI must be observed before any DOI is written into `CITATION.cff`, README, or the manuscript.

Once the record exists, append here:

- **Zenodo record ID:** `PENDING`
- **Version DOI:** `PENDING`
- **Concept DOI:** `PENDING`
- **Zenodo metadata verification:** `PENDING`

Do not alter or move tag `v0.2.0` to add DOI metadata. DOI/documentation updates belong to later commits on `main`; the archived release remains immutable.
