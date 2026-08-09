# NOTICE

This project, **NutEV/NutMEV** (`nutev-nutmev`), evolved from an inherited open-source codebase and now contains a distinct scientific/methodological implementation under the NutEV Evidence Engine. This notice records provenance, licensing and the boundary between inherited history and the current source tree.

## 1. Inherited project

- **Inherited engine:** Local Deep Research (LDR)
- **Original copyright:** Copyright (c) 2025 **LearningCircuit** (see `LICENSE`)
- **Original license:** MIT License (retained in `LICENSE`, unchanged)
- **Upstream repository:** https://github.com/LearningCircuit/local-deep-research
- **Exact derivation point:** HUMAN INPUT REQUIRED before final DOI minting if a specific upstream commit/release is to be stated. Do not invent it.

The inherited LDR engine is **not present in the current working tree**. Its historical code remains in Git history, and its MIT attribution is preserved by the repository license and this NOTICE.

## 2. Current NutEV contributions

The current repository contains the NutEV Evidence Engine, including:

- the canonical NutEV engine under `src/nutev/`;
- NutEV configuration, taxonomy and methodological rules under `config/`;
- the canonical test suite under `nutev_tests/`;
- methodology, governance, reproducibility and release documentation under `docs/`;
- the `nutev` command-line entry point and associated dashboard/API components.

The current `src/nutev/` runtime does not depend on the removed `src/local_deep_research/` tree.

## 3. Boundary: inherited history vs current tree

| Path / component | Current status | Provenance / licensing note |
|---|---|---|
| `src/local_deep_research/**` | Removed from current tree; retained only in Git history | Inherited LDR code, MIT / LearningCircuit |
| legacy `tests/**` | Removed from current tree; retained only in Git history | Inherited historical test suite |
| `src/nutev/**` | Present | NutEV contribution; repository distributed under MIT |
| `config/**` | Present | NutEV project configuration/methodology files |
| `nutev_tests/**` | Present | NutEV canonical tests |
| NutEV `docs/**` | Present | NutEV scientific/methodological documentation |

Historical runtime compatibility shims such as `src/sitecustomize.py` and `src/usercustomize.py` are no longer part of the current tree and must not be described as retained runtime components.

## 4. NutEV authorship

Current release metadata identifies:

- **Willian Vagner Dorneles Schneider** — NutEV Evidence Engine creator metadata.

Before minting the DOI, confirm and synchronize the following human metadata across `.zenodo.json` and `CITATION.cff`:

- exact institutional affiliation;
- ORCID;
- any additional creators/contributors and their order, if applicable.

Do not derive scientific authorship automatically from commit history and do not invent missing identifiers.

## 5. Third-party dependencies and assets

- Python dependencies are declared in `pyproject.toml`; each dependency carries its own upstream license.
- Optional document, OCR, dashboard, API, watch and reporting stacks are installed through optional dependency groups.
- The current source tree should be audited before every citable release for third-party binary assets, copied code, generated outputs and other material whose redistribution terms may differ from the repository MIT license.

## 6. Release provenance gates

Before a citable Zenodo release:

1. Confirm the exact upstream derivation point if it will be stated publicly.
2. Confirm that no inherited binary/static assets remain without documented redistribution rights.
3. Confirm NutEV creator/contributor names, affiliations and ORCIDs.
4. Confirm that the release contains no protected PDFs/full text, personal/clinical data, credentials or non-redistributable outputs.
5. Keep the LearningCircuit MIT attribution in `LICENSE` and this NOTICE; do not remove historical attribution.

This NOTICE is a provenance record, not a claim that every current line of code originated in the upstream project.
