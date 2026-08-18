# Reference Engine cleanup audit

Date: 2026-08-18  
Cleanup branch: `agent/cleanup-reference-engine`  
Initial audit base: `dd4dcb9857b64696ec61976ef63a3e1164eb32e8`  
Final reconciled base before merge: `ed051bf57026c826cf77569cc58fdce89c8d6407`  
Validated cleanup head: `1d418d26bb3fe72e460b728b9193997aad03d365`  
Merged `main`: `55344c4201febfe435fba1bc001ac96fd5d96dc8`

## Objective

Reduce the current working tree to the supported NutEV Reference Engine and remove obsolete product surfaces rather than retaining them as compatibility layers.

Canonical product flow at the time of this cleanup:

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT
```

The later guardrail layer extends the operational flow with traceability gating and audit outputs; see `docs/AUDITABILITY_AND_GUARDRAILS.md`.

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

Current runtime dependency target at cleanup time: `requests` only. Development/CI dependencies are isolated in the `dev` extra and `requirements/nutev-ci.txt`.

## Final diff statistics

PR #1082 (`Clean repository for Reference Engine v1`) changed 459 files, with 1,159 additions and 67,375 deletions.

## Final validation

GitHub Actions was the authoritative integration environment for this cleanup because the preparation environment could not clone GitHub directly over DNS. No unexecuted local integration test is reported as passed.

All workflows associated with validated cleanup head `1d418d26bb3fe72e460b728b9193997aad03d365` completed successfully:

- `ci` — success;
- `security-scan` — success;
- `dependency-review` — success;
- `codeql` — success;
- `release-artifact-validation` — success.

The cleanup PR was marked ready only after these checks completed successfully and was merged without bypass. The resulting `main` merge commit is `55344c4201febfe435fba1bc001ac96fd5d96dc8`.

The merge commit points to the cleaned Reference Engine tree. Release metadata on `main` remained synchronized at version `1.0.0`.

## DOI state: historical clarification

At the exact time this cleanup audit was written, no Zenodo DOI had yet been claimed because an archive DOI had not been independently verified. That statement described the repository state **at that point in time** and must not be read as a current assertion.

The stable v1.0.0 archive was subsequently published and verified as:

- Zenodo record: `21998607`;
- DOI: `10.5281/zenodo.21998607`.

The immutable release snapshot remains the `v1.0.0` tag; later guardrails and documentation changes on `main` do not rewrite that archived snapshot.

## Result

The cleanup established the Reference Engine as the supported product and removed obsolete research-review and parallel product surfaces from the current tree. Those historical surfaces remain recoverable through Git history but are not part of the supported runtime.

For the current fail-closed provenance, quarantine and hashing contract, use `docs/AUDITABILITY_AND_GUARDRAILS.md` rather than treating this historical cleanup document as the current operational specification.
