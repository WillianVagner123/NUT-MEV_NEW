# Provenance and license boundary

## Origin

NutEV Reference Engine evolved from the open-source Local Deep Research project maintained by LearningCircuit and distributed under the MIT License.

The inherited runtime is no longer present in the current working tree. Historical code remains available through Git history, and upstream attribution remains preserved in `LICENSE` and `NOTICE.md`.

## Current tree

The active NutEV software is now limited to the Reference Engine:

- provider connectors and search helpers under `src/nutev/search/`;
- collection and ranking tools under `tools/`;
- search/ranking/taxonomy configuration under `config/`;
- focused tests under `nutev_tests/`;
- current product and release documentation under `docs/`.

Do not claim either that every current NutEV line was authored by LearningCircuit or that the repository has no upstream MIT provenance.

## Release provenance gate

Before a public archive, verify:

1. upstream license/attribution remains intact;
2. current creator metadata is synchronized across `CITATION.cff` and `.zenodo.json`;
3. the exact release SHA/tag has passed required CI/security/build checks;
4. no secrets, private data, protected full text or non-redistributable generated outputs are included;
5. a DOI is recorded only after the archive service actually issues it.

Do not invent an upstream derivation commit, ORCID, affiliation or DOI.
