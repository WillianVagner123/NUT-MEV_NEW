# Scientific Validation Status

Current verdict: **B — DEMOTE**  
Meaning: operational/experimental reference-discovery utility; scientific incremental benefit not yet demonstrated.

Base `main` audited for this engineering-gate cycle: `6070e89786eb0164a9a8d8531effe8e3703d1845`  
Canonical taxonomy: `2026-08-v2`  
Stable release `v1.0.0`: must remain immutable.

## Evidence status

| Domain | Status | Current evidence |
|---|---|---|
| Software executes deterministically for fixed inputs/config | OBSERVED | Unit/integration tests and prior audited runs |
| Input/output integrity via hashes | OBSERVED | Guardrails and `AUDIT_MANIFEST.json` |
| Canonical taxonomy structure | OBSERVED | Registry, fail-closed mapping, taxonomy tests |
| Scientific retrieval recall | NOT_TESTED | No independent gold standard yet |
| Scientific retrieval precision | NOT_TESTED | No independent gold standard yet |
| MAP/MRR/nDCG versus baselines | NOT_TESTED | No comparative benchmark yet |
| Taxonomy validity versus human experts | NOT_TESTED | Structural tests are not scientific validation |
| Work-level deduplication precision/recall | NOT_TESTED | Canonical exact identity is not semantic/work-level validation |
| Provider incremental value | NOT_TESTED | No leave-one-provider-out benchmark |
| Provider weight validity | NOT_TESTED | Weights remain engineering heuristics |
| Metadata availability bias | NOT_TESTED | No controlled perturbation study |
| Quarantine recall loss | NOT_TESTED | No human review sample of quarantined relevant records |
| Ranking sensitivity | NOT_TESTED | No systematic parameter perturbation benchmark |
| User workload benefit | NOT_TESTED | No controlled user study |
| Generalization to external questions | NOT_TESTED | No sealed external test set |

## Engineering gate

| Requirement | Status | Action/evidence |
|---|---|---|
| Taxonomy registry and exclusion of historical workstreams | PASS | Registry and regression tests |
| Document type separated from taxonomy | PASS | Taxonomy registry tests |
| Input SHA-256 fail-closed | PASS | Guardrail contract |
| Invalid identifier cannot qualify as `A_IDENTIFIER` | IMPLEMENTED_PENDING_CI | Shared identifier validators reject malformed DOI/PMID/PMCID |
| Invalid identifier never repaired by inference | IMPLEMENTED_PENDING_CI | Malformed values remain unchanged and are quarantined or use URL fallback |
| Consistency between identifier validity and identifier score bonus | IMPLEMENTED_PENDING_CI | Identifier bonus now requires the same validated identifier contract as traceability |
| Same canonical identity normalization in collection and ranking | IMPLEMENTED_PENDING_CI | Both stages call `src/nutev/reference_identity.py` for DOI -> PMID -> URL -> title identity and deduplication |
| README/limitations fully aligned with canonical taxonomy/runtime | IMPLEMENTED_PENDING_CI | Public docs now describe traceability gate, canonical taxonomy `2026-08-v2`, `Q_INVALID_IDENTIFIER` and shared identity |
| Branch protection / required checks enforced in repository settings | EXTERNAL_GOVERNANCE_GAP | Tracked separately; not scientific evidence |

## Freeze decision

**FREEZE BLOCKED PENDING CI.**

The three repository engineering failures from issue #1094 have implementation changes on the current branch, but they are not `PASS` until the full GitHub Actions suite succeeds on the exact candidate head.

No external-test labels may be used to tune ranking weights, queries or taxonomy before a validation candidate is frozen.

## Required next sequence

1. pass CI on the exact engineering-gate candidate;
2. mark the engineering requirements `PASS`;
3. declare the exact validation candidate SHA/freeze;
4. build the independent gold standard;
5. execute baselines and NutEV on identical questions;
6. compute benchmark metrics;
7. run ablations and sensitivity analyses;
8. validate taxonomy against humans;
9. test deduplication, provider contribution and quarantine loss;
10. open the sealed external test set;
11. issue verdict A/B/C/D.

## Interpretation rule

Absence of evidence is not proof of uselessness. Conversely, successful software execution is not proof of scientific utility. Until an independent benchmark exists, `B_DEMOTE` remains the only defensible scientific status.
