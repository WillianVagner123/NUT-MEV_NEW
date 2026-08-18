# NutEV Reference Engine v1.0.0

**This is the first stable release of the NutEV Reference Engine.**

Release date: 2026-08-18

## Product identity

NutEV Reference Engine is a taxonomy-guided, multi-source reference discovery and ranking engine for Lifestyle Nutrition research.

The supported v1 product flow is:

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT
```

The product produces a prioritized reading/reference queue. Ranking is not scientific inclusion/exclusion and is not a clinical recommendation.

## Main capabilities

- multi-source bibliographic and institutional discovery;
- PubMed, Europe PMC, OpenAlex, Crossref, DOAJ and Semantic Scholar;
- configured official/institutional sources;
- native LILACS/BVS and SciELO routes;
- deterministic technical deduplication for ranking;
- NutEV taxonomy matching through `keyword_taxonomy*.json`;
- configurable focus keywords and provider weights;
- document-type and recency weighting;
- Markdown, CSV and JSONL ranking exports.

## Public outputs

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/latest.json
```

## Ranking tiers

- `A_TOP_REFERENCE`
- `B_STRONG_REFERENCE`
- `C_DISCOVERY`

These tiers express reading priority only.

## Product boundary

The supported v1 workflow does not perform systematic/scoping-review orchestration, PRISMA reporting, PRESS/FREEZE scientific gates, automatic INCLUDE/EXCLUDE decisions or clinical recommendations.

Scopus and Web of Science are not simulated.

Historical research-review modules and documents remain in the repository only for provenance or compatibility and are outside the supported v1 product contract.

## Release metadata

- Version: `1.0.0`
- Git tag target: `v1.0.0`
- License: MIT
- Zenodo metadata: `.zenodo.json`
- Citation metadata: `CITATION.cff`
- DOI: intentionally absent until a real Zenodo archive DOI is issued and verified

## Validation required before tag

The exact release candidate must pass:

- Python 3.12 CI;
- Python 3.13 CI;
- Windows smoke;
- canonical pytest suite;
- compile/ruff gates;
- typecheck used by the repository;
- security scan;
- dependency review;
- CodeQL;
- release artifact build/check/clean-wheel installation.

The `v1.0.0` tag must be created only after the release PR is merged and the exact final `main` SHA is verified.

## Zenodo publication rule

Do not claim `RELEASED / ZENODO ARCHIVED` until Zenodo has actually ingested the GitHub Release and a DOI has been issued and verified.
