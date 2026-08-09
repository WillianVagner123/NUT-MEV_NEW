# NutEV Evidence Engine v0.2.0

**Maturity:** alpha research software  
**Release identity:** `0.2.0` / planned Git tag `v0.2.0`

## Why v0.2.0

The repository already contains historical tags `v0.1.0` through `v0.1.8`. Those tags are preserved as immutable history. Historical tag/version alignment was not consistently synchronized — for example, the `v0.1.8` tree still declared the NutEV package as `0.1.0`. This release therefore starts the reconciled citation-grade line at **v0.2.0** rather than reusing or moving an existing tag.

## Purpose

NutEV Evidence Engine is research software that supports reproducible evidence work for Lifestyle Nutrition research, with particular support for the scoping-review/document-analysis workflow of Article 1. It makes computational transformations visible, versioned and auditable while preserving human control over scientific decisions.

## Scientific scope

This release supports:

- transparent search-strategy construction and execution;
- retrieval and normalization of scientific/official-document metadata;
- deduplication and document identity/version/family handling;
- open-access/full-text recoverability diagnostics;
- document extraction and OCR with visible failure states;
- Article-1 A/B/C/D domain coding suggestions with source snippets/pages;
- two-reviewer screening, conflict handling and adjudication workflow;
- PRISMA-ScR-oriented counts without declaring a final corpus prematurely;
- evidence/audit tables, provenance records and reproducible exports;
- zero-key synthetic demonstration data for installation/reproducibility checks.

## What this release does not do

The software does not provide diagnosis, individualized prescription, autonomous clinical decision-making or final clinical recommendations. `RecommendationCandidate` outputs are non-final candidates. Final inclusion/exclusion, domain coding, interpretation and protocol decisions remain human responsibilities.

## Reproducibility controls

Citation-grade use should record:

- version `0.2.0`, tag `v0.2.0` and exact commit SHA;
- execution date/time;
- Python/runtime environment snapshot;
- `config_digest` and config provenance;
- frozen search-strategy version;
- reviewer/adjudication records;
- run summary and coverage-loss/full-text reports;
- exact publication-facing outputs used in the manuscript.

See `docs/REPRODUCIBILITY.md` and `docs/ARTICLE1_SOFTWARE_TRACEABILITY.md`.

## Validation baseline

The release-reconciliation PR passed canonical CI on Python 3.12 and 3.13 with **703 passed, 8 skipped and 1 xpassed** on each interpreter. The same change passed `security-scan`, `dependency-review`, `codeql`, and blocking Ruff checks.

The dedicated `.github/workflows/release-validation.yml` validates the final `0.2.0` identity, ensures tag `v0.2.0` is unused, reruns the canonical suite, builds wheel/sdist, runs `twine check`, installs the built wheel in a clean virtual environment, executes the zero-key demo, checks relative documentation links, and captures an exact environment snapshot.

## Known limitations

- maturity remains **alpha** despite the SemVer release being `0.2.0`;
- external bibliographic/official sources can fail because of availability, rate limits, SSL/network conditions or publisher restrictions;
- protected full text is not redistributed and paywalls are not bypassed;
- OCR quality varies by source and can require human review;
- automated coding is assistive and requires reviewer validation;
- full scientific reproduction should prefer the repository checkout when root-level configuration is required unless a wheel-only path has been explicitly validated;
- optional external services and system OCR dependencies can affect feature availability.

## Citation

Use `CITATION.cff`. The Zenodo Version DOI will be added only after the GitHub Release has actually been archived. Do not substitute a placeholder DOI.

## License and provenance

The repository is distributed under the MIT license while preserving the original LearningCircuit attribution associated with the historical Local Deep Research base. The inherited engine is no longer present in the current working tree. See `LICENSE` and `NOTICE.md`.

## Relationship with the NutEV PhD

This repository is the **Evidence Engine**. It supports evidence identification, organization, auditability and Article-1/Article-2 evidence workflows. It is distinct from the clinical **Decision Engine**, which is not contained or executed here.

## Release procedure

Publish only from the exact `main` SHA that passes the release gate. Create the new immutable tag `v0.2.0`, publish **NutEV Evidence Engine v0.2.0**, then validate the resulting Zenodo record and use the **Version DOI** for manuscript reproducibility.
