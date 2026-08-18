# Article 1 — Open-database strategy after Scopus/Web of Science unavailability

Status: **methodological implementation decision — pre-FREEZE / non-PRISMA**.

## Decision

For the current Article 1 execution environment, **Scopus and Web of Science are not operationally available because licensed access is unavailable**. They must therefore not remain represented as if execution were merely waiting to happen, and they must never be simulated through another provider.

The search architecture is reorganized into complementary tracks:

### Primary bibliographic route

- PubMed/MEDLINE — canonical biomedical indexed route and current GF-02 strategy-validation target.
- LILACS/BVS — native regional health-information route queried through the official BVS search interface.

### Native regional supplementary route

- SciELO — queried through the official SciELO article-search interface, rather than the historical Crossref DOI-prefix approximation.

### Open supplementary discovery routes

- Europe PMC;
- OpenAlex;
- Crossref;
- DOAJ;
- Semantic Scholar;
- declared web-search providers when configured.

These supplementary routes increase discovery sensitivity and metadata reconciliation. **They are not claimed to be methodological equivalents or replacements for Scopus/Web of Science.**

### Normative/grey-literature route

Official organizations, professional societies, guideline repositories and declared institutional web sources remain independent tracks because Article 1 targets normative documents that may never be represented adequately by journal-indexing databases.

## Scientific boundary

The change does **not** authorize FORMAL identification or PRISMA accounting. Until the protocol strategy is PRESS-reviewed, applicable gates are resolved, and GF-10 FREEZE binds the final strategy/configuration/software SHA, all new open-source collection remains `REAL_DISCOVERY_NONFORMAL` or PILOT as explicitly declared.

## Provenance requirements for LILACS/BVS and SciELO

Every live native execution must preserve, at minimum:

- provider identity;
- exact query;
- exact search URL;
- timestamp;
- HTTP outcome;
- raw official search HTML where legally retainable;
- SHA-256 of the raw capture;
- parsed discovery candidates separately from the raw authority;
- parser status/failure;
- explicit `formal_execution_authorized=false` and `prisma_eligible=false` before FREEZE.

A parser failure is **not zero results**. If a website changes layout, the raw capture and failure record remain the audit evidence.

## Current software implementation

`tools/run_latin_sources.py` implements the native LILACS/BVS and SciELO discovery layer. `RODAR_TUDO.cmd` invokes this layer after the general automated collection and before deterministic post-processing/OCR.

The native layer intentionally does not infer eligibility, inclusion, PRESS approval, FREEZE, PRISMA state, or ABCD coding.

## Manuscript-facing reporting

The eventual Methods section should report the databases and routes actually executed. Scopus/Web of Science should be described only as unavailable licensed databases if that remains true at FREEZE; they must not appear in the executed-source list or PRISMA identification counts.

The limitation should be explicit: open bibliographic/discovery routes broaden retrieval but do not establish equivalence to proprietary citation indexes.
