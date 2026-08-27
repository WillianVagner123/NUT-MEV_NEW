# NutEV Pre-Screening Document Enrichment

Status: reviewer-support stage executed **before any scientific screening decision is imported**.

The purpose of this stage is to give the reviewer more document-level information without allowing NutEV ranking, taxonomy, or machine inference to become an inclusion/exclusion decision.

## Canonical order

```text
REFERENCE DISCOVERY / RANKING
  -> science-export
  -> DocumentCandidate / EvidenceRecord
  -> science-enrich
  -> FullTextArtifact
  -> text extraction / OCR
  -> DocumentEnrichment
  -> ReviewerDossier
  -> human screening / adjudication
  -> science-screening
```

A final screening decision should normally not be imported unless a verified `ReviewerDossier` exists for that document.

## Command

Default, offline/controlled mode:

```bash
nutev science-enrich
```

This uses recorded bibliographic metadata and any supplied local assets. If no full text exists, NutEV creates an explicit `abstract_only` dossier when an abstract is available.

To provide local full text or a known full-text URL, create a JSONL file such as:

```json
{"document_id":"doi:10.1000/example","path":"C:/articles/example.pdf","media_type":"application/pdf","scope":"full_text"}
```

or:

```json
{"document_id":"pmid:12345678","url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/","scope":"full_text"}
```

Then run:

```bash
nutev science-enrich \
  --assets-jsonl project_output_reference/scientific/full_text_assets.jsonl
```

Network retrieval is opt-in:

```bash
nutev science-enrich --allow-network
```

When network retrieval is enabled and no explicit asset is supplied, the command may attempt the `DocumentCandidate.url`. A generic publisher/DOI HTML page is treated as `partial` unless the route clearly represents full text (for example PDF or PMC).

## Extraction cascade

NutEV attempts the following paths without silently pretending one succeeded:

```text
plain text
HTML
XML/JATS-like text
PDF native text layer (pdftotext)
OCR fallback (pdftoppm + tesseract)
abstract-only fallback
unavailable
```

For PDFs:

1. if `pdftotext` is available, NutEV first extracts the native text layer;
2. if the native layer is absent/too short, NutEV attempts OCR;
3. OCR requires both `pdftoppm` and `tesseract` in `PATH`;
4. `NUTEV_OCR_LANG` controls Tesseract languages and defaults to `eng`;
5. missing OCR tools, failed pages, or unreadable files are recorded as warnings rather than fabricated text.

Example for English + Portuguese when those language packs are installed:

```bash
set NUTEV_OCR_LANG=eng+por
nutev science-enrich --assets-jsonl project_output_reference/scientific/full_text_assets.jsonl
```

## What is extracted for the reviewer

The enrichment stage builds a document map including:

- bibliographic identifiers already known to NutEV;
- title, year, journal, authors and article type when present;
- recorded abstract;
- full-text retrieval status;
- extraction method;
- whether OCR was used and which engine was used;
- extracted-text character count and SHA-256;
- detected section headings;
- section previews with locators;
- table and figure mentions;
- `n=` sample-size mentions;
- machine-detected study-design phrases;
- frequent content terms;
- explicit extraction warnings.

These are **reading aids**, not scientific judgments.

## Reviewer blindness

`ReviewerDossier` deliberately excludes:

```text
reference_rank
reference_score
reference_tier
NutEV taxonomy assignments
inclusion probability
quality score
recommendation
```

The dossier carries explicit guardrails:

```text
blind_to_nutev_rank = true
blind_to_nutev_taxonomy = true
machine_signals_are_not_screening_decisions = true
missing_content_is_not_inferred = true
```

This preserves the existing NutEV principle that system rank/taxonomy must not leak into a blinded human judgment.

## Outputs

Default location:

```text
project_output_reference/scientific/enrichment/
```

Files:

```text
full_text_artifacts.jsonl
document_enrichments.jsonl
reviewer_dossiers.jsonl
enrichment_events.jsonl
ENRICHMENT_MANIFEST.json
private_assets/
private_text/
```

`private_assets/` and `private_text/` are execution artifacts, not publication outputs.

## Copyright / redistribution rule

NutEV may process text that the user is lawfully able to access for private review. The system must not assume that extracted full text can be redistributed.

The enrichment manifest therefore treats extracted full text as a private execution artifact. Do not publish or redistribute full copyrighted text unless the source license permits it.

## Current limits

This first implementation does not yet claim to provide:

- validated PICO/PECO/PCC extraction;
- validated named-entity recognition for population/intervention/outcome;
- table-cell reconstruction;
- figure image understanding;
- OCR confidence calibration across engines/languages;
- automatic inclusion/exclusion;
- risk-of-bias judgments;
- `EvidenceClaim` extraction.

Those should be added as explicit, separately validated layers rather than hidden inside the dossier builder.
