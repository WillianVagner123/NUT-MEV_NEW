# Reference Engine cleanup audit

Date: 2026-08-18  
Branch: `agent/cleanup-reference-engine`  
Base `main`: `dd4dcb9857b64696ec61976ef63a3e1164eb32e8`

## Objective

Reduce the current working tree to the supported NutEV Reference Engine and remove obsolete product surfaces rather than retaining them as compatibility layers.

Canonical product flow:

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT
```

## Dependency finding

The original collector still obtained its PubMed query from a research-workflow-specific module/configuration. That coupling was removed before deleting the obsolete subsystem. The canonical query now lives in `config/reference_search.json` and is loaded by `src/nutev/search/reference_queries.py`.

## Refactors before deletion

- replaced the collector with a Reference Engine-specific multi-provider collector;
- replaced official-source validation with a small manifest loader independent of deleted orchestration code;
- removed obsolete control metadata from current collection outputs;
- converted ranking output sanitation to an explicit public metadata allowlist;
- rebuilt the CLI around only `--version` and provider listing;
- rebuilt CI/tests around the actual current product.

## Removed categories

| Category | Result | Reason |
|---|---|---|
| obsolete scientific workflow modules | removed | outside current product and no longer required by collection/ranking |
| article-specific orchestration | removed | outside current software scope |
| review/curation surfaces | removed | not part of reference discovery/ranking |
| API and UI | removed | not used by canonical flow |
| monitoring/watch services | removed | parallel abandoned product surface |
| full-text/OCR pipeline | removed | not used by metadata reference engine |
| analysis/export framework | removed | replaced by direct ranking exports |
| compatibility wrapper | removed | redundant with canonical launcher |
| old test suite | removed/rebuilt | tests now target current modules only |
| old documentation tree | removed/rebuilt | Git history preserves prior material |

## Preserved categories

- PubMed, Europe PMC, OpenAlex, Crossref, DOAJ and Semantic Scholar connectors;
- Google Programmable Search, Brave and SerpAPI optional connectors;
- native LILACS/BVS and SciELO collection tool;
- official-source manifests;
- every `config/keyword_taxonomy*.json` file;
- `config/reference_mode.json` and `config/reference_search.json`;
- license, notice, citation and archive metadata;
- CI/security/dependency/CodeQL infrastructure;
- canonical Windows launchers and ranking outputs.

## Dependency audit

Current runtime dependency target: `requests` only. Development/CI dependencies are isolated in the `dev` extra and `requirements/nutev-ci.txt`.

## Validation status

Remote GitHub Actions is the authoritative integration environment for this cleanup because the execution environment used to prepare the branch could not clone GitHub directly over DNS. No unexecuted local integration test is reported as passed.

Final validation requires all current branch CI/security/build jobs to pass at the exact final SHA. Exact file/line removal statistics and final check results are appended in the final validation commit.
