# Article 1 — software traceability matrix

This document links methodological claims that may be reported for Article 1 to the concrete NutEV Evidence Engine implementation, tests, and publication-facing outputs. It is a release-control artifact for `v0.2.0`; it does not replace the study protocol or human methodological decisions.

## Scope rule

The software **supports** identification, organization, deduplication, extraction, coding suggestions, traceability, screening workflow, and reproducible exports. It does **not** decide final inclusion/exclusion, final domain coding, clinical interpretation, or recommendations. Those remain human decisions under `docs/SCIENTIFIC_GOVERNANCE.md`.

## Traceability matrix

| Method claim / function | Implementation | Verification / tests | Output / evidence of execution | Human boundary |
|---|---|---|---|---|
| Research questions can be translated into transparent, per-database search expressions | `src/nutev/search/strategy_builder.py` and the querypack/search orchestration layer | canonical `nutev_tests/` suite; release validation reruns the full suite | strategy/grid output and search execution snapshots under `07_logs/` | final search strategy must be reviewed and frozen by the research team |
| Retrieved records are normalized and deduplicated with auditable identity rules | `src/nutev/analysis/dedup.py`; corpus/registry logic in `src/nutev/analysis/registries.py` | dedup/registry tests in `nutev_tests/` | unique document/version/family registries and corpus outputs | ambiguous duplicates/reissues can require reviewer adjudication |
| Full-text recoverability is measured rather than silently assumed | `src/nutev/acquire/recoverability.py`, `src/nutev/acquire/fulltext_resolver.py` | recoverability/full-text tests in `nutev_tests/` | `07_logs/fulltext_recoverability.*`, full-text status fields | paywalls are not bypassed; unresolved documents remain explicitly unresolved |
| Scanned documents can be extracted with OCR while failures remain visible | `src/nutev/extract/pdf_text.py`, `src/nutev/extract/smart_extract.py` | OCR/extraction regression tests in `nutev_tests/` | extraction status, OCR status, logs and coverage-loss records | poor OCR can block screening; reviewers must assess usability |
| Article-1 A/B/C/D domain coding is assistive and evidence-linked | `src/nutev/analysis/article1_coding.py`, `src/nutev/analysis/domain_states.py` | `nutev_tests/test_domain_states.py` and related Article-1 coding tests | `NUTEV_GUIDES_DOMAIN_STATES.csv`, evidence snippets/page/reference fields | machine suggestions never equal final coding; human review is required |
| Domain intensity/state does not treat missing keywords as proven absence | `src/nutev/analysis/domain_states.py` | `nutev_tests/test_domain_states.py` explicitly verifies blank intensity for `NOT_ASSESSED` and guards incidental mentions | state/intensity/evidence columns | intensity 0 / assessed-and-absent is a human judgment, not a machine inference |
| Document assets, versions, and families are kept distinct so mirrors/reissues do not inflate denominators | `src/nutev/analysis/registries.py` | registry tests in `nutev_tests/` | file-asset, document-version, document-family and denominator registries | edition/current-status decisions may require documentary review |
| Two independent reviewers and adjudication are represented explicitly | `src/nutev/review/screening.py` | `nutev_tests/test_screening.py` | screening queue, decision ledger, agreement report | two distinct humans decide; `uncertain` or disagreement remains conflict until adjudication |
| Scientific export is blocked until full-text inclusion is resolved | `src/nutev/review/screening.py` | `nutev_tests/test_screening.py::test_export_gate_blocks_until_validated` | export-ready / blocked status | the software records and enforces the gate; it does not choose the human decision |
| PRISMA-ScR counts do not fabricate a final included corpus | `src/nutev/export/article1_exports.py` | `nutev_tests/test_article1_exports.py` | `07_logs/prisma_counts.json`, PRISMA Mermaid diagram | `included` remains `pending` until human two-reviewer validation is complete |
| The central Article-1 domain result can be exported as a reproducible wide matrix | `src/nutev/export/article1_exports.py` | `nutev_tests/test_article1_exports.py::test_abcd_matrix_wide_shape` | `NUTEV_GUIDES_ABCD_MATRIX.csv` | matrix values remain subject to the human coding workflow |
| Config changes can be tied to a run | `src/nutev/config_provenance.py` and config-loading layer | config-provenance tests in `nutev_tests/` | `07_logs/config_provenance.json`, `config_digest` in run snapshots | methodological interpretation of a config change remains human |
| Evidence claims/candidates retain an explicit non-final status | audit/export layer and `docs/SCIENTIFIC_GOVERNANCE.md` | canonical audit/runtime tests in `nutev_tests/` | canonical audit CSVs under `02_metadata/`, derived convergence/gap tables under `06_tables/` | no `RecommendationCandidate` is a clinical recommendation or final protocol item |

## Citation-grade run record

For an analysis cited in a manuscript, record at minimum:

- software version `0.2.0`, Git tag `v0.2.0`, and exact commit SHA;
- execution date/time;
- Python version and environment snapshot;
- `config_digest` and config provenance file;
- frozen search-strategy identifier/version;
- input/output manifests;
- reviewer decision/adjudication ledger;
- coverage-loss / full-text recoverability report;
- the exact publication-facing tables used in the manuscript.

## Interpretation boundary

Passing software tests demonstrates that the implemented contracts behave as specified by the test suite. It does **not** by itself validate the scientific construct, establish clinical validity, or substitute for protocol adherence, reviewer training, risk-of-bias/quality appraisal, or methodological judgment.
