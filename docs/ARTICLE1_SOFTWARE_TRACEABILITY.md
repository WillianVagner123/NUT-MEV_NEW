# Article 1 — software traceability matrix

This document links Article 1 methodological claims to the NutEV Evidence Engine implementation. The study protocol/codebook and D-xxx decision log remain the scientific-method authority; the exact Engine commit defines what the software actually executed. Human reviewers remain authoritative for final inclusion, ABCD coding, relations and adjudication.

## Scope rule

The Engine supports identification, organization, deduplication, traceability, reviewer workflows, validation guards and reproducible exports. It does **not** infer final scientific decisions or clinical recommendations.

## Current Article 1 traceability

| Method claim / function | Engine implementation | Verification | Human / scientific boundary |
|---|---|---|---|
| Search versions, PILOT/FORMAL separation and freeze guards | search strategy registry/execution/gate modules | canonical search/gate tests and run manifests | real PRESS, licensed executions and GF closures are external/human evidence |
| Corpus identity, deduplication and provenance | corpus build/registry modules | immutable manifests, hashes and dedup tests | ambiguous versions/manifestations may require human review |
| Canonical ABCD scientific object = 34 components | `src/nutev/analysis/article1_abcd.py` | `nutev_tests/test_article1_abcd.py` | final presence/depth is human; no machine absence or global score |
| ABCD closure requires 34/34 | `article1_abcd.document_completion` / `assert_document_can_close` | missing, duplicate, DOUBT and presence↔depth invariant tests | unresolved component blocks final synthesis/export |
| D-102 calibration keeps YES/NO/DOUBT in presence agreement | `article1_abcd.calibration_metrics` | calibration denominator/depth-denominator tests | thresholds are revision signals, not construct-validity claims |
| Title/abstract DOUBT advances conservatively | `src/nutev/review/screening.py` | screening tests for `DOUBT -> ADVANCE` | original independent DOUBT remains preserved |
| Full-text DOUBT blocks closure | `screening.reconcile_full_text` / `final_decision` | unresolved-DOUBT tests | consensus/adjudication required; original decisions are not overwritten |
| Screening calibration is separate from ABCD calibration | `title_abstract_calibration_metrics` and `full_text_calibration_metrics` | 100% completeness, ≥80% candidate signal, GF-07 and contradiction guards | GF-07 requires real R1/R2/adjudicator; software cannot invent identities |
| Reviewer blindness | `screening.blind_reviewer_view` as service-layer invariant | paired-decision hiding tests | UI/persistence layer must enforce the same rule |
| Historical broad A/B/C/D heuristic | `article1_coding.py` / `domain_states.py` | legacy regression tests | compatibility/assistive only; not the current manuscript ABCD result |
| Canonical manuscript ABCD export | `src/nutev/export/article1_exports.py::abcd_34_matrix_rows` | `nutev_tests/test_article1_exports.py` | emitted only from final human 34/34 coding |
| PRISMA remains formal-lineage only | search execution guards + screening/full-text ledgers | PRISMA/export tests | PILOT/staging/calibration contribute zero formal PRISMA counts |
| Generic evidence-matrix infrastructure | `src/nutev/review/evidence_matrix_*` | evidence-matrix tests | Article 1 must not auto-require AGREE II/AGREE-REX; descriptive method characterization remains separate |

## Explicit deprecations for Article 1

The following are not valid current manuscript-facing ABCD outputs:

- four broad A/B/C/D booleans as the final scientific object;
- `profile`;
- `n_domains` / `n_domains_positive`;
- global ABCD sum;
- mean depth;
- maturity/ranking score;
- co-occurrence interpreted as explicit integration.

Historical broad-domain artifacts may remain for reproducibility, but must be labelled legacy/compatibility.

## Citation-grade run record

For any analysis cited in the manuscript, record at minimum:

- exact Engine commit SHA and released software version when applicable;
- execution date/time and environment snapshot;
- config digest and frozen search-strategy version;
- corpus/input/output manifests and hashes;
- codebook version (`ABCD-NutEV v1.1-candidate` until formally superseded);
- reviewer/adjudication ledgers;
- the exact publication-facing tables used.

Passing software tests demonstrates implementation-contract behavior only. It does not establish scientific validity or substitute for protocol adherence, real reviewer calibration or external/human gates.
