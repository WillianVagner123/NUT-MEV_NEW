# NutEV Reference Engine — Validation Runtime Freeze

Status: **FROZEN FOR SCIENTIFIC BENCHMARK**  
Scientific verdict at freeze: **B — DEMOTE**  
Frozen runtime SHA: `6aa7a5fe6009776e611ca3e1506486606b05f4f6`  
Engineering-gate base main: `6070e89786eb0164a9a8d8531effe8e3703d1845`  
Taxonomy: `2026-08-v2`  
Guardrail policy: `2026-08-18.2`

## Purpose

This freeze identifies the exact runtime candidate that may be evaluated in the scientific rehabilitation benchmark. It does **not** claim that the Engine is scientifically validated.

## Runtime contract frozen

The candidate binds, through the Git commit SHA:

- `config/reference_search.json` queries and provider limits;
- `config/reference_mode.json` ranking weights and guardrails;
- `config/taxonomy_registry.json` and all `keyword_taxonomy*.json` vocabulary sources;
- traceability classes and identifier validation;
- canonical identity/deduplication rules;
- taxonomy compilation/classification;
- ranking logic and score breakdown;
- export and audit behavior;
- scientific-validation metric implementation present at the commit.

## Canonical identity at freeze

```text
valid DOI
  -> valid PMID
  -> normalized HTTP(S) URL
  -> normalized title
```

Collection and ranking share the implementation in `src/nutev/reference_identity.py`.

## Change-control rule

Benchmark results attributed to this candidate must use the frozen SHA. No external-test labels may be used to modify:

- queries;
- taxonomy;
- ranking weights;
- provider weights;
- focus keywords;
- identity/deduplication rules;
- traceability rules.

A runtime change requires a new candidate SHA and a new freeze record. Development-set tuning is permitted only when explicitly separated from the sealed external test set.

## Scientific boundary

At freeze, the following remain untested unless later populated with real benchmark evidence:

- recall/precision;
- MAP/MRR/nDCG;
- taxonomy validity versus independent humans;
- semantic/work-level deduplication quality;
- provider incremental value;
- metadata bias;
- quarantine recall loss;
- ranking sensitivity;
- user workload benefit;
- external generalization.

The freeze therefore changes the project from **not ready to test** to **ready to test**. It does not change the scientific verdict from `B — DEMOTE`.

## Required evidence chain

```text
FROZEN RUNTIME
  -> INDEPENDENT GOLD STANDARD
  -> SEALED EXTERNAL TEST SET
  -> DECLARED BASELINES
  -> BENCHMARK
  -> ABLATIONS / SENSITIVITY
  -> TAXONOMY / DEDUP / PROVIDER / QUARANTINE AUDITS
  -> FINAL A/B/C/D VERDICT
```

Stable release `v1.0.0` remains immutable and is not moved or recreated by this freeze.
