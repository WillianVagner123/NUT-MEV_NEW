# Scientific Validation Status

Current verdict: **B — DEMOTE**  
Meaning: operational/experimental reference-discovery utility; scientific incremental benefit not yet demonstrated.

Base `main` audited for this rehabilitation cycle: `0585732c456b0fae95cd1fc511d8263d6524c680`  
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
| Work-level deduplication precision/recall | NOT_TESTED | Current identity rule is identifier/URL/title based |
| Provider incremental value | NOT_TESTED | No leave-one-provider-out benchmark |
| Provider weight validity | NOT_TESTED | Weights remain engineering heuristics |
| Metadata availability bias | NOT_TESTED | No controlled perturbation study |
| Quarantine recall loss | NOT_TESTED | No human review sample of quarantined relevant records |
| Ranking sensitivity | NOT_TESTED | No systematic parameter perturbation benchmark |
| User workload benefit | NOT_TESTED | No controlled user study |
| Generalization to external questions | NOT_TESTED | No sealed external test set |

## Engineering gate

| Requirement | Status | Action |
|---|---|---|
| Taxonomy registry and exclusion of historical workstreams | PASS | Maintain tests and versioning |
| Document type separated from taxonomy | PASS | Maintain tests |
| Input SHA-256 fail-closed | PASS | Maintain tests |
| Invalid identifier cannot qualify as `A_IDENTIFIER` | IMPLEMENTED_PENDING_CI | Added syntax validation in rehabilitation branch |
| Invalid identifier never repaired by inference | IMPLEMENTED_PENDING_CI | Added explicit regression test |
| Consistency between identifier validity and identifier score bonus | FAIL | Ranking bonus currently depends on raw identifier presence; must use validated identifier state |
| Same canonical identity normalization in collection and ranking | FAIL | Collection and ranker currently implement different normalization logic |
| README/limitations fully aligned with canonical taxonomy/runtime | FAIL | Residual pre-registry wording remains in public docs |
| Branch protection / required checks enforced in repository settings | EXTERNAL_GOVERNANCE_GAP | Tracked separately; connector cannot enforce admin settings |

## Freeze decision

**FREEZE BLOCKED.**

The scientific candidate must not be frozen while the three engineering `FAIL` items above remain unresolved. No empirical scientific result may be claimed before a freeze and independent benchmark.

## Required next sequence

1. close engineering FAIL items;
2. pass CI;
3. declare validation candidate/freeze;
4. build independent gold standard;
5. execute baselines and NutEV on identical questions;
6. compute benchmark metrics;
7. run ablations and sensitivity analyses;
8. validate taxonomy against humans;
9. test deduplication, provider contribution and quarantine loss;
10. open sealed external test set;
11. issue verdict A/B/C/D.

## Interpretation rule

Absence of evidence is not proof of uselessness. Conversely, successful software execution is not proof of scientific utility. Until the benchmark exists, `B_DEMOTE` remains the only defensible status.
