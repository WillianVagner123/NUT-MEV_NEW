# NutEV Reference Engine v1.0.0

**First stable software identity of the NutEV Reference Engine.**

Release date: 2026-08-18

## Product identity

NutEV Reference Engine is a taxonomy-guided, multi-source reference discovery and ranking engine for Lifestyle Nutrition.

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT
```

The product produces a prioritized reading/reference queue. Scores and A/B/C tiers are information-retrieval priority signals, not clinical or scientific decisions.

## Main capabilities

- PubMed, Europe PMC, OpenAlex, Crossref, DOAJ and Semantic Scholar;
- configured official/institutional sources;
- native LILACS/BVS and SciELO routes;
- optional credentialed web-search providers;
- deterministic cross-source deduplication;
- NutEV taxonomy matching through `keyword_taxonomy*.json`;
- configurable focus keywords and provider weights;
- document-type and light recency weighting;
- Markdown, CSV and JSONL ranking exports.

Scopus and Web of Science are not simulated.

## Public outputs

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/latest.json
```

## Release metadata

- Version: `1.0.0`
- Published tag: `v1.0.0`
- Release commit: `5728d79b05e618897f01ba93886a17584c9f215f`
- License: MIT
- Archive metadata: `.zenodo.json`
- Citation metadata: `CITATION.cff`
- Zenodo record: `21998607`
- DOI: `10.5281/zenodo.21998607`

## Release validation

The release candidate passed Python 3.12 and 3.13 tests, Windows smoke, compile/lint, type checking, security scanning, dependency review, CodeQL and clean wheel/sdist validation before the release tag was created.

The published tag `v1.0.0` points to commit `5728d79b05e618897f01ba93886a17584c9f215f` and is immutable. The subsequent DOI-documentation patch does not alter that tag or archived release snapshot.
