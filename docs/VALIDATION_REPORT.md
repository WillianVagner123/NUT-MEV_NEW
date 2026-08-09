# NutEV Evidence Engine — Release Validation Report

**Release:** `0.2.0`  
**Planned tag:** `v0.2.0`  
**Scientific maturity:** alpha  
**Publication rule:** the tag is created only from an exact `main` SHA whose `release-validation` workflow completed successfully.

## 1. Why the release line starts at v0.2.0

During release validation, the repository was found to already contain historical tags `v0.1.0` through `v0.1.8`. They are preserved as immutable history. Historical tag/package alignment was not consistently synchronized (for example, the `v0.1.8` tree still declared NutEV package version `0.1.0`). The citation-grade reconciled line therefore starts at **v0.2.0** rather than overwriting an existing tag.

## 2. Baseline validation evidence

The release-reconciliation/hardening branch passed the following GitHub Actions gates before merge:

| Gate | Result |
|---|---|
| canonical CI — Python 3.12 | PASS — 703 passed, 8 skipped, 1 xpassed |
| canonical CI — Python 3.13 | PASS — 703 passed, 8 skipped, 1 xpassed |
| blocking Ruff F/E9 | PASS |
| security-scan / gitleaks / repo hygiene | PASS |
| dependency-review | PASS |
| CodeQL | PASS |
| release identity (`0.2.0`) | PASS |
| unused tag check (`v0.2.0`) | PASS |
| wheel + sdist build | PASS |
| `twine check` | PASS |
| clean-wheel installation | PASS |
| zero-key demo from installed wheel | PASS |
| relative Markdown link check | PASS |
| environment snapshot upload | PASS |

These results validate the release controls themselves and the candidate state used in PR validation. Publication still requires the same `release-validation` workflow to pass on the exact `main` SHA that will be tagged.

## 3. Exact-SHA publication control

`.github/workflows/release-validation.yml` runs on pushes to `main` and performs, in order:

1. version consistency check across code, `.zenodo.json`, `CITATION.cff`, CHANGELOG and release checklist;
2. confirmation that `v0.2.0` does not already exist;
3. full canonical test suite;
4. wheel/sdist build;
5. `twine check`;
6. installation of the built wheel in a clean Python 3.12 environment;
7. `nutev --help` and zero-key `nutev demo-data` execution;
8. documentation-link validation;
9. capture of exact Python/pip/dependency environment;
10. upload of build/environment artifacts.

The publication workflow must consume the successful `workflow_run.head_sha`; it must not tag a different commit.

## 4. Scientific boundary

The software supports evidence identification, organization, deduplication, retrieval, extraction, coding suggestions, audit, screening workflow and reproducible exports. It is not the Clinical Decision Engine and does not provide diagnosis, individualized prescription or final clinical recommendations.

A `RecommendationCandidate` remains non-final. Final inclusion/exclusion, domain coding, scientific interpretation and protocol decisions remain human responsibilities.

See `docs/ARTICLE1_SOFTWARE_TRACEABILITY.md` for method claim → implementation → test → output → human-boundary mapping.

## 5. Reproducibility record

For the tagged release, retain:

- version `0.2.0`;
- tag `v0.2.0`;
- exact validated commit SHA;
- release-validation run ID;
- runner OS and Python version;
- `release_environment_python312.txt` dependency snapshot;
- built wheel and sdist;
- canonical test result;
- zero-key demo result;
- release notes;
- known limitations.

For manuscript scientific runs, additionally retain `config_digest`, config provenance, frozen search-strategy version, retrieval dates, reviewer/adjudication ledger, coverage-loss/full-text reports and exact publication tables.

## 6. Metadata and provenance

- `.zenodo.json` is the deposit metadata source for GitHub→Zenodo archival when both `.zenodo.json` and `CITATION.cff` are present.
- software version: `0.2.0`;
- license: MIT;
- creator listed: Willian Vagner Dorneles Schneider;
- ORCID and institutional affiliation are intentionally omitted from deposit metadata until confirmed rather than fabricated;
- `NOTICE.md` preserves historical LearningCircuit/Local Deep Research attribution and describes removed inherited paths as historical.

## 7. GO / NO-GO matrix

| Gate | Status before final tag |
|---|---|
| VERSIONING | PASS |
| TAG COLLISION | PASS (`v0.2.0` unused during validation) |
| TESTS | PASS |
| BUILD / TWINE | PASS |
| ZERO-KEY DEMO | PASS |
| REPRODUCIBILITY | PASS — release artifact snapshot implemented |
| SECURITY | PASS |
| PRIVACY | PASS by repository policy/hygiene gates; no clinical data intended in release |
| COPYRIGHT | PASS for repository software under current MIT/provenance policy; third-party protected full texts excluded |
| PROVENANCE | PASS with historical derivation explicitly disclosed |
| METADATA | PASS for required release metadata; optional ORCID/affiliation omitted until confirmed |
| CITATION | PASS for version/title/creator/license consistency; DOI added only after Zenodo exists |
| SCIENTIFIC CONSISTENCY | PASS with human-decision boundary documented |
| DOCUMENTATION | PASS subject to the final `main` release-validation run |

## 8. Final release decision

**READY FOR AUTOMATED PUBLICATION ONLY AFTER `release-validation` RETURNS SUCCESS ON THE EXACT FINAL `main` SHA.**

The publisher must then create the new immutable tag `v0.2.0` and GitHub Release from that SHA. If the Zenodo GitHub integration is enabled, the resulting release should be ingested by Zenodo; the DOI must be verified from the actual Zenodo record before it is added to the manuscript or citation files.
