# Validated Windows run — 2026-08-18

This document records a real successful NutEV Reference Engine execution supplied by the operator after the first-run collection fixes were merged to `main`.

## Repository context

Current product identity: `1.0.0`  
Published immutable tag: `v1.0.0`  
Zenodo DOI: `10.5281/zenodo.21998607`

At documentation time, `main` included the post-release first-run fix that introduced the operational collection profile and non-fatal handling for access-denied BVS/SciELO native routes.

## Observed ranking result

The supplied `latest.json` output reported:

```json
{
  "mode": "REFERENCE_RANKING",
  "status": "COMPLETE",
  "created_at": "2026-08-18T14:41:59-03:00",
  "records_input": 8702,
  "records_unique": 8702,
  "taxonomy_groups_loaded": 115,
  "focus_keywords": [
    "lifestyle medicine",
    "lifestyle nutrition",
    "nutrition care",
    "dietary pattern",
    "food-based dietary guideline",
    "behavior change",
    "food literacy",
    "culinary",
    "shared decision making",
    "social determinants of health"
  ],
  "top_n": 100
}
```

The source files reported for that ranking were:

```text
C:\Users\Victor\NutEV-Evidence-Engine\project_output_reference\13_reference_collection\reference_20260818T143953-0300_246d457c\master_records.jsonl
project_output_reference\14_latin_native\latin_20260818T144145-0300\latin_native_records.jsonl
```

## Observed pipeline completion

The terminal ended with:

```text
Coleta geral: codigo 0
LILACS/BVS + SciELO: codigo 0
Ranking: codigo 0

SUCESSO: ranking de referencias gerado.
```

The generated outputs were:

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/latest.json
```

## Interpretation boundary

`records_input: 8702` and `records_unique: 8702` are the values emitted by the ranking run under the current identity/deduplication rules. They do not prove that all 8,702 records are semantically distinct publications. Parallel publications, closely related versions or items with different persistent identifiers may remain separate.

The TOP 100 is therefore a prioritized reading queue, not a scientific inclusion set and not a clinical recommendation.

## UI messages after completion

After `TOP_REFERENCIAS.md` opened in VS Code, the operator observed messages such as `StorageMainService`, Node `DeprecationWarning` and `Unknown channel`. These were emitted by VS Code after the Reference Engine had already completed successfully and are not recorded as NutEV runtime failures.

## Reproducibility note

For future auditable runs, record before execution:

```bat
git rev-parse HEAD
```

and retain `reference_ranking/latest.json` plus the source collection manifests. This ties an output set to the exact repository state and collection inputs used.
