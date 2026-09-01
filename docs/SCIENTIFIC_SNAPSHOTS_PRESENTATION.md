# Scientific Snapshot + Presentation View v2

This layer makes the current Article 1 dashboard state reproducible and presentation-ready without mutating scientific state.

## Snapshot contract

`apps/nutev-web/scientific-snapshot.js` builds a browser-side snapshot from the same safe, canonical surfaces already used by the NutEV Article 1 workspace:

- `SEARCH_STATE.json`;
- `CONTEXT_MANIFEST.json`;
- `ARTICLE_SUMMARIES.jsonl`;
- the exact static mirror of `article1_query_draft_v1.json` used by Strategy Lab;
- `build-info.json`.

The builder computes SHA-256 for every source file with Web Crypto and derives `snapshot_id` from a stable canonical JSON representation of the scientific/operational state. `generated_at` is metadata and is deliberately excluded from the identity hash, so the same source state receives the same snapshot ID.

The snapshot contains safe metadata and aggregates only. It does not contain protected full text, Bank rank/score/tier, machine relevance scores, accepted EvidenceClaims, eligibility decisions, RoB, certainty or recommendations.

Downloading the JSON creates the immutable artifact. The public web app does not expose a write endpoint for snapshots, so an unauthenticated visitor cannot fill the server disk.

## Build provenance

The production Docker build now accepts `NUTEV_BUILD_COMMIT`. The Hetzner deploy workflow passes the already-verified `TARGET_SHA`, and container startup writes only that SHA to `apps/nutev-web/build-info.json`. `.git` remains excluded from the image.

For a manual build use:

```bash
docker build \
  --build-arg NUTEV_BUILD_COMMIT="$(git rev-parse HEAD)" \
  -f deploy/hetzner/Dockerfile \
  -t "$IMAGE" .
```

A development fallback `build-info.json` contains `development` and is overwritten at container startup.

## Presentation View v2

`/presentation.html` is a five-screen narrative:

1. Scientific Question;
2. Corpus;
3. Evidence Landscape;
4. B-NORM × C-STRUCT;
5. Formal Search Readiness.

The presentation is built from a scientific snapshot and therefore displays the snapshot ID, build commit and generation time. Arrow keys and PageUp/PageDown navigate. Fullscreen is optional.

`Exportar / PDF` calls the browser print dialog. The print stylesheet renders every presentation screen as a separate page. NutEV does not fabricate a PDF binary server-side.

## Scientific boundary

A snapshot records a state; it does not approve that state. In particular:

- snapshot != PRISMA;
- discovery != formal search;
- route membership != inclusion;
- retrieval/full-text status != eligibility;
- document count != strength/certainty;
- machine profile != risk of bias;
- the presentation cannot approve PRESS, authorize GF-10, freeze a query or execute a provider search.
