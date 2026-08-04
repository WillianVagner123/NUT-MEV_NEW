# Search Corpus Normalization and Deduplication

## Purpose

This stage converts the immutable provider snapshots from one registered search run into an auditable bibliographic corpus. It does not execute a new search and it never reads the current dashboard query. The only inputs are the snapshots already linked to a frozen `run_id`.

## Input integrity

Before processing, every provider JSONL is checked against the SHA-256 stored in `search_execution_artifacts`. A missing, malformed, or modified snapshot fails the corpus build and records the failure in SQLite.

## Output location

Each build has a unique append-only directory:

```text
<project_root>/03_corpus/search_processed/
└── <version_id>/
    └── <run_id>/
        └── <build_id>/
            ├── normalized_records.jsonl
            ├── master_records.jsonl
            ├── metadata_master.csv
            ├── dedup_decisions.csv
            ├── duplicate_candidates.csv
            ├── prisma_identification.json
            └── corpus_manifest.json
```

The run-specific `metadata_master.csv` is compatible with the existing NutEV metadata exporter. This stage does not overwrite the historical project-level metadata file.

## Normalization

Each source row receives a stable `source_record_id` based on the immutable run, provider artifact, source row number, and original JSON content. The stage normalizes:

- DOI;
- PMID;
- PMCID;
- URL;
- title for matching;
- year;
- authors;
- publication metadata;
- provider and retrieval provenance.

The original provider fields remain available in `normalized_records.jsonl`.

## Automatic deduplication

Records are joined transitively through exact normalized identifiers, in this order of preference:

1. DOI;
2. PMID;
3. PMCID;
4. URL.

Transitive matching means that a DOI/PMID record can join a PMID/PMCID record, which can in turn join a PMCID-only record. One master document is produced for the complete connected component.

The retained row is selected by metadata completeness, abstract length, full-text URL strength, and provider priority. Missing fields are supplemented from duplicate rows. Provider provenance and source record IDs are unioned.

Every source record receives one auditable decision:

- `RETAINED`;
- `AUTO_DUPLICATE`.

The decision includes the master `document_id`, match type, match value, and confidence.

## Title and year candidates

An exact normalized title and year match without a shared strong identifier is not removed automatically. The records remain separate master documents and are written to `duplicate_candidates.csv` with:

- `PENDING_HUMAN_REVIEW`;
- low confidence;
- a shared possible-duplicate group.

This prevents an uncertain title match from silently reducing the PRISMA count.

## PRISMA identification metrics

`prisma_identification.json` records:

- records identified before deduplication;
- exact duplicates removed automatically;
- records after automatic deduplication;
- possible duplicates pending human review;
- the equivalent PRISMA counts when the strategy version is eligible.

Pilot searches remain fully auditable but contribute zero to PRISMA.

This stage does not claim that title/abstract screening, full-text eligibility, or final inclusion has occurred.

## SQLite ledger

The existing search registry database receives additive tables:

- `search_corpus_builds`;
- `search_dedup_decisions`;
- `search_duplicate_candidates`.

No historical table is removed or destructively migrated.

## Dashboard workflow

In **Search Strategy → Executar uma versão registrada**:

1. execute a frozen strategy version;
2. select a completed run;
3. click **Normalizar e deduplicar esta execução**;
4. inspect input, unique, removed, possible-duplicate, and PRISMA metrics;
5. open the generated metadata and manifest paths.
