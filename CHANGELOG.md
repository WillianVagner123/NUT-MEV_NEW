# Changelog

All notable public product changes are documented here. Historical pre-v1 research-workflow details remain available in Git history and archived release notes.

## [Unreleased]

No product-scope expansion is planned before publication of the stable v1 line. Post-v1 changes should remain inside the supported reference-engine scope unless a new product decision is explicitly documented.

## [1.0.0] — 2026-08-18

### Stable product identity

- Renamed the supported product identity from **NutEV Evidence Engine** to **NutEV Reference Engine**.
- Established `1.0.0` / `v1.0.0` as the first stable Reference Engine release identity.
- Defined the supported product boundary as `SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT`.

### Search

- Multi-source bibliographic and institutional discovery.
- PubMed.
- Europe PMC.
- OpenAlex.
- Crossref.
- DOAJ.
- Semantic Scholar.
- Configured official/institutional sources.
- Native LILACS/BVS route.
- Native SciELO route.
- Optional configured web-search routes when credentials are available.
- Scopus and Web of Science are not simulated.

### Ranking

- NutEV taxonomy matching through `keyword_taxonomy*.json`.
- Configurable focus keywords through `config/reference_mode.json`.
- Title, keyword/subject and abstract/snippet weighting.
- Document-type weighting.
- Provider/source weighting.
- Strong-identifier bonus.
- Light recency weighting.
- Deterministic ranking exports for identical inputs/configuration.

### Outputs

- `TOP_REFERENCIAS.md`.
- `reference_ranking.csv`.
- `reference_ranking.jsonl`.
- `latest.json`.

### Removed from the supported v1 workflow

- Systematic/scoping-review orchestration.
- PRISMA output as a product goal.
- PRESS/FREEZE scientific gates.
- GF scientific-gate workflow.
- Automatic scientific INCLUDE/EXCLUDE decisions.
- Clinical recommendation claims from ranking scores.

Historical code/documents for earlier research workflows may remain for provenance or compatibility, but they are outside the supported v1 runtime and public output contract.

### Release metadata

- Package version synchronized to `1.0.0`.
- `CITATION.cff` synchronized to v1 identity.
- `.zenodo.json` synchronized to v1 identity without inventing a DOI.
- README and agent guidance rewritten around the stable Reference Engine product.

## Historical releases

### [0.2.0] — 2026-08-09

The `v0.2.0` release is preserved as immutable historical research-software history. Its Evidence Engine/scoping-review/PRISMA-oriented scope is not the supported v1 product scope.

Detailed historical release evidence remains available in:

- `docs/RELEASE_NOTES_v0.2.0.md`
- `docs/RELEASE_RECORD_v0.2.0.md`
- Git history and immutable tag `v0.2.0`

Historical `0.3.0.dev1` development work was never published as a `v0.3.0` release and is superseded by the stable v1 product identity.

[Unreleased]: https://github.com/WillianVagner123/NutEV-Evidence-Engine/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/WillianVagner123/NutEV-Evidence-Engine/releases/tag/v1.0.0
[0.2.0]: https://github.com/WillianVagner123/NutEV-Evidence-Engine/releases/tag/v0.2.0
