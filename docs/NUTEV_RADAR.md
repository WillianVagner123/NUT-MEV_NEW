# NutEV Radar

## Purpose

NutEV Radar is the visual operational layer for the verified Topic / Competency / Audit and Longitudinal / Watch outputs.

It answers:

- what topics and competencies are currently mapped in the bank;
- how many unique documents are mapped at least once;
- which providers are represented in current topic coverage;
- which technical gaps are active;
- which topics require active search;
- what the last status-aware provider runs reported;
- what changed in the latest verified Watch comparison;
- which Watch cases require human review.

It does **not** grade evidence quality, certainty, consensus, causality or recommendation strength.

---

## Route

Start the ordinary NutEV web server:

```bash
python apps/nutev-web/server.py
```

Open:

```text
http://127.0.0.1:8765/radar.html
```

The main NutEV sidebar also links directly to **NutEV Radar**.

---

## API

The page consumes one read-only endpoint:

```text
GET /api/radar
```

There is no Radar POST action in this version. Opening or refreshing the dashboard cannot change scientific state, execute a formal review, accept evidence or feed PRISMA.

---

## Canonical inputs

By default the server reads:

```text
project_output_reference/scientific/topics/TOPIC_AUDIT_MANIFEST.json
project_output_reference/scientific/watch/WATCH_MANIFEST.json
```

The topic manifest resolves and verifies:

- `topic_audits.jsonl`;
- `topic_assignments.jsonl`;
- `active_search_plan.json`;
- `active_search_runs.jsonl`;
- the versioned topic/competency profile.

The Watch manifest, when present, resolves and verifies:

- `WATCH_SNAPSHOT.json`;
- `watch_events.jsonl`;
- `watch_cases.jsonl`.

Every displayed scientific artifact must match the SHA-256 recorded by its manifest. A mismatch blocks the Radar instead of showing stale or tampered values.

---

## No synthetic dashboard data

If the canonical topic audit does not exist, the Radar shows **Radar ainda sem snapshot** and the commands needed to generate scientific outputs.

It does not populate demonstration counts.

If the topic audit exists but fails integrity checks, `GET /api/radar` returns a conflict response and the UI shows **Radar bloqueado**.

---

## Summary semantics

### Tópicos / competências

Number of audited registry units currently present in `topic_audits.jsonl`.

### Documentos únicos

Number of distinct `document_id` values across verified topic assignments.

This is intentionally different from the number of assignments. One document may map to several topics.

### Providers observados

Distinct providers represented in the current topic-audit coverage.

### Tópicos com gaps

Number of audited topics with at least one current technical audit flag.

### Busca ativa requerida

Number of topics where the Topic / Competency Engine currently sets `active_search_required=true`.

These are operational counts, not evidence strength.

---

## Topic dossier

Each topic/competency card exposes:

- registry label and stable topic ID;
- kind: topic, competency, context or implementation;
- current P1/P2/P3/P4 audit priority;
- mapped document count;
- provider count and provider identities;
- latest publication year;
- full-text mapping count and ratio;
- semantic-deconstruction count and ratio;
- relational-mapping count and ratio;
- current audit flags;
- provider-by-provider active-search run status;
- provider-native query from the reproducible search plan;
- latest attached Watch events and cases when current.

A query can be copied from the dossier, but the Radar does not auto-ingest its results.

---

## Provider state

The provider board summarizes statuses recorded by the active-search ledger.

Examples:

- `completed`;
- `empty` — verified successful zero-hit response;
- `failed`;
- `partial`;
- `skipped`;
- `planned_not_executed`.

Scopus and Web of Science remain manual/licensed and are presented as such. They are never simulated and a missing licensed execution is never rendered as `0`.

---

## Watch freshness contract

The Radar compares the SHA-256 of the current topic-audit manifest with the topic-audit SHA recorded in the Watch manifest.

### Same SHA

The Watch is current and its events/cases may be attached to the current topic cards.

### Different SHA

The Radar marks **Watch desatualizado**.

Historical Watch events/cases remain visible in the longitudinal section, but they are not attached to the current topic cards because they describe an older verified audit state.

This prevents an old delta from being presented as a current topic change.

---

## Priority semantics

Topic audit priorities remain:

- `P1_HIGH` — no documents;
- `P2_MEDIUM` — low volume or stale/unknown recency;
- `P3_LOW` — other technical completeness gaps;
- `P4_MONITOR` — no current audit gap.

Radar labels them explicitly as **fila de auditoria / busca**. They are not GRADE, risk of bias, certainty or recommendation strength.

Watch cases remain a separate W1/W2/W3 human-review queue.

---

## Guardrails

Radar MAY display:

- verified counts;
- topic coverage;
- technical completeness ratios;
- provider status;
- gap flags;
- active-search priorities;
- verified longitudinal changes;
- review-required Watch cases.

Radar MUST NOT infer:

- stronger evidence from more documents;
- consensus from provider diversity;
- importance from recency;
- retraction from a removed mapping;
- eligibility from topic assignment;
- clinical recommendation from audit state;
- PRISMA inclusion from discovery/watch output.

PRISMA remains optional and downstream.
