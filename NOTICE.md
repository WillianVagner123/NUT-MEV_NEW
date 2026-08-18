# NOTICE

This repository contains the **NutEV Reference Engine** (`nutev-nutmev`) and retains licensing/provenance information from an inherited open-source codebase.

## Inherited project

- Upstream project: Local Deep Research (LDR)
- Original copyright: Copyright (c) 2025 LearningCircuit
- Original license: MIT License, retained in `LICENSE`
- Upstream repository: `https://github.com/LearningCircuit/local-deep-research`
- Exact derivation commit: not asserted; do not invent one

The inherited LDR runtime is not present in the current working tree. Historical material remains available through Git history, while the upstream MIT attribution remains preserved.

## Current NutEV tree

The current product consists of:

- `src/nutev/search/` - supported provider connectors and reference-search helpers;
- `tools/` - canonical collection and ranking tools;
- `config/` - search configuration, ranking configuration and NutEV taxonomy;
- `nutev_tests/` - current product tests;
- `docs/` - current product, release, provider and provenance documentation;
- `RODAR_TUDO.cmd` and Windows launchers - supported execution path.

The current `src/nutev/` runtime does not depend on the removed `src/local_deep_research/` tree.

## Creator metadata

Current release metadata identifies **Willian Vagner Dorneles Schneider** as the creator of the NutEV Reference Engine release metadata. ORCID and institutional affiliation are not asserted unless independently confirmed.

## Third-party dependencies

Runtime dependencies are declared in `pyproject.toml`. Each dependency and external provider retains its own terms, licenses and service conditions.

## Release provenance checks

Before a citable archive:

1. preserve the LearningCircuit MIT attribution;
2. confirm creator metadata in `.zenodo.json` and `CITATION.cff`;
3. confirm that no private data, secrets, protected full text or non-redistributable generated outputs are included;
4. verify the exact release SHA/tag;
5. add a DOI only after the archive service has actually issued and exposed it.

This NOTICE records provenance; it does not claim that current NutEV source code was authored by the upstream project.
