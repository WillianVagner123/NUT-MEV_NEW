# Article 1 — Search Master

**Canonical status:** `DISCOVERY_CLOSED_FORMAL_SEARCH_PENDING_PRESS_FREEZE`

This is the main human-readable control file for the Article 1 search. For machine-readable state use `config/nutev/article1_search_master_v1.json`. For AI/agent access start at `AI_CONTEXT.md`.

## Research question

> Quais parâmetros nutricionais, competências alimentares e contextos sociais da alimentação são atualmente recomendados, estruturados e utilizados por diretrizes e modelos operacionais para orientar avaliação, aconselhamento, prescrição e monitoramento alimentar aplicáveis à Medicina do Estilo de Vida?

## What is already closed

The broad discovery/harvest stage is technically complete and persisted under search id:

`web_20260830T182743+0000_91bde5be`

Production snapshot verified by the operator on 2026-08-30:

- 41,139 records before deduplication;
- 33,839 unique references in the discovery corpus;
- 33,067 structurally accepted records and 772 structurally quarantined records;
- Tier A: 662/662 documents deepened;
- Tier A retrieval: 504 `retrieved`, 90 `partial`, 68 `not_retrieved`;
- 594/662 (89.73%) retrieved or partially retrieved;
- deepening integrity audit: PASS, 27 v3 batches, 662 rank coverage, 459 SHA-256 artifacts checked, 0 errors, 0 warnings;
- Workbench: 33,067 articles, 42,847 evidence excerpts and 36,648 result bundles;
- Article 1 rank-blind routes: B-NORM 85, C-STRUCT 316, union 351, overlap 50, unrouted 311;
- vocabulary audit completed: 27 B-NORM and 49 C-STRUCT phrases surfaced for human strategy review.

These values describe discovery, retrieval and reviewer-navigation infrastructure. They are **not** scientific inclusion counts and are **not** a PRISMA search result.

## Search architecture

### B-NORM

Purpose: retrieve normative nutrition guidance, guidelines, consensus and professional/scientific statements.

Current status: `CANDIDATE_FOR_PRESS`.

The candidate provider drafts already documented for Scopus and Web of Science remain in `config/nutev/article1_query_draft_v1.json`.

### C-STRUCT

Purpose: retrieve operational structures relevant to the research question without building one giant noisy OR block.

Current subroutes:

1. `C1-CARE-PROCESS` — Nutrition Care Process, models/pathways of care, MNT, prescription/counseling and professional care structures.
2. `C2-COMPETENCY-LITERACY` — food/nutrition/culinary literacy, food skills, competencies, food agency and professional competencies.
3. `C3-IMPLEMENTATION` — implementation/dissemination/quality-improvement and monitoring structures.
4. `C4-SOCIAL-CONTEXT` — social context/determinants, social and food environment, social support, commensality and family/shared meals **only as a PRESS candidate**.

`C4-SOCIAL-CONTEXT` is not yet approved for the formal strategy.

## What is deliberately NOT closed

The formal systematic-review search has **not** been executed.

Current gate state:

- PRESS record: not yet PASS;
- GF-10: not authorized;
- provider-specific query freeze: not complete;
- formal provider search: not executed;
- PRISMA formal-search event: not emitted.

Therefore no agent, reviewer or manuscript may describe the discovery corpus as the final formal systematic-review search.

## Remaining search gate

Before formal execution:

1. PRESS review of B-NORM and C1–C4;
2. delta tests for PRESS-only terms/routes;
3. sentinel/known-item recovery check;
4. provider-specific field/truncation/syntax review;
5. incremental-yield and noise review;
6. explicit `PRESS = PASS` record;
7. explicit GF-10 authorization;
8. versioned provider-query freeze with checksums;
9. only then run `FORMAL` searches and create PRISMA search events.

## Canonical artifacts

Repository:

- `config/nutev/article1_search_master_v1.json` — machine-readable master state;
- `config/nutev/article1_query_draft_v1.json` — pre-PRESS query draft;
- `config/nutev/topic_profiles/article1_prefreeze_v1.json` — pre-freeze topic/competency registry;
- `docs/ARTICLE1_QUERY_DRAFT_PRESS.md` — query-draft rationale;
- `docs/ARTICLE1_ROUTE_REVIEW_QUEUES.md` — B-NORM/C-STRUCT route contract;
- `docs/ARTICLE1_VOCABULARY_AUDIT.md` — vocabulary-audit contract;
- `AI_CONTEXT.md` — shared ChatGPT/Claude entrypoint.

Production runtime authorities:

- `project_output_reference/scientific/deepening/<search_id>/tier-A/DEEPENING_MANIFEST.json`;
- `project_output_reference/scientific/review_queue/<search_id>/tier-A/REVIEW_QUEUE_MANIFEST.json`;
- `project_output_reference/scientific/review_routes/<search_id>/article1/ROUTE_QUEUE_MANIFEST.json`;
- `project_output_reference/scientific/review_routes/<search_id>/article1/VOCABULARY_AUDIT.json`;
- `project_output_reference/scientific/workbench/WORKBENCH_MANIFEST.json`;
- `project_output_reference/agent_context/article1/CONTEXT_MANIFEST.json` after the agent-context bundle is generated.

## Scientific boundaries

Never infer any of the following from the current search infrastructure alone:

- bank presence = inclusion;
- Tier A/B/C/D = evidence quality or risk of bias;
- structural quarantine = scientific exclusion;
- route membership = eligibility;
- machine relevance = accepted evidence;
- full-text retrieval = inclusion;
- discovery counts = PRISMA counts;
- excerpts/result bundles = accepted EvidenceClaims.

When runtime data and this static snapshot disagree, inspect the runtime manifest and report the discrepancy instead of silently overwriting history.
