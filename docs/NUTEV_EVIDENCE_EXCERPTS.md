# NutEV Evidence Excerpts & Result Bundles

## Purpose

This stage converts the already enriched/semantic NutEV CORE into a compact evidence packet per article.

It exists for two reasons:

1. expose short, source-linked scientific excerpts and principal results in the Article Workbench;
2. prevent future synthesis/LLM workflows from repeatedly sending entire PDFs or full extracted texts.

The stage is deterministic by default and performs **zero external LLM calls**.

## Canonical flow

```text
SEARCH / RANK
  -> science-export
  -> science-enrich / OCR
  -> science-core
  -> science-semantic
  -> science-excerpts
       |-- evidence_excerpts.jsonl
       |-- result_bundles.jsonl
       |-- article_evidence_cards.jsonl
       `-- EXCERPT_MANIFEST.json
  -> optional relations / topics / Watch / Workbench / human review
```

`science-excerpts` does not replace semantic or relational extraction. It compacts already traceable source material into a small reusable reading/synthesis object.

## EvidenceExcerpt

Each selected excerpt preserves:

- `document_id`;
- kind: `objective`, `method`, `main_result`, `secondary_result`, `conclusion`, `limitation`, or `disclosure`;
- section;
- locator;
- short verbatim excerpt;
- SHA-256 of the excerpt;
- source sentence SHA-256 when available;
- source FindingCandidate/SemanticFactCandidate IDs;
- semantic fields represented by the sentence;
- deterministic priority score;
- title/DOI/PMID/provider/reference stub;
- `status = machine_candidate`.

The excerpt is capped at 420 characters. Full extracted article text remains private execution material and is not copied into this stage.

## ResultBundle

A ResultBundle is created from selected result excerpts. Facts sharing the same source-sentence SHA are linked without inference.

A bundle can contain:

- outcome candidates;
- effect measures such as OR/RR/HR/beta;
- confidence intervals;
- p-values;
- table references;
- figure references;
- exact result excerpt;
- locator/reference;
- main-result vs secondary-result status.

A missing value stays missing. The engine never manufactures an outcome, comparator, confidence interval, p-value, direction, causal interpretation, or scientific conclusion merely to complete the bundle.

`ResultBundle.status = machine_candidate_not_evidence_claim`.

## ArticleEvidenceCard

One compact card is created per document.

It contains:

- article identity and deterministic reference stub;
- document class and full-text status;
- compact study snapshot from existing semantic facts;
- IDs of selected excerpts and result bundles;
- a curated `llm_context`;
- token/cost policy;
- workflow/guardrails;
- deterministic cache key.

The card is the preferred future input to a synthesis model. The model should not receive the full article by default.

## Token/cost policy

Default policy:

```text
full text -> deterministic extraction only
semantic facts -> deterministic
excerpt selection -> deterministic
result bundling -> deterministic
article card -> deterministic
LLM calls -> 0
```

The compact `llm_context` is capped at 6,000 characters per article.

If a future LLM stage is added, its default input must be:

```text
article_evidence_card.llm_context
```

not the PDF/full text.

The card cache identity is based on:

```text
extractor version + document_id + extracted-text SHA-256
```

The whole stage also reuses an existing output when the semantic input hashes, extractor version, and output hashes all still match.

## Selection policy

The deterministic v1 selector caps each article at approximately:

- 1 objective excerpt;
- 3 method/context excerpts;
- 5 result excerpts;
- 1 conclusion excerpt;
- 2 limitation excerpts;
- 1 disclosure excerpt.

Within a category, result/findings sections and quantitative source signals receive higher reading priority.

The first selected result is labeled `main_result`; the remaining selected results are `secondary_result` candidates. This is reading priority, not an accepted scientific hierarchy.

## Reference policy

The stage preserves DOI and PMID and builds a deterministic reference stub from available authors/title/journal/year.

The stub is explicitly marked:

```text
deterministic_stub_not_journal_style
```

It is not claimed to be Vancouver, APA, ABNT, or a journal-specific citation format. Formatting into a target style belongs to an export layer.

## Integrity

`science-excerpts` fails closed when:

- the semantic manifest is not PASS;
- semantic CORE or semantic-fact hashes do not match the semantic manifest;
- a semantic record lacks `document_id`;
- duplicate document IDs exist;
- a fact references an unknown document;
- a fact lacks source excerpt or source hash;
- cached outputs do not match their recorded hashes.

## Scientific guardrails

EvidenceExcerpt and ResultBundle are machine-created reading/indexing objects.

They are not:

- accepted EvidenceClaims;
- eligibility decisions;
- risk-of-bias judgments;
- certainty assessments;
- causal interpretations;
- recommendations;
- PRISMA events.

A later `ClaimCandidate -> human validation -> EvidenceClaim` workflow may consume these objects, but claim promotion must remain explicit.

## CLI

```bash
nutev science-excerpts
```

Defaults:

```text
semantic records  project_output_reference/scientific/semantic/nutev_core_records_semantic.jsonl
semantic facts    project_output_reference/scientific/semantic/semantic_fact_candidates.jsonl
semantic manifest project_output_reference/scientific/semantic/SEMANTIC_MANIFEST.json
output            project_output_reference/scientific/excerpts/
```

## Workbench contract

The future high-scale Article Workbench should use:

- `article_evidence_cards.jsonl` for list/detail summaries;
- `evidence_excerpts.jsonl` for quote/source panels;
- `result_bundles.jsonl` for structured principal-results panels.

The Workbench should fetch one article/card at a time or server-side filtered pages. It must not load tens of thousands of complete article records into the browser.
