# Article 1 — P2/P3/P4 runtime inside NutEV Evidence Engine

Status: implementation branch. This document describes software capability only; it does not close scientific or human gates.

## P2 — ABCD 34/34 persistence

The canonical Article 1 ABCD object is persisted in the same Evidence Matrix SQLite used by the rest of the Engine. The unit is document × reviewer slot × ABCD component × codebook version. Human submissions are append-only by revision. Final closure requires all 34 components and resolves reviewer disagreement through a separate adjudication ledger.

Hard rules remain: YES requires depth 1–3 and traceable evidence; NO requires depth 0; DOUBT keeps depth blank and cannot be final; missing remains unassessed; N/A is not a valid state; no global score, mean depth, maturity score or ranking is produced.

FORMAL ABCD work is blocked until a real GF-07 assignment exists for R1, R2 and adjudicator. STAGING and CALIBRATION remain distinguishable from FORMAL.

## P3 — explicit relations

Relations are first-class records in the same SQLite. A normalized scientific relation is document × source code × target code × direction × relation type. Evidence passages are stored as separate evidence instances attached to the normalized relation. Multiple passages do not multiply the normalized relation count.

Accepted directions: SOURCE_TO_TARGET, BIDIRECTIONAL and NON_DIRECTIONAL. Relation types are explicit semantic links such as CONDITION, MODIFIES, REQUIRES, TRIGGERS, SUPPORTS, MONITORS and COORDINATES. Co-occurrence is not an accepted relation type and cannot create a relation.

R1/R2 relation calibration reports set sizes, intersection, union and descriptive Jaccard. There is no arbitrary Jaccard pass threshold and absent 34×34 pairs are not used as negative agreement.

## P4 — synthesis, Sheet payload and manifest

The runtime can build family-preserving outputs for component presence, component-specific depth, co-occurrence and explicit relations as separate datasets. Synthesis is blocked in strict mode until all included Article 1 documents have closed ABCD and relation review.

The Google Sheet payload is one-way by contract: ENGINE_TO_SHEET. It is an audit/export representation and does not silently overwrite runtime history.

Evidence Matrix snapshot exports include Article 1 codebook, latest ABCD submissions, comparison/adjudication state, final 34-component rows when closed, relation ledgers, methodological characterization, synthesis, Sheet-sync payload and Article 1 manifest.

The Article 1 manifest records the codebook version, session, available Git/config identifiers, GF-07 identity state and runtime readiness. It explicitly states that software capability does not imply PRESS approval, GF closure, formal search execution, PRISMA completion or scientific validity.

## PRISMA boundary

A dedicated guard refuses formal PRISMA use for STAGING/CALIBRATION, without GF-10 freeze authorization, before screening calibration release, or while unresolved screening decisions remain. The guard does not manufacture PRISMA counts.

## Quality-appraisal boundary

Generic quality instruments remain available to other Evidence Matrix workflows. Article 1 exports explicitly mark methodological quality appraisal as non-mandatory; ABCD coverage/depth is not a quality score.

## Files

- `src/nutev/review/article1_runtime.py`
- `src/nutev/review/evidence_matrix.py`
- `src/nutev/review/evidence_matrix_export.py`
- `nutev_tests/test_article1_runtime.py`

The next scientific blockers remain external/human: PILOT evidence, PRESS, licensed Scopus/WoS execution where applicable, real GF-07 identities, freeze authorization and formal execution from zero.
