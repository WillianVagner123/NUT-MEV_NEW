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

After `tools/build_article1_agent_context.py` is run in production, the canonical live bundle is:

```text
project_output_reference/agent_context/article1/
  CONTEXT_MANIFEST.json
  SEARCH_STATE.json
  SEARCH_SUMMARY.md
  ARTICLE_SUMMARIES.jsonl
```

`ARTICLE_SUMMARIES.jsonl` is deliberately rank-blind and contains structured article-level context only. It must not contain full text, Bank rank/score/tier, machine relevance score/band, eligibility decisions or PRISMA decisions.

When the production web endpoint is available, use:

- `GET /api/agent-context/article1` — current context/search state;
- `GET /api/agent-context/article1/articles?limit=50&offset=0` — paged structured article summaries;
- optional filters: `route`, `document_class`, `q`.

For full Workbench detail of one document use the existing `GET /api/articles/{document_id}` endpoint. Its excerpts/result bundles are machine-index objects, not accepted scientific claims.

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
