# NutEV Scientific Object Model

Status: additive architecture for the next scientific layer. It does not change the published Reference Engine 1.0.0 contract.

## Rule

Model scientific meaning directly. Do not create generic manager/handler/strategy hierarchies when a scientific entity or plain function is sufficient.

The core composition is:

```text
ResearchQuestion
  -> EvidenceConstraint
  -> SearchCase
  -> DocumentCandidate
  -> EvidenceRecord
  -> FullTextArtifact
  -> DocumentEnrichment
  -> ReviewerDossier
  -> ScreeningDecision
  -> EvidenceClaim
  -> ClaimEvaluation
  -> EvidenceSet
  -> RecommendationCandidate
  -> HumanValidation
```

`ScientificEvent` records explicit lifecycle facts. PRISMA-style counts are views derived from those events, not a second hand-maintained truth source.

## Boundary with the Reference Engine

Current Reference Engine:

```text
SEARCH -> NORMALIZE -> TRACEABILITY GATE -> DEDUPLICATE -> CLASSIFY -> RANK -> EXPORT -> AUDIT
```

The scientific layer begins downstream of traceable reference discovery. Ranking remains reading priority. It is not screening, risk of bias, certainty, synthesis, or clinical recommendation.

The integrated scientific flow is now intended to be:

```text
REFERENCE DISCOVERY
  -> traceable DocumentCandidate / EvidenceRecord
  -> full-text retrieval / OCR / document enrichment
  -> rank- and taxonomy-blind ReviewerDossier
  -> human scientific screening
  -> claim extraction
  -> claim evaluation
  -> evidence grouping and synthesis
  -> recommendation candidate
  -> human validation
```

No later stage may silently upgrade an earlier technical score or machine-detected content signal into a scientific judgment.

## Entities

### ResearchQuestion

Owns the scientific question and optional framework fields (PICO, PECO, PCC, etc.).

### EvidenceConstraint

Owns an explicit scientific constraint such as population, intervention/exposure, comparator, outcome, date range, language, or design restriction.

### SearchCase

One provider-specific executable search case linked to a `ResearchQuestion` and its constraints.

Different search variants are separate `SearchCase` objects rather than anonymous `query_v1`, `query_v2`, etc. Metadata may preserve strategy version, database syntax, date, and execution settings.

### DocumentCandidate

Represents a discovered bibliographic object before scientific extraction. Provider identity and traceable identifiers remain explicit.

### EvidenceRecord

The auditable bridge between the Reference Engine and the scientific layer. It preserves source provider, source run, origin hash, taxonomy, and other provenance required to trace the object back to collection outputs.

### FullTextArtifact

Represents the material actually available for document processing: local PDF/text/HTML/XML, retrieved web material, or an explicit unavailable/not-retrieved state.

It records retrieval status, source URL, local path, media type, SHA-256 and retrieval metadata. A missing article is represented as missing; the engine does not synthesize a substitute full text.

### DocumentEnrichment

Machine-generated reading support built before screening.

It records the extraction method, text hash/length, whether OCR was used, extracted blocks/sections, content signals, warnings and private execution paths. It may use native text, HTML/XML extraction, PDF text extraction, OCR, or an abstract-only fallback.

Machine signals are not eligibility, quality, certainty, or inclusion decisions.

### ReviewerDossier

The reviewer-facing document map generated from `DocumentCandidate + DocumentEnrichment`.

It can expose bibliographic metadata, abstract, full-text availability, extraction/OCR status, section map/previews, table/figure mentions, sample-size mentions, study-design phrases and frequent content terms.

It deliberately does **not** expose NutEV ranking or taxonomy to the reviewer:

```text
blind_to_nutev_rank = true
blind_to_nutev_taxonomy = true
```

This prevents retrieval/ranking output from becoming circular evidence for the human screening decision.

### ScreeningDecision

Represents the final resolved human/external screening decision for one document and stage. The standard CLI flow requires a verified reviewer dossier before importing the decision.

### EvidenceClaim

The smallest scientific evidence unit in this model.

