# NutEV CORE Relational Mapping

## Status

This is an additive CORE layer. It is independent from PRISMA and human screening.

Canonical flow:

```text
SEARCH / RANK
  -> science-export
  -> science-enrich (retrieval / OCR)
  -> science-core (macro record / evidence bank)
  -> science-semantic (traceable facts)
  -> science-relations (traceable candidate relations)
  -> relational NutEV bank
       |-- query / synthesis / MEV / maps
       `-- OPTIONAL: human review -> PRISMA
```

## Why this layer exists

A list of facts is not enough for a scientific knowledge base. The bank also needs to know which facts belong together.

Examples:

- which comparator belongs to an intervention arm;
- which effect estimate belongs to an outcome;
- which confidence interval and p-value belong to an effect estimate;
- which timepoint belongs to an outcome or estimate;
- which table or figure reports an outcome.

The relational layer therefore converts traceable `SemanticFactCandidate` objects into traceable `ScientificEntityCandidate` and `ScientificRelationCandidate` objects.

## Command

```bash
nutev science-relations
```

Default inputs:

```text
project_output_reference/scientific/semantic/nutev_core_records_semantic.jsonl
project_output_reference/scientific/semantic/semantic_fact_candidates.jsonl
project_output_reference/scientific/semantic/SEMANTIC_MANIFEST.json
```

Default output:

```text
project_output_reference/scientific/relations/
```

## Integrity gates

`science-relations` fails closed unless:

1. `SEMANTIC_MANIFEST.json` has type `NUTEV_CORE_SEMANTIC_DECONSTRUCTION`;
2. manifest status is `PASS`;
3. semantic CORE record SHA-256 matches the manifest;
4. semantic fact-candidate SHA-256 matches the manifest;
5. every flat semantic fact refers to a known CORE document;
6. embedded semantic fact IDs exactly match the flat fact IDs for each document.

This makes the relationship graph a deterministic derivative of an audited semantic dataset.

## Entities

Current operational entity types include:

- `population`;
- `sample`;
- `study_arm` with role `intervention` or `comparator`;
- `exposure`;
- `outcome`;
- `timepoint`;
- `effect_estimate`;
- `p_value`;
- `confidence_interval`;
- `table`;
- `figure`;
- contextual entities such as objective, eligibility criteria, limitation, funding and conflict of interest.

Where a deterministic parser exists, normalized values are added without removing the original label. Examples:

```json
{"entity_type":"effect_estimate","normalized":{"measure":"OR","value":1.42,"raw":"OR=1.42"}}
```

```json
{"entity_type":"confidence_interval","normalized":{"level":0.95,"lower":1.05,"upper":1.92,"raw":"95% CI 1.05 to 1.92"}}
```

These objects remain machine candidates.

## Relations

Current relation types include:

- `compared_with`;
- `effect_estimate_for`;
- `p_value_for`;
- `confidence_interval_for`;
- `effect_has_p_value`;
- `effect_has_confidence_interval`;
- `measured_at`;
- `estimated_at`;
- `reported_in`.

Every relation preserves:

- source entity ID;
- target entity ID;
- source semantic fact IDs;
- source sentence SHA-256 values;
- locators when available;
- relation basis;
- rule-strength score;
- `status = machine_candidate`.

## Linking hierarchy

### Level 1: same sentence

This is the preferred rule.

If an outcome, OR, CI and p-value originate from the same source sentence, the engine may produce a candidate effect bundle between those objects.

Likewise, an intervention and comparator explicitly represented by semantic facts from the same sentence may produce a `compared_with` relation.

### Level 2: same locator, unique candidates only

A weaker fallback can be used when there is exactly one plausible source and target of the relevant type within a locator.

Example:

```text
Results section:
  exactly one outcome
  exactly one effect estimate
```

A weak `effect_estimate_for` candidate may be produced.

### Ambiguity rule

NutEV must not create the Cartesian product of multiple outcomes and multiple estimates merely because they occur in the same section.

Example:

```text
Outcome A
Outcome B
OR 1.2
```

with different source sentences but the same `Results` locator does **not** justify choosing whether OR 1.2 belongs to Outcome A or Outcome B.

The relationship remains unresolved.

## Relational coverage score

`NUTEV_RELATIONAL_COVERAGE` is a 0-100 technical score with five blocks:

1. entity normalization — 20;
2. study-arm comparison mapping — 20;
3. outcome/time mapping — 20;
4. quantitative estimate bundle — 30;
5. relation provenance — 10.

This score answers:

> How much of the extracted semantic material could NutEV link into traceable, non-ambiguous candidate relationships?

It does **not** answer:

- whether a study is high quality;
- whether the effect is true;
- whether the study is eligible;
- risk of bias;
- certainty of evidence;
- recommendation strength.

## Outputs

The layer generates:

```text
nutev_core_records_relational.jsonl
scientific_entity_candidates.jsonl
scientific_relation_candidates.jsonl
relational_scorecards.jsonl
nutev_relations.sqlite
RELATIONS_MANIFEST.json
```

The macro record moves to schema version 3 and gains a `relational` section.

## SQLite relational bank

`nutev_relations.sqlite` contains:

- `entities`;
- `relations`;
- `relation_meta`.

This allows operational queries such as:

```sql
SELECT *
FROM relations
WHERE relation_type = 'effect_estimate_for';
```

or joins between effect estimates and outcomes through their entity IDs.

The SQLite database is an operational index. JSONL remains the portable/auditable representation.

## Scientific guardrails

1. Entity candidates are not accepted scientific facts.
2. Relation candidates are not accepted `EvidenceClaim` objects.
3. Same-sentence evidence is preferred over section-level inference.
4. Locator fallback requires unique candidate pairs.
5. Relation confidence is rule strength, not a calibrated probability.
6. Missing relationships remain missing rather than being invented.
7. PRISMA remains optional downstream.
8. Ranking remains technical reading priority and must never become scientific quality or eligibility.

## What this enables next

After this contract is stable, NutEV can add higher-resolution parsers while keeping the same provenance model:

- named study arms instead of sentence-level arm descriptions;
- intervention dose, frequency and route;
- outcome instrument/scale;
- explicit timepoint normalization;
- attrition and per-arm sample sizes;
- trial registry/protocol identifiers;
- table-cell extraction;
- outcome/effect/timepoint bundles;
- cross-paper EvidenceSet graphs;
- contradiction and convergence maps.

Human validation can later promote selected candidates into accepted scientific objects without changing the provenance chain.
