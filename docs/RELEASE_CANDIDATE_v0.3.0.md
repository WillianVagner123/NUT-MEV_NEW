# NutEV Evidence Engine v0.3.0 — Validated Candidate Record

Status: **VALIDATED CANDIDATE — PUBLICATION DEFERRED / NOT PUBLISHED**

This document preserves the validation history of the 2026-08-10 `0.3.0` candidate. No `v0.3.0` tag, GitHub Release, Zenodo archive or DOI was created. Development subsequently resumed on `main`.

## Object identity

The candidate validated the unified global-search, generated-versus-executed provenance, master-corpus, curation/human-review and reproducible release-validation architecture used to support the evidence-synthesis workflow of the NutEV project.

This was a **software/reproducibility candidate** at alpha scientific maturity. It did not assert that human screening was complete, that the Article 1 manuscript was ready, or that any `RecommendationCandidate` was a final clinical recommendation.

## Candidate lineage

- Candidate branch: `release/0.3.0-candidate`
- Candidate base main SHA: `b3a98095372ad74a72737bcc81776089f4d686c7`
- Exact validated candidate head SHA: `6a3035bac80ebfb4467bfdd3bf7ea48632a2e3e5`
- Squash merge SHA that recorded the candidate on `main`: `aedf6d7e370d4705a08ef7f96fa8293d8a5d8504`
- Previous and still-latest immutable public release: `v0.2.0`
- Proposed but **never published** tag: `v0.3.0`
- Candidate package version: `0.3.0`
- Zenodo DOI: **none assigned / none asserted**
- Release date: **none assigned because no release occurred**

After publication was deferred, the source tree returned to a PEP 440 development identity (`0.3.0.dev1`) and citation/archive metadata returned to the latest actually published release (`0.2.0`).

## Scientific invariants validated

The candidate preserved these release-critical contracts:

- generated query is not an executed query;
- actual provider attempts are the authority for executed-query ledgers;
- `execution_status` is distinct from `scientific_readiness`;
- `manuscript_ready` requires explicit human/manuscript gates;
- one global frozen research strategy is rendered per provider and produces one governed run/master corpus before article-specific screening;
- Track A, Track B and optional Track C retain distinct sampling/provenance semantics;
- metadata-only is not silently promoted to full text;
- the current SciELO connector is Crossref retrieval scoped to DOI prefix `10.1590`, not a comprehensive native SciELO free-text search;
- operational prioritization is not scientific inclusion;
- Evidence Engine is not a Clinical Decision Engine.

## Exact-SHA validation evidence

All required candidate workflows completed successfully on exact candidate head `6a3035bac80ebfb4467bfdd3bf7ea48632a2e3e5`:

- canonical CI on Python 3.12 and 3.13;
- blocking coverage threshold: **73.19%** with a 70% floor;
- test result: **752 passed, 8 skipped, 1 xpassed**;
- Windows smoke and zero-key demo;
- compileall and blocking Ruff checks;
- mypy provenance-core checks;
- CodeQL;
- security scan / Gitleaks / repository hygiene;
- dependency review actually executed;
- wheel and sdist build;
- metadata validation;
- clean wheel install, CLI startup and zero-key demo from the installed artifact.

Relevant workflow run IDs recorded during validation:

- CI: `31378474870`
- release-artifact-validation: `31378474890`
- security-scan: `31378474659`
- dependency-review: `31378474448`
- CodeQL: `31378474445`

These results are historical evidence for that exact candidate SHA. They are **not** automatically PASS evidence for later development SHAs.

## Why publication was deferred

Publication was intentionally postponed so repository cleanup, structural backlog reconciliation and end-to-end scientific workflow validation could continue before any new public release is frozen.

Therefore:

- `v0.3.0` must not be described as published;
- `0.3.0` candidate validation must not be confused with a released software object;
- future publication requires a **new candidate SHA** and fresh exact-SHA gates;
- the latest public/citable release remains `v0.2.0` until a later release is actually published.

## Future publication gate

If/when publication is resumed, create a fresh release candidate from the then-current `main`, reconcile version/citation/archive metadata on that new candidate, re-run all release gates on its exact final SHA, confirm tag collision absence, and only then consider creating a new immutable tag/release.
