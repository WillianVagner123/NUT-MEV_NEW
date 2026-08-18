# NOTICE

This project, **NutEV/NutMEV** (`nutev-nutmev`), evolved from an inherited open-source codebase and now contains the **NutEV Reference Engine**. This notice records provenance, licensing and the boundary between inherited history and the current source tree.

## 1. Inherited project

- **Inherited engine:** Local Deep Research (LDR)
- **Original copyright:** Copyright (c) 2025 **LearningCircuit** (see `LICENSE`)
- **Original license:** MIT License (retained in `LICENSE`, unchanged)
- **Upstream repository:** https://github.com/LearningCircuit/local-deep-research
- **Exact derivation point:** not asserted in v1.0.0 metadata; do not invent a specific upstream commit/release.

The inherited LDR engine is **not present in the current working tree**. Its historical code remains in Git history, and its MIT attribution is preserved by the repository license and this NOTICE.

## 2. Current NutEV contributions

The current repository contains the NutEV Reference Engine, including:

- the canonical NutEV runtime under `src/nutev/`;
- NutEV configuration and taxonomy under `config/`;
- the canonical test suite under `nutev_tests/`;
- current product, provenance and release documentation under `docs/`;
- the `nutev` command-line entry point and associated compatibility/dashboard/API components;
- the supported v1 reference-ranking path driven by `RODAR_TUDO.cmd` and `tools/rank_references.py`.

The current `src/nutev/` runtime does not depend on the removed `src/local_deep_research/` tree.

## 3. Boundary: inherited history vs current tree

| Path / component | Current status | Provenance / licensing note |
|---|---|---|
| `src/local_deep_research/**` | Removed from current tree; retained only in Git history | Inherited LDR code, MIT / LearningCircuit |
| legacy `tests/**` | Removed from current tree; retained only in Git history | Inherited historical test suite |
| `src/nutev/**` | Present | NutEV contribution; repository distributed under MIT |
| `config/**` | Present | NutEV project configuration and taxonomy |
| `nutev_tests/**` | Present | NutEV canonical tests |
| `docs/**` | Present | Current and historical NutEV documentation; legacy scientific-review material is outside the supported v1 product scope |

Historical runtime compatibility shims such as `src/sitecustomize.py` and `src/usercustomize.py` are no longer part of the current tree and must not be described as retained runtime components.

## 4. NutEV creator metadata

Current v1.0.0 release metadata identifies:

- **Willian Vagner Dorneles Schneider** — creator of the NutEV Reference Engine release metadata.

Institutional affiliation and ORCID are intentionally omitted until independently confirmed. Additional creators/contributors must not be inferred automatically from commit history.

## 5. Third-party dependencies and assets

- Python dependencies are declared in `pyproject.toml`; each dependency carries its own upstream license.
- Optional document, OCR, dashboard, API, watch and reporting stacks are installed through optional dependency groups.
- Every release should be checked for third-party binary assets, copied code, generated outputs and other material whose redistribution terms may differ from the repository MIT license.

## 6. Release provenance checks

Before a citable Zenodo release:

1. Do not state an exact upstream derivation commit unless independently verified.
2. Confirm that no inherited binary/static assets remain without documented redistribution rights.
3. Confirm that creator metadata in `.zenodo.json` and `CITATION.cff` is synchronized.
4. Confirm that the release contains no protected PDFs/full text, personal/clinical data, credentials or non-redistributable outputs.
5. Keep the LearningCircuit MIT attribution in `LICENSE` and this NOTICE; do not remove historical attribution.

This NOTICE is a provenance record, not a claim that every current line of code originated in the upstream project.
