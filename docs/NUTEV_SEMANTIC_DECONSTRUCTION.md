# NutEV Semantic Deconstruction

## Status

This is an additive CORE stage. It does not require human screening or PRISMA.

Canonical flow:

```text
SEARCH / RANK
  -> science-export
  -> science-enrich (retrieval / scraping / OCR)
  -> science-core (macro record / local evidence bank)
  -> science-semantic (structured semantic deconstruction)
  -> reusable NutEV knowledge record
       |-- search / classification / synthesis / MEV profiles
       `-- OPTIONAL: human screening -> PRISMA
```

## Why this stage exists

A PDF is not yet a reusable scientific object. The semantic stage converts the extracted article text into small, source-linked candidates that can be indexed, scored, searched, compared, or later validated.

The goal is to make the NutEV CORE useful even when no systematic/scoping review is planned.

## Output macro record v2

`science-semantic` reads the hash-verified CORE records and document enrichments and writes:

- `nutev_core_records_semantic.jsonl`
- `semantic_fact_candidates.jsonl`
- `semantic_scorecards.jsonl`
- `SEMANTIC_MANIFEST.json`

The v2 macro record preserves the original CORE record and adds a `semantic` section.

## Semantic fact candidate

Every `SemanticFactCandidate` contains:

- `field`
- `value`
- `section`
- `locator`
- `source_excerpt`
- `source_sha256`
- `extraction_method`
- `extraction_confidence`
- `status = machine_candidate`

`extraction_confidence` is a rule-strength indicator, not a calibrated scientific probability.

## Fields in rule_v1

The first deterministic extractor supports candidates for:

- objective
- population
- sample size
- intervention
- exposure
- comparator
- outcome
- duration
- follow-up
- effect measure (OR/RR/HR/SMD/MD/IRR/aOR/aRR/beta)
- p-value
- confidence interval
- eligibility criteria
- limitation
- funding
- conflict of interest
- table reference
- figure reference

This list is deliberately extensible.

## PICO / PECO / PCC

Frameworks are emitted only as candidates.

Examples:

- intervention + outcome (+ optional comparator/population) -> `PICO` candidate
- exposure + outcome (+ optional comparator/population) -> `PECO` candidate
- review/synthesis + population, without resolved intervention/exposure -> weak `PCC` candidate with an explicit warning that concept/context are not yet resolved

The engine must not fabricate a missing P/I/E/C/O/C field.

## Semantic coverage score

`NUTEV_SEMANTIC_COVERAGE` is a technical coverage score from 0 to 100.

It evaluates whether traceable candidates exist in five blocks:

1. question and population context — 20
2. design, sample and time — 20
3. intervention/exposure and comparator — 20
4. outcomes and quantitative results — 25
5. limitations and disclosure context — 15

This is **not**:

- evidence quality
- risk of bias
- certainty
- eligibility
- effect credibility
- recommendation strength

It measures only the semantic completeness of the NutEV macro record.

## Relationship with MEV

The semantic facts are designed to become stable inputs for versioned MEV profiles.

NutEV still does not invent MEV blocks or weights. A future canonical MEV profile can reference fields such as:

```text
semantic.field_counts.sample_size
semantic.field_counts.effect_measure
semantic.coverage_score.normalized_score
classification.document_class
acquisition.full_text_status
```

or, in later schema versions, validated semantic facts and claims.

## Relationship with EvidenceClaim

A `SemanticFactCandidate` and a `FindingCandidate` are machine-created reading/indexing objects.

Neither is an accepted `EvidenceClaim`.

A later claim-extraction/validation stage may transform selected source-linked candidates into `EvidenceClaim` only under an explicit provenance and validation contract.

## Relationship with PRISMA

PRISMA remains optional.

The semantic layer does not make include/exclude decisions and does not create PRISMA counts.

A project that needs a formal review can consume the same enriched CORE records and then run reviewer screening/adjudication. A project that only needs evidence mapping, a literature bank, topic analysis, or scientific retrieval can stop at the CORE/semantic layer.

## Integrity rules

`science-semantic` fails closed when:

- CORE records do not match the SHA in `CORE_MANIFEST.json`
- document enrichments do not match the SHA in `ENRICHMENT_MANIFEST.json`
- document ID sets differ
- duplicate/missing document IDs are found

Missing scientific information is never inferred merely to improve coverage scores.

## Next layer

After this deterministic semantic contract is stable, the next extension should be high-recall semantic extraction with the same provenance contract, including:

- normalized population attributes (age/sex/condition/context)
- intervention dose/frequency/intensity
- exposure definitions
- comparator details
- outcome names and instruments
- time points
- table-cell extraction
- arm-level sample sizes
- effect estimates linked to outcomes/time points
- attrition
- protocol/registration identifiers
- funding/COI normalization

An LLM may propose candidates, but it must not bypass source excerpt, locator, hash, extraction method, and validation status.
