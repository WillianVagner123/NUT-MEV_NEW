# NutEV PLAY

`nutev play` is the one-command computational orchestrator for the NutEV Evidence Engine.

## Current scope

The first implementation is deliberately **PILOT-only**. It executes the latest registered PILOT strategy (or an explicit `--version-id`), builds the master corpus, resolves lawful open-access full text, downloads accessible artifacts, extracts native text and uses OCR automatically when needed.

It does **not** create human scientific decisions and does not authorize a formal search.

```text
registered PILOT strategy
        ↓
provider execution + immutable snapshots
        ↓
master corpus + deterministic deduplication
        ↓
lawful OA full-text resolution
        ↓
download
        ↓
native-text extraction / OCR when needed
        ↓
12_play/<play_id>/ complete audit summary
```

## Run

Windows PowerShell:

```powershell
.\.venv\Scripts\nutev.exe play --project-root .\project_output_scientific
```

The default requests up to 10,000 records per executable provider and resumes provider checkpoints when available.

Useful options:

```powershell
.\.venv\Scripts\nutev.exe play `
  --project-root .\project_output_scientific `
  --version-id STRATEGY_VERSION_ID `
  --breadth specific `
  --limit 10000 `
  --providers pubmed europepmc crossref openalex
```

Metadata-only test:

```powershell
.\.venv\Scripts\nutev.exe play `
  --project-root .\project_output_scientific `
  --metadata-only
```

## Output

Each invocation creates:

```text
project_output_scientific/
└── 12_play/
    ├── latest_summary.json
    └── play_<timestamp>_<id>/
        ├── play_state.json
        ├── play_summary.json
        ├── play_summary.sha256
        ├── play_summary.md
        ├── search_providers.csv
        ├── fulltext_ledger.jsonl
        ├── download_manifest.jsonl
        ├── download_failures.jsonl
        └── extraction_manifest.jsonl
```

`play_summary.json` is written once and then hashed. Its SHA-256 is stored in the sibling `play_summary.sha256` file, avoiding a circular/self-hash that would invalidate itself when embedded into the JSON being hashed.

The summary makes truncation explicit by comparing provider-reported totals with returned rows. A provider with fewer returned records than `total_found` is marked `truncated=true`; that run must not be described as exhaustive.

## Scientific gate

The current implementation refuses strategy versions that are PRISMA-eligible. This is intentional while GF-02/GF-03/GF-06/GF-07/GF-10 are still being implemented.

A future FORMAL `nutev play` must require recorded authorization for:

- GF-02 sentinel recall + noise validation;
- GF-03 PRESS;
- GF-06 final search date and filters;
- GF-07 human screening setup;
- GF-10 freeze.

No flag should silently bypass those requirements.

## Human boundary

PLAY may retrieve, normalize, deduplicate, resolve, download, extract, OCR, calculate metrics and prepare review queues. It must not silently create `INCLUDE`, `EXCLUDE`, `ADJUDICATED`, PRESS approval, freeze authorization or a final clinical recommendation.

## Full-text boundary

PLAY only attempts lawful open-access resolution and ordinary public retrieval. Paywalls are not bypassed. Unavailable content remains visible as paywall/metadata-only/failure evidence.

## Not integrated yet

The current one-command implementation does not yet merge all methodological tracks into a single master corpus. In particular, Scopus and Web of Science remain manual/licensed execution routes, and institutional/guideline-repository tracks still need the formal registry/gate integration defined for Article 1. These gaps are reported rather than hidden.
