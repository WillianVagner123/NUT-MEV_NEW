# AGENTS.md - NutEV Reference Engine

This repository contains the NutEV Reference Engine, a focused multi-source reference discovery and ranking product for Lifestyle Nutrition.

## Product scope

The supported flow is:

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT
```

The engine collects bibliographic and official-source metadata, preserves provider identity, deduplicates records, matches the NutEV taxonomy and configurable focus terms, applies transparent ranking signals and exports a prioritized reading queue.

## Non-negotiable invariants

1. Never fabricate provider results, counts, identifiers, URLs or metadata.
2. Provider failures, rate limits, credential gaps and interface changes remain explicit.
3. Scopus and Web of Science are never simulated.
4. Ranking is reading/reference priority only; it is not a clinical recommendation or scientific eligibility decision.
5. Provider/source identity must survive collection and ranking.
6. Taxonomy and search configuration must remain inspectable and versioned in the repository.
7. Ranking must be deterministic for identical inputs and configuration.
8. Public ranking outputs use an explicit metadata allowlist.
9. Published tags/releases are immutable.
10. Never invent DOI, ORCID, affiliation, funding, authorship or execution evidence.
11. Do not commit secrets, private research data or protected full text without redistribution rights.

## Canonical runtime

- `RODAR_TUDO.cmd`
- `run_everything_now.cmd`
- `tools/run_everything_now.py`
- `tools/run_latin_sources.py`
- `tools/rank_references.py`
- `config/reference_search.json`
- `config/reference_mode.json`
- `config/keyword_taxonomy*.json`
- `src/nutev/search/`

Primary outputs:

- `project_output_reference/reference_ranking/TOP_REFERENCIAS.md`
- `project_output_reference/reference_ranking/reference_ranking.csv`
- `project_output_reference/reference_ranking/reference_ranking.jsonl`
- `project_output_reference/reference_ranking/latest.json`

## Change workflow

For non-trivial changes:

1. inspect the current `main` SHA;
2. use a dedicated branch;
3. keep changes inside the Reference Engine scope unless the product scope is explicitly changed;
4. add regression tests for ranking/provider/output-contract changes;
5. run or obtain CI/security/build evidence at the exact candidate SHA;
6. use a PR before merge;
7. do not bypass failing required checks.

Avoid feature creep. The supported product ends at reference discovery, normalization, deduplication, ranking and export.

## Releases

Package version, Git tag, GitHub Release, `CITATION.cff`, `.zenodo.json`, changelog and release notes must refer to one exact release identity. A DOI is recorded only after the actual Zenodo archive exists and has been verified.
