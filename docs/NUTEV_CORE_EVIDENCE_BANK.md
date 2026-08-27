# NutEV CORE Evidence Bank

Status: canonical reusable article-information layer. **PRISMA is optional downstream behavior.**

## Product rule

The NutEV CORE is not a screening pipeline.

Its primary job is to transform every traceable discovered article into one durable, enriched, queryable scientific-information record that can be reused across projects, reviews, teaching, evidence maps, article writing, and future NutEV products.

The canonical flow is:

```text
SEARCH / DISCOVERY
  -> NORMALIZE / TRACEABILITY / DEDUPE / RANK
  -> science-export
  -> DocumentCandidate + EvidenceRecord
  -> science-enrich
  -> retrieval / scraping / PDF / HTML / XML / OCR
  -> DocumentEnrichment + ReviewerDossier
  -> science-core
  -> NutEVCoreRecord
  -> NutEV evidence bank
```

After the CORE record exists, optional workflows may consume it:

```text
NutEVCoreRecord
  |---> query / classification / evidence mapping / writing support
  |---> project-specific synthesis
  |---> MEV scorecard when a versioned MEV profile exists
  `---> OPTIONAL human screening -> PRISMA
```

Human screening is therefore **not required to create or keep a CORE record**.

## Command

After `science-export` and `science-enrich`:

```bash
nutev science-core
```

Default inputs:

```text
project_output_reference/scientific/document_candidates.jsonl
project_output_reference/scientific/evidence_records.jsonl
project_output_reference/scientific/SCIENTIFIC_EXPORT_MANIFEST.json
project_output_reference/scientific/enrichment/full_text_artifacts.jsonl
project_output_reference/scientific/enrichment/document_enrichments.jsonl
project_output_reference/scientific/enrichment/reviewer_dossiers.jsonl
project_output_reference/scientific/enrichment/ENRICHMENT_MANIFEST.json
```

Default output:

```text
project_output_reference/scientific/core/
```

## The macro document: `NutEVCoreRecord`

Each article receives one canonical macro record.

### 1. Identity

```text
title
DOI
PMID
URL
year
source provider
```

### 2. Bibliographic layer

```text
abstract
journal
authors
article type
keywords
```

### 3. Reference-engine layer

The CORE preserves previous technical information without confusing it with scientific quality:

```text
reference_rank
reference_score
reference_tier
reference_taxonomy
audit traceability
```

Guardrail:

> Reference ranking is technical reading priority, not scientific quality.

### 4. Provenance

```text
EvidenceRecord ID
source provider
source run ID
origin SHA-256
source manifests and hashes
```

### 5. Acquisition / scraping / OCR

```text
FullTextArtifact ID
retrieval status
source URL
media type
artifact SHA-256
retrieved_at
extraction method
OCR used
OCR engine
text SHA-256
text length
warnings
```

The CORE consumes the `science-enrich` retrieval/extraction layer rather than creating a second scraper.

### 6. Structure

```text
section coverage
section map
block count
table mentions
figure mentions
sample-size mentions
```

Typical detected coverage:

```text
abstract
introduction/background
methods
results/findings
discussion
conclusion
references
```

### 7. Classification

The first classifier is intentionally conservative and traceable.

Possible index classes include:

```text
primary_randomized
primary_observational
primary_qualitative
evidence_synthesis
review
guidance
unclassified
```

It also preserves:

```text
recorded article type
study-design candidates
topic terms
sample-size mentions
section coverage
```

These labels are indexing aids, not eligibility or quality decisions.

## Main findings

The CORE can generate `FindingCandidate` objects from high-information sections such as:

```text
Results
Findings
Conclusion
Discussion
```

A candidate stores:

```text
finding ID
document ID
section
locator
short source excerpt
SHA-256 of the source sentence
importance score
machine-detected finding signals
status = machine_candidate
```

The machine importance score is only a prioritization heuristic for indexing/reading. A `FindingCandidate` is **not** automatically an `EvidenceClaim`.

A future semantic extraction layer may convert selected candidates into structured claims with population/intervention/exposure/comparator/outcome and human validation.

## Scores

### CORE readiness score

NutEV always calculates a transparent technical `NUTEV_CORE_READINESS` score from 0 to 100.

Its blocks are:

```text
1. Identity and traceability       20
2. Document access and extraction 20
3. Structural mapping             20
4. Classification metadata        20
5. Finding traceability           20
```

This score answers:

> "How complete and traceable is this NutEV article record?"

It does **not** answer:

```text
Is the study high quality?
Is risk of bias low?
Should it be included in a review?
Is certainty high?
Should a clinical recommendation be made?
```

### MEV scores

The repository currently has no canonical definition of the user's MEV blocks/weights.

NutEV therefore does not invent them.

Without a profile:

```json
{
  "mev": {
    "status": "not_scored",
    "reason": "no versioned MEV profile supplied"
  }
}
```

When the canonical MEV specification exists, pass a versioned JSON profile:

```bash
nutev science-core --mev-profile config/mev_v1.json
```

Example profile shape:

```json
{
  "profile_id": "MEV_CANONICAL",
  "version": "1.0.0",
  "semantic_kind": "mev_scientific_score",
  "blocks": [
    {
      "id": "example_block",
      "label": "Example block",
      "max_score": 10,
      "rules": [
        {
          "field": "classification.section_coverage.has_methods",
          "operator": "truthy",
          "points": 3
        }
      ]
    }
  ]
}
```

Supported first-version operators:

```text
present
truthy
equals
contains
count_gte
numeric_gte
```

The profile ID, version, block scores and rationale remain stored with the record.

## Evidence-bank outputs

`science-core` generates:

```text
nutev_core_records.jsonl
finding_candidates.jsonl
scorecards.jsonl
nutev_core.sqlite
CORE_MANIFEST.json
```

### JSONL

Canonical portable representation for audit, versioning, bulk processing and future migration.

### SQLite

Operational local bank containing:

```text
core_records
finding_candidates
scorecards
bank_meta
```

This is intentionally a local portable foundation, not a claim that SQLite is the final production database.

The same stable record schema can later be indexed in Postgres/Supabase, a document store, a search engine, or a vector index without changing the scientific meaning of the record.

## Relationship to the reviewer dossier

`ReviewerDossier` and `NutEVCoreRecord` have different purposes.

### ReviewerDossier

Blinded decision-support view. It deliberately hides NutEV rank/taxonomy so the reviewer is not biased by the engine.

### NutEVCoreRecord

Internal canonical knowledge record. It may preserve reference rank/taxonomy because the bank needs the complete provenance/history of the object.

The UI must choose the appropriate view for the workflow.

## Relationship to PRISMA

PRISMA is an optional downstream projection.

```text
CORE exists
   |
   +-- no systematic/scoping review needed -> stop here / reuse bank
   |
   `-- review project requires formal screening
          -> ReviewerDossier
          -> human assessments/adjudication
          -> final ScreeningDecision
          -> PRISMA events/counts
```

No PRISMA event is created simply because an article entered the CORE.

## Future semantic layer

The next logical extension after this CORE contract is validated semantic extraction, for example:

```text
population
intervention/exposure
comparator
outcomes
study design
sample size
duration/follow-up
eligibility criteria
main results
effect measures
limitations
funding/conflicts
tables/figures
```

Every extracted semantic value should keep:

```text
source document
source locator
source text hash
extraction method
machine/human provenance
validation status
```

That layer should enrich the CORE without making PRISMA mandatory and without silently converting machine output into accepted scientific claims.
