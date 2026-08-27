# NutEV Longitudinal / Watch Engine

## Status

This document defines the longitudinal monitoring layer of the NutEV CORE.

The Watch Engine compares **verified topic/competency audit snapshots over time**. Its purpose is to detect changes in the operational evidence-bank state: new mapped documents, changes in provider diversity, freshness, full-text availability, semantic/relational coverage, audit flags and active-search priority.

The Watch Engine is independent of PRISMA. A longitudinal change is an operational difference between two verified NutEV audit states. It is **not** a scientific claim, evidence-quality judgment, certainty rating, eligibility decision, retraction claim, causal conclusion or clinical recommendation.

---

## Place in the NutEV CORE

```text
SEARCH / DISCOVERY
  -> NORMALIZE / TRACEABILITY / DEDUPE / RANK
  -> SCIENTIFIC EXPORT
  -> ENRICH / OCR
  -> CORE MACRO RECORD
  -> SEMANTIC DECONSTRUCTION
  -> SCIENTIFIC RELATIONS
  -> TOPIC / COMPETENCY AUDIT
  -> LONGITUDINAL / WATCH
       |-- verified snapshot
       |-- change events
       |-- review cases
       `-- next-search / re-audit action

OPTIONAL DOWNSTREAM:
  -> human review
  -> formal review workflow
  -> PRISMA
```

The Watch Engine consumes the Topic / Competency / Audit Engine outputs. It does not bypass the ordinary NutEV evidence pipeline.

---

## Command

First baseline:

```bash
nutev science-watch \
  --topic-audits-jsonl project_output_reference/scientific/topics/topic_audits.jsonl \
  --topic-assignments-jsonl project_output_reference/scientific/topics/topic_assignments.jsonl \
  --topic-audit-manifest project_output_reference/scientific/topics/TOPIC_AUDIT_MANIFEST.json \
  --output-dir project_output_reference/scientific/watch
```

Subsequent comparison:

```bash
nutev science-watch \
  --previous-snapshot previous/WATCH_SNAPSHOT.json \
  --previous-watch-manifest previous/WATCH_MANIFEST.json \
  --output-dir project_output_reference/scientific/watch
