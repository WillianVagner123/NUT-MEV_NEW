# NutEV Topic / Competency / Audit Engine

## Status

This document defines the active topic/competency audit layer of the NutEV CORE.

The layer is **independent of PRISMA**. It exists to keep the NutEV evidence bank aware of what it knows, what it does not know, what is stale, and which topics or competencies deserve a new search.

Topic assignments, competency assignments, audit priorities, and active-search results are machine aids. They are not eligibility decisions, evidence quality, risk-of-bias judgements, certainty ratings, causal conclusions, clinical recommendations, or PRISMA events.

---

## Architectural analogy with PINGO

The useful part of the PINGO architecture is not the athlete-specific content. It is the separation of responsibilities:

`raw data -> context -> orchestrator -> specialist engines -> cross engine -> standardized result -> decision/audit -> output policy`

NutEV follows the same systems logic:

```text
1. SCIENTIFIC INPUT
   articles / guidelines / statements / standards / grey literature

2. NUTEV EVIDENCE CONTEXT
   identity / provider / date / document class / full text / provenance

3. NUTEV ORCHESTRATOR
   search -> normalize -> traceability -> enrich/OCR -> CORE -> semantic -> relations

4A. DOCUMENT ENGINES
   provider search / retrieval / OCR / structure / semantic extraction

4B. TOPIC + COMPETENCY ENGINE
   versioned topic registry
   versioned competency registry
   lexical/structured mapping to the evidence bank

4C. LONGITUDINAL / FRESHNESS ENGINE
   publication years
   provider diversity
   latest evidence date
   stale/unknown topic coverage

5. CROSS / AUDIT ENGINE
   topic x provider
   topic x document type
   topic x competency
   topic x full text
   topic x semantic coverage
   topic x relational coverage
   gap detection

6. STANDARDIZED AUDIT RESULT
   topic assignments
   competency assignments
   topic coverage
   audit flags
   active-search priorities
   reproducible provider queries

7. AUDIT DECISION
   What is covered?
   What is missing?
   Is the evidence recent enough?
   Is source diversity adequate?
   Is the content only metadata/abstract or full text?
   Has it been semantically deconstructed?
   Are scientific relations available?
   Does the topic require active search?

8. OUTPUT POLICY
   MAY:
   - classify/index topics and competencies;
   - surface coverage gaps;
   - generate an active-search plan;
   - execute status-aware discovery searches;
   - request human taxonomy validation;
   - monitor topic freshness.

   MAY NOT:
   - treat lexical topic assignment as scientific truth;
   - infer a missing competency;
   - call provider failure "zero results";
   - turn active-search results directly into evidence-bank truth;
   - feed active-search results directly into PRISMA;
   - generate clinical recommendations without downstream scientific/human validation.

9. PRODUCT OUTPUTS
   topic dashboard / competency map / audit cases / active-search queue /
   article dossier / future watcher / optional human review / optional PRISMA
```

---

## Core object: Topic Registry

Topics and competencies are not hard-coded into Python.

They live in a versioned JSON registry:

```json
{
  "profile_kind": "NUTEV_TOPIC_COMPETENCY_REGISTRY",
  "profile_id": "...",
  "version": "...",
  "status": "PREFREEZE | CANONICAL",
  "formal_gate": {"authorized": false},
  "topics": []
}
```

Each definition has:

- `id`;
- `label`;
- `kind`: `topic`, `competency`, `context`, or `implementation`;
- `terms`;
- optional `anchor_terms`;
- optional `qualifier_terms`;
- query mode;
- enabled state.

A profile cannot claim `CANONICAL` status unless its formal gate is explicitly authorized.

---

## Article 1 bootstrap profile

`config/nutev/topic_profiles/article1_prefreeze_v1.json`

This profile reuses the vocabulary already proposed for Article 1 and is deliberately marked `PREFREEZE` because GF-10 has not been authorized.

Initial blocks:

- nutrition core;
- normative guidance and standards;
- structural nutrition care;
- food/culinary competencies;
- professional nutrition competencies;
- implementation/monitoring;
- dietary orientation/patterns.

This is a bootstrap search/audit registry, **not yet an official NutEV competency ontology**.

---

## Topic / competency assignment

`science-topics` reads schema-v3 relational CORE records and searches traceable record surfaces:

- title;
- abstract;
- keywords;
- semantic facts;
- relational entity labels.

