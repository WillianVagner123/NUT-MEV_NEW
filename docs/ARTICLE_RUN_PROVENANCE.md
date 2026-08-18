# Article-run provenance contract

This document defines the durable-output contract for governed A1-A4 thesis ranking runs.

## Canonical source

Scientific scope is defined by `config/nutev_governance_manifest.json`. Article-specific ranking focus is defined by `config/article_reference_profiles.json`. The two files must declare the same governance version.

## Required execution scope

A governed thesis ranking run must declare exactly one article: `A1`, `A2`, `A3`, or `A4`.

Unscoped thesis runs fail closed. The general v1 reference-ranking mode remains available separately and must not be mislabeled as an article-specific thesis run.

## Durable directory

Every governed run receives a unique `run_id` and is preserved at:

```text
project_output_reference/reference_ranking/by_article/<ARTICLE>/runs/<RUN_ID>/
```

The run directory contains:

- `TOP_REFERENCIAS.md`;
- `reference_ranking.csv`;
- `reference_ranking.jsonl`;
- `nutev_governance_manifest.json` snapshot;
- `effective_reference_mode.json` snapshot;
- `run_manifest.json`.

The ranking artifacts and configuration snapshots are recorded with SHA-256 hashes in `run_manifest.json`.

## Latest pointers

`reference_ranking/by_article/<ARTICLE>/latest.json` points to the latest governed run for that article.

`reference_ranking/latest.json` is only a convenience pointer to the most recent ranking run of any type. It is not the canonical historical record for an article.

## Scientific boundary

Governance metadata controls scope and provenance only. It must not be interpreted as an automated eligibility decision, PRISMA state, causal conclusion, methodological-quality judgment, or clinical recommendation.

Final scientific inclusion/exclusion, interpretation, synthesis, and clinical decisions remain human-controlled.
