# Registered Search Execution and Identification Ledger

## Purpose

The Search Strategy page can now execute a frozen strategy version instead of
running the text currently visible in the form. This protects formal searches
from silent changes after protocol approval.

The execution layer reuses the canonical NutEV provider orchestrator. It does
not introduce a second search implementation.

## Workflow

1. Build the global search in the single research field.
2. Save an immutable strategy version in the Search Strategy Registry.
3. Select the frozen version, breadth, providers, result limit, and checkpoint
   behavior.
4. Execute the selected providers.
5. Preserve one immutable provider-result snapshot per provider.
6. Record the provider execution, exact expression, status, counts, checksum,
   and paths in SQLite.
7. Write a run manifest and calculate the identification count before
   deduplication.

## Storage

The existing registry database remains:

```text
<project_root>/01_querypacks/search_registry.sqlite3
```

The execution feature adds two tables without changing or deleting the existing
strategy tables:

- `search_runs`: one row per grouped execution of a strategy version;
- `search_execution_artifacts`: one row per provider snapshot.

Snapshots are written to unique, append-only directories:

```text
<project_root>/03_corpus/search_raw/<version_id>/<run_id>/
├── pubmed.jsonl
├── europepmc.jsonl
├── crossref.jsonl
├── openalex.jsonl
└── run_manifest.json
```

No earlier run directory is reused or overwritten.

## What “raw” means in this stage

The JSONL files preserve the rows returned by the canonical provider connector
before cross-provider normalization and deduplication. They are provider-result
snapshots, not byte-for-byte HTTP response bodies. Each snapshot receives a
SHA-256 checksum and remains traceable to:

- strategy and version;
- exact stored expression;
- provider query and API filter;
- retrieval status;
- returned and provider-reported counts;
- checkpoint path and provider metadata.

A later ingestion phase may additionally retain original HTTP payloads when a
provider exposes them safely.

## Provider expressions

PubMed and Europe PMC receive the stored Boolean expression directly.

Crossref and OpenAlex expressions are stored in the auditable form:

```text
query=<free-text query> | filter=<provider API filter>
```

The executor separates these parts and forwards the frozen filter through the
canonical provider orchestrator. This prevents a saved date or language filter
from being displayed in the registry but omitted during the real request.

## Statuses

Provider-native statuses remain visible in the artifact ledger:

- `completed`
- `empty`
- `partial`
- `failed`
- `skipped`

Run-level statuses are:

- `SUCCEEDED`: every requested provider completed or returned an empty result;
- `PARTIAL`: at least one provider succeeded or was partial and another did not;
- `FAILED`: every requested provider failed;
- `CANCELLED`: every requested provider was skipped or none was executable.

## PRISMA preparation

The run manifest stores three different quantities:

- `records_identified_before_deduplication`: rows actually returned and saved;
- `provider_reported_total_found`: total results reported by providers when
  available;
- `prisma_records_identified`: equal to the returned-row count only when the
  frozen strategy version is explicitly PRISMA-eligible.

A `PILOT` version remains auditable but contributes zero to the PRISMA count by
default. These are identification counts only. Deduplication, screening,
eligibility, and inclusion are later stages and must not be inferred here.

## Safety and reproducibility

- executions use immutable version IDs;
- filters for Crossref and OpenAlex are forwarded to the actual request;
- network providers run sequentially through the existing orchestrator;
- checkpoints can be resumed;
- provider errors do not erase successful snapshots from the same run;
- every run has a manifest and every snapshot has a checksum;
- no historical CSV, JSON, JSONL, or registry row is destructively migrated.
