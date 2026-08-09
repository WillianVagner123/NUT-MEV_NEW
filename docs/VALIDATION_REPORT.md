# NutEV Evidence Engine — Release Validation Report

**Release:** `0.2.0`  
**Published tag:** `v0.2.0`  
**Release date:** `2026-08-09`  
**Validated/tagged commit SHA:** `bd4191a4dbc1a71cddf34911033078acc5165bb9`  
**Scientific maturity:** alpha

This document records the validation state of the already-published `v0.2.0` release. It is not a pre-release checklist and does not authorize moving or recreating the immutable tag.

## 1. Why the citation-grade line starts at v0.2.0

Historical tags `v0.1.0` through `v0.1.8` already existed and are preserved as immutable history. Historical tag/package alignment was not consistently synchronized. The reconciled citation-grade line therefore started at `v0.2.0` rather than overwriting earlier tags.

## 2. Validation evidence used for publication

The release preparation and exact-SHA publication flow validated the following controls:

| Gate | Recorded result |
|---|---|
| canonical CI — Python 3.12 | PASS — 703 passed, 8 skipped, 1 xpassed during release preparation |
| canonical CI — Python 3.13 | PASS — 703 passed, 8 skipped, 1 xpassed during release preparation |
| blocking Ruff F/E9 | PASS |
| security-scan / gitleaks / repository hygiene | PASS |
| CodeQL | PASS |
| release identity (`0.2.0`) | PASS |
| unused tag check before publication | PASS |
| wheel + sdist build | PASS |
| `twine check` | PASS |
| clean-wheel installation | PASS |
| zero-key demo from installed wheel | PASS |
| relative Markdown link check | PASS |
| environment snapshot/build artifact upload | PASS |
| dependency review | **NOT VALIDATED — see correction below** |

## 3. Dependency-review correction

A post-release audit on 2026-08-09 inspected the dependency-review action itself and found that GitHub dependency review had not actually run because the repository Dependency Graph was disabled. The workflow step used `continue-on-error: true`, allowing the overall job to appear successful despite the unsupported action.

Therefore the correct interpretation for `v0.2.0` is:

> **Dependency review = NOT VALIDATED.**

This is a supply-chain validation gap, not evidence that a vulnerable dependency was found. The immutable `v0.2.0` software tag is not rewritten. Future release/security gates must only report dependency review as PASS after Dependency Graph is enabled and the action executes successfully as a blocking step.

## 4. Exact release identity

The published release identity is:

- version: `0.2.0`;
- tag: `v0.2.0`;
- commit: `bd4191a4dbc1a71cddf34911033078acc5165bb9`;
- release date: `2026-08-09`.

The tag and `main` were checked as identical immediately after publication. Later documentation/remediation commits belong to later repository history and must not repoint `v0.2.0`.

## 5. Scientific boundary

The software supports evidence identification, organization, deduplication, retrieval, extraction, coding suggestions, audit, screening workflow and reproducible exports. It is not the Clinical Decision Engine and does not provide diagnosis, individualized prescription or final clinical recommendations.

A `RecommendationCandidate` remains non-final. Final inclusion/exclusion, domain coding, scientific interpretation and protocol decisions remain human responsibilities.

The complete post-release audit additionally identified two methodological semantics that must be corrected in later code before freezing a definitive Article 1 execution:

1. generated query space must be separated from expressions actually attempted;
2. computational completion must be separate from scientific/manuscript readiness.

Those remediations are tracked in `docs/COMPLETE_CODE_SCIENTIFIC_AUDIT_2026-08-09.md` and `docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md`.

## 6. Reproducibility record

For the tagged release, retain:

- version `0.2.0`;
- tag `v0.2.0`;
- exact commit SHA;
- release-validation workflow/run evidence;
- runner OS and Python version;
- exact resolved dependency snapshot;
- built wheel and sdist;
- canonical test evidence;
- zero-key demo result;
- release notes;
- known limitations.

For manuscript scientific runs, additionally retain:

- `config_digest` and config provenance;
- frozen search-strategy version where applicable;
- generated-versus-executed query distinction;
- attempt-level query execution ledger;
- retrieval dates;
- provider limits/truncation/pagination semantics;
- raw snapshots/checksums for frozen indexed searches;
- official-source manifest/artifact provenance;
- deduplication state;
- coverage-loss/full-text reports;
- reviewer/adjudication state;
- final PRISMA/manuscript export identifiers.

## 7. Metadata and provenance

- software version: `0.2.0`;
- license: MIT;
- creator listed: Willian Vagner Dorneles Schneider;
- ORCID and exact institutional affiliation remain omitted until confirmed rather than fabricated;
- `NOTICE.md` preserves historical LearningCircuit/Local Deep Research attribution;
- Zenodo DOI remains pending until a real public record is verified.

## 8. Corrected release decision

### `v0.2.0` as a public research-software release

**GO.** The release remains a valid immutable public software object with passing runtime/build/security controls documented above.

### `v0.2.0` dependency supply-chain review

**NOT VALIDATED.** The workflow conclusion was not sufficient evidence because the GitHub dependency-review action was unsupported while Dependency Graph was disabled.

### Definitive Article 1 computational methods freeze

**NO-GO for the `v0.2.0` implementation as the final methods-freeze contract.** Post-release audit findings require the P0 provenance/readiness remediation before a definitive Article 1 run is frozen and cited as such.

This distinction preserves the published release honestly without overstating what its validation evidence proves.