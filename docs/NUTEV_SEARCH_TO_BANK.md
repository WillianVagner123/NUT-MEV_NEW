# NutEV — Saved Search to Evidence Bank

## Purpose

This stage turns a completed web search persisted under `15_web_searches/<search_id>/result.json` into the reusable NutEV Article Workbench without sending tens of thousands of documents to an LLM or downloading every full text.

## Default low-cost flow

```text
persisted web search
  -> verify result.json + search_id
  -> A/B/C/D operational tiering
  -> audited reference_ranking.jsonl
  -> Scientific Export
  -> enrichment with network DISABLED
       |-- use abstract/summary when available
       `-- preserve missing full text as missing
  -> CORE
  -> semantic candidates
  -> EvidenceExcerpt / ResultBundle / ArticleEvidenceCard
  -> hash-verified SQLite Workbench
```

The default materialization makes **zero external LLM calls** and performs **no network full-text retrieval**.

## Tier policy

Tiers are operational processing priorities derived from the already-computed NutEV reading-priority rank:

- A: top 2%;
- B: 2–10%;
- C: 10–40%;
- D: 40–100%.

They are not eligibility decisions, risk-of-bias judgments, quality scores, certainty assessments, EvidenceClaims, recommendations, or PRISMA events.

The point of the tiers is cost control: all references can enter the metadata/abstract Workbench, while later full-text/OCR deepening can focus first on A and then B.

## Run

From the repository root:

```bash
python tools/process_web_search_to_bank.py --search-id <SEARCH_ID>
```

To process the most recent completed persisted web search:

```bash
python tools/process_web_search_to_bank.py
```

In Docker/Hetzner:

```bash
docker exec -it hetzner-nutev-1 \
  python /app/tools/process_web_search_to_bank.py
```

## Outputs

Per-search audit material:

```text
project_output_reference/bank/searches/<search_id>/
  reference_ranking.jsonl
  AUDIT_MANIFEST.json
  BANK_IMPORT_MANIFEST.json
  BANK_PIPELINE_MANIFEST.json
```

Reusable scientific bank:

```text
project_output_reference/scientific/
  document_candidates.jsonl
  evidence_records.jsonl
  enrichment/
  core/
  semantic/
  excerpts/
  workbench/
    evidence_workbench.sqlite
    WORKBENCH_MANIFEST.json
```

The `/articles.html` UI and `/api/articles*` endpoints continue to read only the hash-verified Workbench projection.

## Coverage gaps

Provider failures, unavailability, and non-exhaustive providers from the source search are preserved in the bank import/pipeline manifests. They are never recoded as zero coverage and processing a search does not make it a formal/PRISMA search.

## Future deepening

A later explicit stage may retrieve full text for Tier A/B, run PDF text extraction/OCR, and rebuild the affected scientific objects. It must remain separate from the default low-cost ingestion so a large discovery run cannot accidentally trigger tens of thousands of downloads.
