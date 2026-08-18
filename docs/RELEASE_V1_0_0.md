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
- Intended tag: `v1.0.0`
- License: MIT
- Archive metadata: `.zenodo.json`
- Citation metadata: `CITATION.cff`
- DOI: absent until a real archive record is issued and verified

## Release validation

The exact candidate SHA must pass Python 3.12 and 3.13 tests, Windows smoke, compile/lint, type checking, security scanning, dependency review, CodeQL and clean wheel/sdist validation before a release tag is created.

Published tags are immutable and must not be moved.
