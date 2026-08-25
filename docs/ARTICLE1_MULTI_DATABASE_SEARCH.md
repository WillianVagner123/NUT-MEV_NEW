# Article 1 multi-database search

Status: operational pre-freeze workflow.

## Purpose

`/full-search.html` gives Article 1 one canonical keyword profile and deterministic database-specific projections without collapsing B-NORM and C-STRUCT into one Boolean route.

The screen is designed to remove manual copy/paste drift while preserving the scientific gates already defined in the CONTROL CENTER.

## Source of truth

- PubMed B-NORM uses the exact `B-NORM-PUBMED v0.7` strategy stored in the PRESS package.
- PubMed C-STRUCT uses the exact `C-STRUCT-PUBMED v0.5.1` strategy stored in the PRESS package.
- LILACS/BVS and SciELO use the canonical regional query already defined for GF-01.
- Scopus and Web of Science use the provider-native translations recorded in the Article 1 formal-search plan; they remain manual/licensed and are never simulated.
- Europe PMC, OpenAlex, Crossref, DOAJ and Semantic Scholar are discovery/QA providers in this workflow, not automatic formal-PRISMA replacements for protocol databases.

## Canonical keyword families

The profile records condition-neutral families for:

1. nutrition/diet core;
2. normative/guideline markers;
3. care architecture;
4. food/culinary competence;
5. professional nutrition competence;
6. structural/document qualifiers;
7. implementation/monitoring;
8. dietary patterns/approaches and orienting qualifiers.

The multi-database compiler does not add disease names, known sentinel text, or retrospective terms based on observed results.

## Validation semantics

`PASS_STATIC` means only that the generated query is non-empty, within local size limits, structurally balanced, does not leak PubMed tags to other providers, and contains the expected provider-native wrapper for PubMed/Scopus/WoS/regional routes.

It does **not** mean the remote provider accepted the query, that the route is exhaustive, or that coverage is scientifically sufficient. Remote acceptance is established only by real execution and its audit artifacts.

## Execution classes

### PREFLIGHT

The screen can run all connected providers in three auditable route jobs:

- B-NORM;
- C-STRUCT;
- B-SUPP SciELO.

PREFLIGHT is intentionally bounded to 25 records per provider and up to 300 rendered results. It validates transport and provider behavior without generating PRISMA counts.

### FORMAL

Formal execution is fail-closed. The Article 1 profile currently carries `gf10_authorized: false`, so the FORMAL button remains disabled.

After GF-10 is explicitly authorized, the profile may be versioned to `gf10_authorized: true`. Only then may the screen issue 0/0 exhaustive jobs for the connected formal routes. The formal run still requires review of provider gaps, search details, exports and the formal search log before PRISMA use.

## Manual/licensed databases

Scopus and Web of Science queries are rendered with provider-native syntax and a copy button. If institutional access is unavailable, they remain documented as unavailable/licensed and are not replaced by another source. If access is available, the exact query must be executed in the licensed interface and the export/date/count preserved.

## Audit rule

A database marked unavailable, failed or non-exhaustive is never recoded as zero. Discovery-only sources remain separate from the formal Article 1 corpus unless the protocol is prospectively amended before formal execution.