```

`--previous-snapshot` and `--previous-watch-manifest` must be supplied together. The previous snapshot hash is verified against its watch manifest before comparison.

---

## Verified snapshot

`WATCH_SNAPSHOT.json` is a compact longitudinal representation of one verified topic-audit run.

Per topic or competency it stores:

- topic ID and kind;
- mapped document count;
- exact mapped document IDs;
- provider count and providers;
- full-text count;
- semantic-deconstruction count;
- relational-mapping count;
- latest publication year;
- current audit flags;
- active-search priority;
- whether active search is currently required.

It also stores the registry profile identity/version/status used by the topic audit.

The snapshot is intentionally smaller than the full evidence bank. It is a **state vector for longitudinal comparison**, not a replacement for article records, evidence claims or source documents.

---

## Integrity contract

Before a snapshot can be created, the engine verifies:

1. `TOPIC_AUDIT_MANIFEST.json` is a passing `NUTEV_TOPIC_COMPETENCY_AUDIT` manifest;
2. `topic_audits.jsonl` SHA-256 matches the manifest;
3. `topic_assignments.jsonl` SHA-256 matches the manifest;
4. every assignment references a known audited topic;
5. each topic's `document_count` matches its unique assignment count.

When comparing with a previous run, the engine additionally verifies the previous `WATCH_SNAPSHOT.json` SHA-256 against the previous `WATCH_MANIFEST.json`.

Mismatch is fail-closed.

---

## Baseline semantics

The first verified run has no prior state.

It creates:

- one `baseline_created` event;
- a verified snapshot;
- no change-review case.

Baseline creation must not be interpreted as evidence growth or improvement.

---

## Registry comparability

Longitudinal trends are only meaningful when the registry context is comparable.

### Same profile ID and version

`comparability = full`

Topic-level changes may be compared directly.

### Same profile ID, different version

`comparability = limited_profile_version_changed`

The engine records a registry-version event and still reports topic differences, but those differences require interpretation because vocabulary/rules may have changed.

### Different profile ID

`comparability = incompatible`

The engine emits `profile_changed` and **does not produce direct topic trend claims**. A human must review the registry change before interpreting longitudinal deltas.

This prevents taxonomy changes from being misreported as scientific change.

---

## Watch events

Events are deterministic machine-operational differences between verified snapshots.

### Registry events

- `profile_changed`
- `profile_version_changed`
- `profile_status_changed`

### Topic membership events

- `topic_added`
- `topic_removed`

### Document mapping events

- `document_added`
- `document_removed`

A document removal means only that the document is no longer mapped in the current verified audit state. It does **not** mean retraction, invalid evidence or exclusion.

### Coverage-metric events

- `document_count_changed`
- `provider_count_changed`
- `full_text_count_changed`
- `semantic_count_changed`
- `relational_count_changed`

### Provider events

- `provider_added`
- `provider_removed`

### Freshness event

- `latest_year_changed`

A more recent latest year is operational freshness advancement. It does not mean stronger evidence.

### Gap events

- `flag_added`
- `flag_resolved`

### Search-priority events

- `priority_escalated`
- `priority_deescalated`
- `priority_changed`

The priority is an audit/search priority, never an evidence grade.

---

## Watch cases

Events may create review cases.

### W1_HIGH — profile change

`PROFILE_CHANGE_REVIEW`

Action:

`review_registry_change_before_interpreting_longitudinal_deltas`

### W1_HIGH — coverage regression

`COVERAGE_REGRESSION_REVIEW`

Examples:

- document mapping decreased;
- provider diversity decreased;
- full-text/semantic/relational coverage decreased;
- new audit gap flag appeared;
- active-search priority escalated.

Action:

`review_coverage_change_and_reaudit_topic`

### W2_MEDIUM — new material

`NEW_MATERIAL_REVIEW`

Examples:

- new mapped document;
- new topic;
- new provider;
- publication freshness advanced.

Action:

`review_new_material_through_normal_nutev_core_pipeline`

### W3_LOW — gap resolution

`GAP_RESOLUTION_REVIEW`

Action:

`confirm_operational_gap_resolution`

All cases require review. None auto-accepts evidence and none feeds PRISMA.

---

## Outputs

- `WATCH_SNAPSHOT.json`
- `watch_events.jsonl`
- `watch_cases.jsonl`
- `WATCH_MANIFEST.json`

`WATCH_MANIFEST.json` records source hashes, comparability, event/case counts and guardrail assertions.

---

## Output policy

The Watch Engine MAY:

- report that a new document is mapped to a topic;
- report that provider diversity changed;
- report that latest publication year advanced or receded;
- report that a technical coverage gap appeared or was resolved;
- escalate a topic for new search/re-audit;
- create a human review case;
- compare topic-audit state over time when registry context is comparable.

The Watch Engine MAY NOT:

- call a new document important merely because it is new;
- call a removed mapping a retraction;
- call increased document count stronger evidence;
- infer consensus from document volume;
- infer causality from longitudinal evidence-bank change;
- convert watch events into accepted EvidenceClaims;
- auto-accept search results;
- feed watch events or cases directly into PRISMA;
- generate clinical recommendations from watch state alone.

---

## Scientific role

The Watch Engine answers operational questions such as:

- What changed since the last verified NutEV audit?
- Did a topic gain new mapped material?
- Did source diversity improve or regress?
- Has the topic's evidence-bank freshness advanced?
- Did a previous coverage gap resolve?
- Did a new gap appear?
- Does the topic need an active search or human re-audit?

It does not answer by itself:

- Is the new study valid?
- Is the evidence high quality?
- Is the result clinically important?
- Is there scientific consensus?
- Should a recommendation change?

Those questions belong to downstream scientific evaluation and human validation.

---

## Future extensions

After this contract is stable, the next safe extensions are:

1. status-aware adapters for all discovery providers;
2. scheduled/triggered execution outside the scientific core;
3. document-class aware watch events (for example new guideline/consensus/standard);
4. accepted-claim change tracking after human validation exists;
5. conflict/convergence monitoring over validated claims;
6. visual Watch dashboard with topic state, delta, last verified audit and action required;
7. notification adapters that report only verified operational changes.

The longitudinal layer must remain downstream of traceability and upstream of any optional formal-review/PRISMA workflow.
