# Scientific Validation Status

Current verdict: **B — DEMOTE**  
Meaning: operational/experimental reference-discovery utility; scientific incremental benefit not yet demonstrated.

Engineering-gate base `main`: `6070e89786eb0164a9a8d8531effe8e3703d1845`  
Frozen validation runtime candidate: `6aa7a5fe6009776e611ca3e1506486606b05f4f6`  
Canonical taxonomy: `2026-08-v2`  
Guardrail policy: `2026-08-18.2`  
Stable release `v1.0.0`: immutable and outside this validation freeze.

## Evidence status

| Domain | Status | Current evidence |
|---|---|---|
| Software executes deterministically for fixed inputs/config | OBSERVED | Unit/integration tests and audited runtime contracts |
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

| Requirement | Status | Evidence |
|---|---|---|
| Taxonomy registry and exclusion of historical workstreams | PASS | Registry and regression tests |
| Document type separated from taxonomy | PASS | Taxonomy registry tests |
| Input SHA-256 fail-closed | PASS | Guardrail contract |
| Invalid identifier cannot qualify as `A_IDENTIFIER` | PASS | Shared DOI/PMID/PMCID validators + regression tests |
| Invalid identifier never repaired by inference | PASS | Malformed values remain unchanged; URL fallback/quarantine is explicit |
| Consistency between identifier validity and identifier score bonus | PASS | `score_breakdown.identifier` now requires the same validated identifier contract used by traceability |
| Same canonical identity normalization in collection and ranking | PASS | Both stages call `src/nutev/reference_identity.py` and share `dedupe_records` |
| README/limitations aligned with canonical taxonomy/runtime | PASS | Public docs describe full flow, `2026-08-v2`, `Q_INVALID_IDENTIFIER`, shared identity and `B — DEMOTE` |
| Branch protection / required checks enforced in repository settings | EXTERNAL_GOVERNANCE_GAP | Separate repository-governance issue; not scientific evidence |

## CI evidence for frozen runtime candidate

GitHub Actions on `6aa7a5fe6009776e611ca3e1506486606b05f4f6`:

- tests Python 3.12: PASS;
- tests Python 3.13: PASS;
- Windows smoke Python 3.12: PASS;
- audit guardrail contract: PASS;
- typecheck provenance core: PASS;
- lint/compile: PASS;
- security scan: PASS;
- dependency review: PASS;
- release artifact validation: PASS;
- CodeQL: PASS.

## Freeze decision

**ENGINEERING GATE: PASS.**

**VALIDATION RUNTIME CANDIDATE: FROZEN at `6aa7a5fe6009776e611ca3e1506486606b05f4f6`.**

The freeze binds the runtime implementation used for the forthcoming scientific benchmark. The project remains scientifically `B — DEMOTE` because no independent retrieval benchmark has yet been executed.

After this freeze:

- external-test labels must not be used to change ranking weights, queries, taxonomy or identity rules for this candidate;
- tuning, if needed, must use a declared development set and produce a new candidate version;
- documentation may describe the frozen candidate without changing its runtime SHA;
- any runtime change creates a new validation candidate and invalidates direct attribution of later benchmark results to this SHA.

## Required next sequence

1. construct the independent gold standard without using NutEV rankings to define relevance;
2. seal the external-test partition;
3. generate identical-question outputs for NutEV and the declared baselines;
4. compute precision/recall@k, MRR, MAP, nDCG and workload milestones;
5. run ablations and sensitivity analyses on the permitted development/validation data;
6. validate taxonomy against independent human classifications;
7. benchmark work-level deduplication;
8. quantify provider contribution, metadata bias and quarantine recall loss;
9. open the sealed external-test set only after decisions are fixed;
10. issue verdict A/B/C/D.

## Interpretation rule

Engineering-gate success permits scientific testing; it does not constitute scientific validation. Until an independent benchmark demonstrates otherwise, `B_DEMOTE` remains the defensible scientific verdict.
