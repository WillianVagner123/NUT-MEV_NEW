# NutEV AI Context — shared entrypoint

This file is the neutral entrypoint for ChatGPT/Codex, Claude and other agents working on NutEV.

## Read first

For Article 1 work, read in this order:

1. `AGENTS.md` — repository invariants and scientific guardrails.
2. `ARTICLE1_SEARCH_MASTER.md` — current canonical search status.
3. `config/nutev/article1_search_master_v1.json` — machine-readable search state.
4. `config/nutev/article1_query_draft_v1.json` — current pre-PRESS route/query draft.
5. `docs/ARTICLE1_AGENT_CONTEXT.md` — how to use the live agent bundle.

Claude Code should also read `CLAUDE.md`; it points back to this same source of truth.

## Live production context

After `tools/build_article1_agent_context.py` is run in production, the canonical persistent bundle is:

```text
project_output_reference/agent_context/article1/
  CONTEXT_MANIFEST.json
  SEARCH_STATE.json
  SEARCH_SUMMARY.md
  ARTICLE_SUMMARIES.jsonl
```

`ARTICLE_SUMMARIES.jsonl` is deliberately rank-blind and contains structured article-level context only. It must not contain full text, Bank rank/score/tier, machine relevance score/band, eligibility decisions or PRISMA decisions.

In production the same four safe files can be mirrored to the NutEV static web root. The intended stable URLs are:

- `https://nutev.mindsperformance.com.br/agent-context/article1/CONTEXT_MANIFEST.json`
- `https://nutev.mindsperformance.com.br/agent-context/article1/SEARCH_STATE.json`
- `https://nutev.mindsperformance.com.br/agent-context/article1/SEARCH_SUMMARY.md`
- `https://nutev.mindsperformance.com.br/agent-context/article1/ARTICLE_SUMMARIES.jsonl`

For full Workbench detail of one selected document, use the existing `GET /api/articles/{document_id}` endpoint. Its excerpts/result bundles are machine-index objects, not accepted scientific claims.

## Read-only aggregates over the same bundle

The web tier exposes server-side aggregates computed from the verified bundle, so no client has to
download or re-aggregate it:

- `GET /api/dashboard/overview` — KPIs, class/domain/full-text/route/timeline counts, provenance;
- `GET /api/evidence-map` and `GET /api/evidence-map/cell` — operational-domain × document-class
  matrix and the exact documents behind one cell;
- `GET /api/timeline`, `GET /api/routes/compare`;
- `GET /api/review/status`, `/api/review/queue`, `/api/review/conflicts`, `/api/review/document/{id}`.

All of them are navigation/context. They carry a `guardrail` string and never emit eligibility,
inclusion/exclusion, quality, risk of bias, certainty, recommendation or PRISMA state.

Human review state lives in a separate append-only log
(`project_output_reference/scientific/human_review/article1/`). `REVIEWED` means a human has read the
document; it is not inclusion, and eligibility/screening/PRISMA vocabulary is rejected at write time.
The web tier still cannot approve PRESS, authorize GF-10, freeze a query, execute a formal search or
emit a PRISMA event.

## Current Article 1 boundary

Discovery/harvest and Tier A deepening are technically complete, but the formal systematic-review search is not frozen or executed. PRESS is not yet PASS and GF-10 is not authorized.

Do not call the discovery corpus a final PRISMA search and do not convert routing/profile signals into inclusion or exclusion decisions.

## Good agent behavior

An agent should:

- quote the search id and manifest/hash when making status claims;
- distinguish static repository snapshot from live runtime state;
- prefer runtime manifests when checking mutable production counts;
- expose disagreements or missing files instead of guessing;
- use the agent bundle as navigation/context, not as evidence adjudication;
- preserve the formal-search gate until PRESS + GF-10 + freeze are explicitly recorded.

## Safe prompt starter

A user can tell an agent:

> Read `AI_CONTEXT.md` and `ARTICLE1_SEARCH_MASTER.md`, then use the Article 1 agent-context bundle. Summarize the current scientific state, cite the search/manifests you rely on, and do not treat discovery/ranking/routing as formal inclusion or PRISMA unless the master says the formal gate has been authorized.
