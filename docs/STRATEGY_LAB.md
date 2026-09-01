# Article 1 Strategy Lab

`/strategy.html` is the read-only visual surface for the current Article 1 pre-PRESS query architecture.

## Canonical sources

The scientific source of truth remains:

- `config/nutev/article1_query_draft_v1.json` — canonical query draft;
- `config/nutev/article1_search_master_v1.json` / live `SEARCH_STATE.json` — formal-search gate.

`apps/nutev-web/strategy-data/article1_query_draft_v1.json` is only a static web mirror. A contract test requires semantic JSON equality with the canonical config, so it cannot silently diverge.

## What the page shows

- B-NORM blocks and known Scopus/Web of Science candidate strings;
- C1 Care Process, C2 Competency/Literacy, C3 Implementation and C4 Social Context;
- PRESS-only terms and explicit C4 `NOT_APPROVED` state;
- vocabulary decisions (`KEEP`, `TEST IN PRESS`, `DO NOT AUTO-ADD`);
- registered PRESS delta-test plan;
- PRESS, GF-10, query-freeze and formal-search readiness from the live Search State;
- the canonical freeze rule.

## What it does not do

The Strategy Lab has no scientific write action. It does not edit queries, approve PRESS, authorize GF-10, freeze a version, execute provider searches, create eligibility decisions or emit PRISMA events.

The first version intentionally does not fabricate a query-version history. Until an approved/frozen version exists, the UI states that only the current canonical pre-PRESS draft is available.
