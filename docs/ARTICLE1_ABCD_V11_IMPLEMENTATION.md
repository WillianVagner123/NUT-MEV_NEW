# Article 1 — ABCD-NutEV v1.1-candidate inside the Evidence Engine

Status: **integrated implementation candidate on the Evidence Engine branch**.

This is not a parallel pipeline. The canonical Article 1 execution remains inside NutEV Evidence Engine. The methodological authority is the versioned Article 1 protocol/codebook and D-xxx decision log; this software module implements the currently closed D-098, D-099, D-102, D-105, D-106 and D-107 rules.

## Canonical scientific object

Article 1 uses 34 ABCD components: A1-A5, B1-B9, C1-C10 and D1-D10. Each component is evaluated in two stages: presence (`YES`, `NO`, `DOUBT`) and depth (0-3) when the state permits it.

Hard invariants:

- `YES` -> depth 1-3;
- `NO` -> depth 0;
- `DOUBT` -> depth blank while unresolved;
- `DOUBT` cannot remain at final document closure;
- blank/missing is unassessed, not absence;
- N/A is not a valid ABCD presence state;
- each included document closes only with all 34 codes evaluated exactly once.

Depth is ordinal and component-specific. The Engine must not derive a global ABCD score, mean depth, maturity score, ranking or evidence-quality interpretation from it.

## D-102 calibration

Presence agreement preserves `YES / NO / DOUBT` as observed independent states. `DOUBT` is not blank and is not silently removed from the presence denominator.

Depth agreement is calculated only among component pairs where both reviewers independently coded presence=`YES`.

Operational stability/revision signals remain: presence >=80%, exact depth >=70%, depth difference <=1 in >=90%, with 100% expected-pair completeness. These are operational signals, not validity claims. Recurring critical conceptual contradiction blocks stability regardless of aggregate percentages.

## D-105/D-106/D-107 screening

The canonical screening rules live in `src/nutev/review/screening.py`:

- R1, R2 and adjudicator must be real and distinct before formal screening;
- title/abstract preserves `INCLUDE / EXCLUDE / DOUBT` but maps `INCLUDE` and `DOUBT` to the conservative action `ADVANCE`;
- full-text `DOUBT` always remains unresolved and blocks closure until consensus/adjudication;
- original independent decisions are preserved;
- family agreement is evaluated only among `INCLUDE x INCLUDE` full-text pairs;
- reviewer blindness must hide the paired decision until explicit unblinding;
- recurrence by divergence mechanism, not only an aggregate disagreement percentage, drives rule revision.

## Legacy four-domain model

The historical broad A/B/C/D lexical heuristic remains available only for reproducibility/compatibility of older runs. It is not the current Article 1 scientific object and must not be presented as the manuscript-facing result.

The canonical manuscript-facing ABCD export is document x 34 components and is emitted only from final human 34/34 coding. The Engine does not fabricate it from the legacy machine heuristic.

## PRISMA boundary

PILOT, staging and calibration outputs contribute zero formal PRISMA counts. Formal inclusion remains pending until the formal two-reviewer screening/full-text workflow is complete under the authorized frozen strategy.

## Integration principle

Google Sheets is an audit/synchronization surface. It does not replace the Evidence Engine runtime or become an independent second execution path.
