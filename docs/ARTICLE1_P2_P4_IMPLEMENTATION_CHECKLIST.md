# Article 1 P2/P3/P4 implementation checklist

## Implemented in this branch

- [x] Persistent ABCD 34/34 reviewer submissions in the existing Evidence Matrix SQLite
- [x] Separate ABCD adjudication ledger preserving original R1/R2 submissions
- [x] GF-07 identity guard for FORMAL reviewer work
- [x] STAGING / CALIBRATION / FORMAL execution-mode separation
- [x] ABCD calibration report using the canonical D-102 rules
- [x] Explicit relation ledger separate from co-occurrence
- [x] Multiple relation evidence instances without multiplying normalized relation count
- [x] R1/R2 relation-set comparison and descriptive Jaccard
- [x] Relation adjudication without inferred absent 34×34 negatives
- [x] Descriptive methodological characterization separate from ABCD
- [x] Family-preserving synthesis
- [x] Anti-score / anti-ranking synthesis safeguards
- [x] Controlled ENGINE_TO_SHEET payload
- [x] Article 1 citation/audit manifest
- [x] PRISMA formal-lineage guard
- [x] Evidence Matrix export bundle integration
- [x] Generic quality appraisal kept non-mandatory for Article 1
- [x] Regression tests for core runtime invariants

## Deliberately not fabricated by this branch

- [ ] PubMed/Scopus/WoS PILOT execution evidence
- [ ] PRESS approval
- [ ] GF-01/GF-02/GF-03/GF-10 closure
- [ ] Real R2/adjudicator identities
- [ ] Formal search execution
- [ ] Formal screening decisions
- [ ] Final PRISMA counts
- [ ] Scientific synthesis results

Those items require real external/human execution and remain scientific gates rather than software TODOs.
