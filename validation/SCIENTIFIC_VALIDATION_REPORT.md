# Scientific Validation Report

Date initialized: 2026-08-18

## Current verdict

**B — DEMOTE**

The NutEV Reference Engine is currently an operational/experimental reference-discovery and reading-priority utility. Scientific incremental benefit has not yet been demonstrated against an independent gold standard and appropriate baselines.

## Engineering audit

See `SCIENTIFIC_VALIDATION_STATUS.md`.

Current scientific freeze: **BLOCKED** while critical engineering inconsistencies remain.

## Benchmark

Status: `NOT_TESTED`

No independent gold standard, comparative retrieval metrics or sealed external test set has been registered yet.

## Taxonomy validation

Status: `NOT_TESTED`

The taxonomy has structural/fail-closed tests, but no external human validity study yet.

## Deduplication validation

Status: `NOT_TESTED`

Current identifier/URL/title identity behavior has not been benchmarked against a work-level duplicate gold standard.

## Provider contribution and metadata bias

Status: `NOT_TESTED`

Provider weights remain engineering heuristics pending leave-one-provider-out and controlled metadata/provider perturbation studies.

## Quarantine recall impact

Status: `NOT_TESTED`

No human-audited relevant-record sample has yet quantified recall loss caused by the traceability gate.

## User benefit

Status: `NOT_TESTED`

No controlled comparison has measured time or workload reduction versus a baseline workflow.

## Decision rule

This report may only change to `C — SCIENTIFIC_CANDIDATE` or `D — VALIDATED_FOR_DEFINED_USE` from observed benchmark data produced under the protocol. If results demonstrate absence of sufficient value, `A — KILL` remains an allowed outcome.

Successful CI, hashes, release DOI, number of records or documentation quality cannot by themselves change the verdict.
