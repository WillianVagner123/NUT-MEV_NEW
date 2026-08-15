# Roadmap

Scientific correctness, reproducibility and human oversight take precedence over speed.

The canonical current implementation scope and stop rule are defined in [`ENGINE_MASTER_SCOPE_AND_DEFINITION_OF_DONE.md`](ENGINE_MASTER_SCOPE_AND_DEFINITION_OF_DONE.md).

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
- [ ] Wire the same reviewer-slot/blinding rules through every persistent article/full-text ledger and UI route.

### P2 — ABCD extraction persistence

- [x] Bind the 34-component codebook to the existing evidence-matrix/reviewer-slot persistence layer.
- [x] Persist document × component × reviewer-slot × codebook-version decisions.
- [x] Preserve evidence locator, passage, reviewer/source provenance, revision and adjudication state.
- [x] Isolate STAGING/CALIBRATION/FORMAL and block final synthesis until included documents are 34/34 resolved.

### P3 — explicit ABCD relations

- [x] Add a first-class relation ledger separate from co-occurrence.
- [x] Count unique relation tuples by document × source × target × direction × type.
- [x] Preserve multiple evidence instances without multiplying relation counts.
- [x] Add explicit relation-review completion, including reviewed-empty sets.
- [x] Add descriptive R1/R2 relation calibration (intersection/union/Jaccard) without arbitrary pass threshold.

### P4 — synthesis, synchronization and manuscript package

- [x] Synthesize presence, depth, co-occurrence and explicit relations as separate outputs with denominators by documentary family.
- [x] Generate PRISMA only from PRISMA-eligible FORMAL lineage through explicit guards.
- [x] Tie Article 1 exports to codebook/runtime/session audit manifests and the existing evidence-matrix export layer.
- [x] Generate an `ENGINE_TO_SHEET` Article 1 payload for controlled audit views.
- [ ] Complete authenticated, schema-safe, idempotent Engine → Google Sheets transport; the Sheet must remain an audit mirror, not a second engine.
- [ ] Finalize one canonical manuscript-bundle command/workspace for a selected frozen Article 1 session.

## Minimal closure before architecture freeze

Stop expanding the current Article 1 architecture after these items are complete:

- [ ] S1 — persistent screening ledgers/UI fully enforce canonical reviewer-slot/blinding behavior.
- [ ] S2 — real Engine → Google Sheets transport, with dry-run/diff and sync provenance.
- [ ] S3 — canonical Article 1 strategy import/registration workflow demonstrated without retyping drift.
- [ ] S4 — end-to-end non-PRISMA Article 1 rehearsal passes through strategy → PILOT → corpus → calibration paths → ABCD/relations → synthesis/export → Sheet dry-run.
- [ ] S5 — one-command/workspace manuscript bundle finalized.

After S1-S5, new feature ideas are backlog unless they block a protocol requirement. Manuscript writing becomes the primary activity.

## Scientific/external work still required

Software implementation does not close human/scientific gates. Real PILOT evidence, sentinel/noise audit, PRESS, licensed Scopus/Web of Science execution as required, GF-07 reviewer identities/calibration, GF-10 freeze authorization, formal search from zero, human screening/extraction/adjudication and final manuscript outputs remain separate scientific records.

## Article 2 boundary

Do not build a speculative second Article 2 engine before writing. Article 2 may reuse frozen Article 1 evidence maps, relations and provenance, but clinical/protocol synthesis remains a separate human scientific layer. Frequencies or ABCD depth must not be automatically converted into recommendations or a protocol score.

## Release / Zenodo

Release publication and Zenodo remain later gates. A software implementation branch is not evidence that the scientific review has been executed or validated.

## Architectural rule

Large refactors that may alter scientific outputs require parity tests and versioned methodological review. Query generation, provider behavior, deduplication, coding rules, screening/export gates and configuration semantics must not change silently.

## Permanently out of scope

- rewriting Git history to make old tags look cleaner;
- presenting automated output as final clinical recommendation;
- allowing a legacy heuristic to silently become the current scientific object;
- building a second Article 1 execution pipeline outside NutEV Evidence Engine;
- delaying Article 1/2 writing to add non-required speculative software features.
