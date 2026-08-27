# NutEV Status-Aware Discovery

## Purpose

NutEV scientific audit must never interpret a provider failure as scientific absence.

Legacy provider helpers are retained for compatibility with existing UI/scripts, but some of them historically return `[]` both when a search succeeds with zero records and when a remote request fails after retries.

The status-aware discovery layer introduces the explicit `ProviderResult` contract for active topic/competency search.

---

## Status contract

Every executable status-aware provider returns one of:

### `completed`

The bounded request completed successfully and returned one or more records.

### `empty`

The provider responded successfully and the verified result set for the request contains zero records.

This is the **only** state that may be described as a successful zero-hit response.

### `failed`

No trustworthy provider result was obtained.

`total_found` remains unknown unless a prior verified provider response supplied it.

A failed request must never become `0`.

### `partial`

One or more result pages were obtained and a later request failed before the bounded request completed.

Already retrieved rows are preserved and explicitly marked as partial execution.

Partial is not complete evidence coverage.

### `skipped`

The provider was deliberately not executed, for example because network execution was disabled.

A skipped provider must never become `0`.

---

## Executable providers

The active Topic / Competency Engine can now execute with explicit status:

- PubMed / MEDLINE;
- Europe PMC;
- OpenAlex;
- Crossref;
- DOAJ;
- Semantic Scholar.

The following remain plan-only until an equally explicit status adapter exists:

- LILACS / BVS;
- SciELO.

The following remain manual/licensed and are never simulated:

- Scopus;
- Web of Science.

---

## Compatibility

Existing list-returning functions remain available:

- `search_europepmc(...)`;
- `search_openalex(...)`;
- `search_crossref(...)`;
- `search_doaj(...)`;
- `search_semantic_scholar(...)`.

The new scientific active-search path uses status-aware clients instead. This avoids breaking existing web/search workflows while strengthening the scientific audit contract.

---

## Active topic search

`nutev science-topics --execute-search` now promotes the status-aware providers to:

`EXECUTABLE_STATUS_AWARE`

and records a run row for every provider/topic pair.

Each run preserves:

- topic ID;
- provider;
- provider-native query;
- status;
- explicit error, when applicable;
- `total_found` when the provider supplies it;
- `total_returned`;
- provider metadata;
- checkpoint path when supported;
- `feeds_prisma=false`;
- `auto_ingest=false`.

---

## Discovery result policy

Every returned row is still only a `discovery_candidate`.

A status-aware search result must return through the normal NutEV path:

```text
provider result
 -> normalize
 -> traceability gate
 -> deduplicate
 -> classify
 -> rank
 -> audit
 -> scientific export
 -> enrich / OCR
 -> CORE
 -> semantic
 -> relations
 -> topic / competency audit
```

It is never inserted directly into the CORE bank merely because an active search found it.

It never feeds PRISMA directly.

---

## Scientific interpretation rules

The engine MAY state:

- a provider returned zero hits successfully;
- a provider failed;
- a provider was skipped;
- only part of a bounded request was retrieved;
- a provider returned N records;
- a topic search has incomplete provider coverage.

The engine MUST NOT state:

- `failed = 0 articles`;
- `skipped = 0 articles`;
- `partial = complete search`;
- an unavailable provider proves an evidence gap;
- discovery result count is evidence strength;
- search result rank is scientific quality;
- a discovery result belongs in PRISMA without the formal review pipeline.

---

## Provider-specific mechanics

### Europe PMC

Uses cursor-based pagination and preserves provider `hitCount` when available.

### OpenAlex

Uses cursor pagination and provider metadata `count` when available.

### Crossref

Uses bounded offset pagination and `total-results` when available.

### DOAJ

Uses bounded page pagination and provider `total` when available.

### Semantic Scholar

Uses bounded offset pagination and provider `total` when available.

If a later page fails after rows were retrieved, status is `partial` rather than silently returning a normal list as if the request were complete.

---

## Manifest

When status-aware active search is executed, `TOPIC_AUDIT_MANIFEST.json` records:

- execution contract version;
- status-aware providers;
- plan-only providers;
- manual/licensed providers;
- per-status run counts;
- per-provider run counts;
- assertion that `empty` is distinct from failure;
- assertion that results remain discovery candidates.

The hashes of the updated search plan, run ledger and discovery results are recalculated after execution.

---

## Relationship to Longitudinal Watch

The Watch Engine consumes verified topic-audit state. Provider status matters because an API outage must not create a false longitudinal signal such as:

- apparent disappearance of evidence;
- false drop to zero documents;
- false coverage regression;
- false active-search escalation.

Status-aware discovery is therefore a prerequisite for trustworthy longitudinal monitoring.