An article is not treated as one indivisible conclusion. A document may support multiple distinct claims, each with its own statement, locator, optional short quote, population, intervention/exposure, comparator, outcome, evidence type, and provenance through `EvidenceRecord`.

A claim must not exist without `evidence_record_id`.

### ClaimEvaluation

Stores explicit evaluation dimensions for one claim. The model does not prescribe a single methodology. Dimensions may later include risk-of-bias domains, directness, precision, applicability, or project-specific judgments.

Automated values must remain distinguishable from human judgments through metadata/assessor conventions.

### EvidenceSet

Groups claim IDs around a scientific question, domain, outcome, contradiction, or evidence lens. It references claims rather than copying them.

Examples:

```text
protein_ffm
food_guidelines
behavior_implementation
GLP1_food_noise
```

A claim may participate in more than one evidence set when scientifically justified.

### RecommendationCandidate

A proposed statement supported by one or more `EvidenceSet` objects. It is explicitly a candidate until validation is completed.

No ranking score or single claim can automatically become an accepted recommendation.

### HumanValidation

Explicit review gate for claims, evaluations, evidence sets, syntheses, or recommendation candidates. Decisions are `pending`, `accept`, `reject`, or `revise`.

### ScientificEvent

Append-only lifecycle fact for a scientific entity. The event records entity, action, optional state transition, reason, timestamp, and metadata.

Events are the source for derived workflow views such as PRISMA counts.

## PRISMA rule

PRISMA is derived, not manually maintained as independent state.

Examples of explicit actions:

```text
identified
duplicate_removed
screened
excluded_screening
sought_for_retrieval
not_retrieved
assessed_for_eligibility
excluded_full_text
included
```

`derive_prisma_counts()` counts only events that exist. Missing workflow events remain zero/unknown; the engine must not infer screening or eligibility from ranking, taxonomy, OCR, or content signals.

Exclusion reasons belong on their corresponding events and should later support reason-specific PRISMA reporting.

## Composition over duplicate pipelines

Prefer:

```text
one DocumentCandidate
  -> one auditable EvidenceRecord
  -> one or more traceable document artifacts
  -> one reviewer-safe enrichment view
  -> many EvidenceClaim
  -> many EvidenceSet views
```

Avoid separate copies of the same article for each article/review/project when identity and provenance can be preserved through links and project-specific scientific objects.

## Search-space semantics

A scientific search space should be represented by explicit `EvidenceConstraint` values and resolved into concrete `SearchCase` objects.

Conceptually:

```text
SearchSpace / constraints
  population = [overweight, obesity]
  intervention = [LCD, VLCD]
  outcome = [FFM, LM]
  date = [2000+, 2010+]

          resolve
             |
             v
SearchCase A
SearchCase B
SearchCase C
...
```

The current implementation deliberately does not add a `SearchSpace` class until executable resolution semantics are specified. `EvidenceConstraint` + `SearchCase` provide the stable minimum contract without decorative abstraction.

## Lenses

A lens is currently stored as a meaningful value on `EvidenceSet`, not as an abstract class hierarchy.

Examples:

```text
food_guidelines
clinical_guidelines
dietary_intervention
behavior_implementation
```

If a future lens requires actual behavior, introduce a concrete implementation with an explicit scientific warrant. Do not create `AbstractLens` solely for taxonomy.

## Non-goals of the current layer

This layer does not claim to implement:

- automatic formal screening decisions;
- validated PICO/PECO/PCC extraction;
- table-cell reconstruction;
- figure image interpretation;
- risk-of-bias instruments;
- GRADE;
- meta-analysis;
- automatic full-text `EvidenceClaim` extraction;
- clinical recommendation generation;
- automatic human adjudication;
- a complete PRISMA 2020 renderer.

Those features must be implemented as explicit downstream behavior and tested independently.

## Compatibility

The published v1.0.0 snapshot and its Zenodo DOI are immutable. New scientific-layer behavior is additive development for a future release. Existing Reference Engine ranking semantics remain unchanged.