A match becomes `TopicAssignment(status=machine_candidate)`.

The technical `lexical_match_score` means only how many registered terms were detected. It is not scientific importance, quality, certainty, relevance, or recommendation strength.

---

## Topic audit

For each registered topic/competency, the engine reports:

- number of mapped documents;
- provider diversity;
- full-text availability;
- semantic deconstruction availability;
- relational mapping availability;
- latest publication year;
- gap flags;
- active-search priority.

Current flags:

- `no_documents`;
- `low_document_count`;
- `low_provider_diversity`;
- `stale_or_unknown_recency`;
- `no_full_text`;
- `semantic_incomplete`;
- `relational_incomplete`.

Priority:

- `P1_HIGH`: no documents;
- `P2_MEDIUM`: low volume or stale coverage;
- `P3_LOW`: other technical completeness gaps;
- `P4_MONITOR`: no current gap flag.

Priority is a **search/audit priority**, not an evidence grade.

---

## Active search

The engine generates a reproducible search plan for every registered topic.

Providers represented in the plan:

- PubMed;
- Europe PMC;
- OpenAlex;
- Crossref;
- DOAJ;
- Semantic Scholar;
- LILACS/BVS;
- SciELO;
- Scopus;
- Web of Science.

### Execution policy v1

PubMed may be executed by `science-topics --execute-search` because `PubMedClient` exposes explicit provider status (`completed`, `partial`, `failed`, `skipped`, `empty`).

The current Europe PMC/OpenAlex/Crossref/DOAJ/Semantic Scholar helper functions return lists and may collapse remote failure into an empty list. They therefore remain `PLAN_ONLY_STATUS_ADAPTER_REQUIRED` in this scientific audit path until they expose an explicit `ProviderResult`-style status contract.

Scopus and Web of Science remain `MANUAL_LICENSED` and are never simulated.

LILACS/BVS and SciELO remain in the plan but require a status-aware connector integration in the CORE search package before automatic execution here.

This is intentional fail-closed behaviour: provider failure must not be reported as `0` scientific results.

---

## Active-search ingestion policy

An active-search hit is only a discovery candidate.

It does **not** automatically enter:

- the NutEV evidence bank;
- accepted EvidenceClaims;
- scientific synthesis;
- PRISMA.

It must return through the ordinary pipeline:

```text
ACTIVE SEARCH RESULT
  -> NORMALIZE
  -> TRACEABILITY GATE
  -> DEDUPLICATE
  -> CLASSIFY / RANK
  -> SCIENTIFIC EXPORT
  -> ENRICH / OCR
  -> CORE
  -> SEMANTIC
  -> RELATIONS
  -> TOPIC AUDIT
```

This creates a closed learning/search loop without bypassing provenance controls.

---

## CLI

Plan/audit only:

```bash
nutev science-topics \
  --relational-records-jsonl project_output_reference/scientific/relations/nutev_core_records_relational.jsonl \
  --relations-manifest project_output_reference/scientific/relations/RELATIONS_MANIFEST.json \
  --topic-profile config/nutev/topic_profiles/article1_prefreeze_v1.json \
  --output-dir project_output_reference/scientific/topics
```

Execute status-aware PubMed discovery as well:

```bash
nutev science-topics \
  --execute-search \
  --limit 20
```

---

## Outputs

- `topic_assignments.jsonl`
- `topic_audits.jsonl`
- `active_search_plan.json`
- `active_search_runs.jsonl`
- `active_search_results.jsonl`
- `TOPIC_AUDIT_MANIFEST.json`

All outputs remain under project output paths and preserve explicit guardrails.

---

## What is still needed after this layer

1. Promote the Article 1 topic profile from `PREFREEZE` only after scientific review/GF-10 authorization.
2. Add explicit status-aware adapters for Europe PMC, OpenAlex, Crossref, DOAJ and Semantic Scholar.
3. Add LILACS/BVS and SciELO status-aware CORE connectors.
4. Add version/change monitoring so a topic can detect newly published or changed guidance since the last verified run.
5. Add topic-cross-topic convergence/conflict maps using accepted or human-validated claims; machine relations alone must not be called scientific consensus.
6. Build the UI equivalent of the PINGO audit panel: topic state, gap reason, last search, provider status, evidence-bank coverage, and action required.
7. Keep PRISMA optional and downstream.
