# Article 1 Agent Context Bundle

The agent-context bundle is a deterministic, read-only summary layer over the verified Article 1 production artifacts. It exists so ChatGPT/Codex, Claude and other agents can retrieve the current scientific/technical state without reconstructing it from chat history or scanning unrelated files.

## Canonical location

```text
project_output_reference/agent_context/article1/
  CONTEXT_MANIFEST.json
  SEARCH_STATE.json
  SEARCH_SUMMARY.md
  ARTICLE_SUMMARIES.jsonl
```

Build it with:

```bash
python tools/build_article1_agent_context.py \
  --search-id web_20260830T182743+0000_91bde5be \
  --output-root project_output_reference
```

The command verifies the active Workbench database/hash and the Article 1 route outputs before materializing the bundle.

## Files

### `CONTEXT_MANIFEST.json`

Machine entrypoint. Records context version, source manifests/hashes, counts and hashes of every generated output.

### `SEARCH_STATE.json`

Compact current state for the search: master status, formal-search gate, Workbench state, Tier A deepening state, route counts and vocabulary-audit state.

### `SEARCH_SUMMARY.md`

Human/LLM-readable summary of the same state. It intentionally distinguishes discovery/harvest from formal PRISMA search.

### `ARTICLE_SUMMARIES.jsonl`

One rank-blind structured record per Tier A article. It contains only safe navigation context:

- document id;
- title/year/DOI/PMID/provider;
- document class and full-text status;
- reference stub;
- B-NORM/C-STRUCT route membership;
- selected review-profile fields (document-shape confidence, operational domains and warnings);
- counts of evidence excerpts/result bundles.

It deliberately omits:

- full text;
- Bank rank/score/tier;
- machine relevance score/band;
- eligibility/inclusion/exclusion decisions;
- quality, risk-of-bias or certainty judgments;
- recommendations;
- PRISMA events.

## Web access

When the bundle exists in production, the NutEV web service exposes only this safe context layer:

```text
GET /api/agent-context/article1
GET /api/agent-context/article1/articles?limit=50&offset=0
```

Supported article filters are `route`, `document_class` and `q`. The endpoint is read-only and page-limited. It never returns protected full text.

For a specific document's existing Workbench detail, use `/api/articles/{document_id}`. Evidence excerpts and result bundles returned there remain machine/index artifacts, not accepted EvidenceClaims.

## Authority and staleness

`ARTICLE1_SEARCH_MASTER.md` and `config/nutev/article1_search_master_v1.json` are the repository-level control files. Mutable production claims must be checked against the live context/underlying runtime manifests.

If the static master and live runtime differ, an agent must report the discrepancy. It must not silently rewrite scientific history or infer that a new formal search occurred.

## Scientific boundary

The bundle is context infrastructure only. Its existence or completeness does not authorize GF-10, freeze a query, execute a formal systematic-review search or create a PRISMA event.
