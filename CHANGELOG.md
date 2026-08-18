# Changelog

All notable public product changes are documented here. Older implementation history remains available through Git tags and commit history.

## [Unreleased]

### Repository cleanup

- Decoupled the canonical reference collector from obsolete research-workflow configuration.
- Removed unused review, protocol, orchestration, API, UI, monitoring, full-text/OCR and analysis surfaces from the current tree.
- Reduced runtime dependencies to those required by the supported Reference Engine.
- Rebuilt tests and CI around collection, provider identity, deduplication, taxonomy configuration and deterministic ranking.
- Replaced old compatibility behavior with a minimal Reference Engine CLI.
- Reduced documentation to current product, provider, provenance and release material.

## [1.0.0] - 2026-08-18

### Stable product identity

- Established **NutEV Reference Engine** as the supported product identity.
- Established version `1.0.0` as the stable software identity.
- Defined the supported flow as `SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT`.

### Sources

- PubMed
- Europe PMC
- OpenAlex
- Crossref
- DOAJ
- Semantic Scholar
- configured official/institutional sources
- native LILACS/BVS
- native SciELO
- optional Google Programmable Search, Brave and SerpAPI when configured

Scopus and Web of Science are not simulated.

### Ranking

- NutEV taxonomy matching through `keyword_taxonomy*.json`.
- Configurable focus keywords and provider weights.
- Document-type signals.
- Strong identifier bonus.
- Light recency weighting.
- Deterministic exports for identical inputs and configuration.

### Outputs

- `TOP_REFERENCIAS.md`
- `reference_ranking.csv`
- `reference_ranking.jsonl`
- `latest.json`

### Release metadata

- Package version synchronized to `1.0.0`.
- `CITATION.cff` and `.zenodo.json` synchronized to the Reference Engine identity.
- No archive DOI is claimed until a real archive record is issued and verified.

[Unreleased]: https://github.com/WillianVagner123/NutEV-Evidence-Engine/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/WillianVagner123/NutEV-Evidence-Engine/releases/tag/v1.0.0
