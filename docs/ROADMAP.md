# Roadmap

Scientific correctness, reproducibility and human oversight take precedence over speed.

## Historical v0.1.x line

Historical tags `v0.1.0` through `v0.1.8` are preserved unchanged. They record earlier development states and are not rewritten to match the current citation-grade line.

## v0.2.0 — citation-grade reconciled Evidence Engine

Completed baseline capabilities include repository provenance, CI/security/release controls, search-strategy registry and execution traceability, auditable normalization/deduplication, full-text recoverability, human screening/adjudication infrastructure, PRISMA-oriented exports, config provenance and release metadata.

Historical broad A/B/C/D coding remains reproducible but is no longer the canonical Article 1 scientific object.

## Current Article 1 integration line

The Evidence Engine itself is the execution layer. Do not create a parallel review pipeline outside this repository.

### P0 — methodology parity

- [x] Add canonical ABCD-NutEV v1.1-candidate registry with 34 components (A1-A5, B1-B9, C1-C10, D1-D10).
- [x] Enforce presence/depth invariants: YES→1-3, NO→0, DOUBT→blank/unresolved, missing≠absence.
- [x] Enforce 34/34 closure before canonical ABCD export.
- [x] Block global ABCD score, mean depth, maturity/ranking fields from the canonical path.
- [x] Reclassify the historical four-domain heuristic as compatibility/assistive only.
- [x] Add D-102 calibration metrics with DOUBT retained in the presence denominator.

### P1 — reviewer-pair screening convergence

- [x] Integrate D-105/D-106/D-107 semantics into the existing `review/screening.py` module.
- [x] Title/abstract: preserve DOUBT and map it operationally to ADVANCE.
- [x] Full text: DOUBT blocks closure until consensus/adjudication.
- [x] Add formal R1/R2/adjudicator distinct-identity guard.
- [x] Add reviewer-blindness service-layer invariant and calibration metrics.
- [ ] Wire the same reviewer-slot/blinding rules through all persistent article/full-text ledgers and UI routes.

### P2 — ABCD extraction persistence

- [ ] Bind the 34-component codebook to the existing evidence-matrix/reviewer-slot persistence layer.
- [ ] Persist document × component × reviewer-slot × codebook-version decisions.
- [ ] Preserve evidence locator, passage, human/machine source and adjudication state.
- [ ] Block final synthesis until every included document is 34/34 resolved.

### P3 — explicit ABCD relations

- [ ] Add a first-class relation ledger separate from co-occurrence.
- [ ] Count unique relation tuples by document × source × target × direction × type.
- [ ] Preserve multiple evidence instances without multiplying relation counts.
- [ ] Add descriptive R1/R2 relation calibration (intersection/union/Jaccard) without arbitrary pass threshold.

### P4 — synthesis, synchronization and manuscript package

- [ ] Synthesize presence, depth, co-occurrence and explicit relations as separate outputs with denominators by documentary family.
- [ ] Synchronize controlled audit views to the canonical Google Sheet without creating a second execution engine.
- [ ] Generate PRISMA only from PRISMA-eligible FORMAL lineage.
- [ ] Tie manuscript exports to codebook version, Git SHA, config digest, corpus build and reviewer ledgers.

## Scientific/external work still required

Software implementation does not close human/scientific gates. Real PILOT evidence, PRESS, licensed Scopus/Web of Science execution, GF-07 reviewer identities/calibration, GF-10 freeze authorization and the formal search from zero remain separate scientific records.

## Release / Zenodo

Release publication and Zenodo remain later gates. A software implementation branch is not evidence that the scientific review has been executed or validated.

## Architectural rule

Large refactors that may alter scientific outputs require parity tests and versioned methodological review. Query generation, provider behavior, deduplication, coding rules, screening/export gates and configuration semantics must not change silently.

## Permanently out of scope

- rewriting Git history to make old tags look cleaner;
- presenting automated output as final clinical recommendation;
- allowing a legacy heuristic to silently become the current scientific object;
- building a second Article 1 execution pipeline outside NutEV Evidence Engine.
