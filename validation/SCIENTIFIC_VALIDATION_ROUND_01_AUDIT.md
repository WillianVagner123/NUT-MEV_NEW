# Scientific Validation Round 01 — Closing Audit

Date: 2026-09-06  
Lineage: issue #1123 · supersedes the unmerged documentation draft #1124.

## 1. Objective

Close the engineering/preparation audit for the first benchmark-grade NutEV scientific validation round without modifying the frozen scientific candidate and without confusing later product development with evidence about that candidate.

## 2. Frozen scientific authority

Frozen validation runtime candidate:

```text
6aa7a5fe6009776e611ca3e1506486606b05f4f6
```

Current scientific verdict:

```text
B — DEMOTE
```

This remains the canonical state because an independent human gold-standard retrieval benchmark has not yet been completed. Engineering tests and later product improvements do not promote this verdict.

The stable `v1.0.0` release/Zenodo archive remain immutable and outside this validation freeze.

Canonical status/freeze sources:

- `validation/SCIENTIFIC_VALIDATION_STATUS.md`;
- `validation/VALIDATION_FREEZE.md`;
- `validation/BENCHMARK_PREREGISTRATION.md`;
- `validation/PREREGISTRATION_AMENDMENTS.md`.

## 3. Product-main boundary

The current product `main` is intentionally allowed to evolve independently from the frozen validation candidate. In September 2026 the public product became search/classification-first and advanced review/PRESS/validation/synthesis workflows were hibernated under the advanced laboratory.

Those changes do **not** change the runtime SHA under scientific test. Results from later `main` commits must never be retroactively attributed to `6aa7a5fe...`.

Any scientific benchmark of a later runtime is a new candidate and requires explicit candidate identity/versioning.

## 4. Participant identity and custody — engineering gap closed

Participant identities are runtime/private configuration, not source-code constants.

Canonical contract:

```text
validation/RUNTIME_PARTICIPANT_IDENTITY_AND_CUSTODY_PROTOCOL.md
```

Canonical production packet path:

```bash
python tools/build_assessor_packets.py \
  --pool validation/data/VALIDATION_BLINDED_POOL.csv \
  --assessor-count 2 \
  --output-dir validation/data/validation_assessor_packets \
  --manifest validation/data/VALIDATION_ASSESSOR_PACKETS_MANIFEST.json
```

The tooling now:

- generates opaque `assessor_<digest>` slots at runtime;
- requires at least two assessor slots;
- permits a configurable assessor count without changing source code;
- keeps real human identity/contact mapping outside Git;
- preserves independently shuffled assessor packets;
- fails closed on prohibited ranking/system leakage;
- records only opaque operational identity in public benchmark artifacts.

Opaque IDs do not prove human independence. The operator remains responsible for assigning genuinely independent assessors and preserving blinding/custody.

## 5. What engineering preparation proves

The repository has engineering evidence for deterministic execution, input/output integrity, taxonomy/runtime guardrails and benchmark tooling.

That evidence permits scientific testing. It does **not** prove:

- scientific retrieval recall or precision;
- superiority to baselines;
- MAP/MRR/nDCG benefit;
- taxonomy validity against experts;
- work-level deduplication validity;
- provider incremental value;
- ranking-weight validity;
- absence of metadata bias;
- quarantine recall safety;
- external generalization;
- clinical validity.

Those remain scientific/empirical questions.

## 6. Critical blocker

The remaining blocker for Round 01 is **independent human scientific evidence**.

The round cannot move above `B — DEMOTE` until blinded human assessments create an adjudicated gold standard and the frozen candidate is compared with preregistered baselines under the frozen benchmark protocol.

No UI state, ranking score, search classification, automated reviewer, LLM output or heuristic may substitute for those human labels.

## 7. Human-role gate

Before labeling begins, privately assign:

- [ ] at least two independent assessors;
- [ ] one external-test custodian;
- [ ] one human adjudicator, or an explicitly documented adjudication arrangement.

A person may hold more than one role only if preregistered blinding and custody remain valid.

External-test evidence must remain inaccessible to the validation-stage analyst until the continuation decision is locked.

No real participant identity belongs in the public repository or benchmark packet manifest.

## 8. Phase 1 — reproduce frozen candidate output

- [ ] checkout exact runtime `6aa7a5fe6009776e611ca3e1506486606b05f4f6` in a clean worktree/clone;
- [ ] run the canonical reference-engine workflow for that candidate;
- [ ] preserve the eligible `reference_ranking.jsonl` used for the benchmark;
- [ ] preserve `AUDIT_MANIFEST.json` and source/run manifests/hashes;
- [ ] do not substitute a later `main` ranking.

## 9. Phase 2 — build label-blind benchmark rankings

Required outputs:

- [ ] `validation/data/BENCHMARK_RANKINGS.csv`;
- [ ] `validation/data/BENCHMARK_RANKINGS_MANIFEST.json`.

Require:

```text
label_blind_build = true
gold_standard_consumed = false
candidate_runtime_sha = 6aa7a5fe6009776e611ca3e1506486606b05f4f6
```

Do not calculate promotional scientific metrics at this stage.

## 10. Phase 3 — build physically separate blinded pools

Primary comparison systems and depth remain governed by the preregistration/runbook.

Validation artifacts:

- [ ] `VALIDATION_BLINDED_POOL.csv`;
- [ ] `VALIDATION_POOL_AUDIT.csv`;
- [ ] `VALIDATION_POOL_MANIFEST.json`.

External-test artifacts must be built and stored under custodian control.

Pool audit files contain system membership/ranking information and must never be shown to assessors before initial decisions are locked.

## 11. Phase 4 — independent blinded assessment

Each assessor receives only:

- their own opaque-ID packet/session;
- frozen question definitions;
- relevance instructions necessary to judge the item.

They must not receive:

- pool audit files;
- benchmark rankings;
- NutEV scores/ranks/taxonomy;
- another assessor's decisions.

Each row requires:

- `relevance_grade` 0/1/2;
- concise human reason;
- decision timestamp;
- unchanged opaque assessor ID;
- truthful `blind_to_nutev` status.

Broken blinding must be recorded rather than hidden.

## 12. Phase 5 — consolidation and adjudication

- [ ] preserve completed raw assessor packets immutably;
- [ ] build `VALIDATION_ASSESSMENTS.csv`;
- [ ] mark unanimous judgments `AGREED`;
- [ ] send disagreements to a human adjudicator;
- [ ] build `VALIDATION_GOLD_STANDARD.csv`;
- [ ] never average or algorithmically choose between conflicting human grades.

The adjudicator may be represented by an opaque operational ID; the real identity remains private operational data.

## 13. Phase 6 — gold-standard gate

Before scientific metrics, require the canonical gold validator to demonstrate process completeness:

```text
status = PASS
pool_assessment_coverage_fraction = 1.0
pool_gold_coverage_fraction = 1.0
minimum_assessors_per_reference >= 2
```

Validator PASS proves completeness/coherence of the labeling process, not correctness of the scientific judgment.

## 14. Phase 7 — validation-only comparison

Compute the preregistered validation metrics against declared baselines, including the required ranking/retrieval metrics and workload milestones.

Preserve at minimum:

- [ ] `VALIDATION_BENCHMARK_RESULTS.csv`;
- [ ] `VALIDATION_COMPARISON.json`;
- [ ] `VALIDATION_PAIRED.csv`.

External-test labels/results remain sealed during this stage.

## 15. Phase 8 — continuation decision

Only the protocol-defined locked outcomes are valid:

```text
CONTINUE_TO_EXTERNAL
STOP_AT_B
```

Before external evidence is released, preserve:

- gold validation report;
- validation metrics;
- paired output;
- comparison summary;
- exact runtime/tooling SHAs;
- dated locked continuation decision.

If validation fails, retain `B — DEMOTE`. Do not inspect external evidence to rescue, tune or narratively optimize the same frozen candidate.

## 16. Phase 9 — external test

Only after a valid locked `CONTINUE_TO_EXTERNAL` decision:

- [ ] custodian releases the sealed external evidence;
- [ ] validate external gold completeness;
- [ ] compute external-test-only metrics;
- [ ] apply preregistered defined-use criteria;
- [ ] record final scientific verdict.

A passing defined-use benchmark supports only the preregistered represented domain/question population and prioritization task. It does not establish exhaustive global discovery, study quality, certainty or clinical validity.

## 17. Verdict interpretation

### B — DEMOTE

Scientific incremental benefit has not been demonstrated. This remains the current state.

### C — SCIENTIFIC CANDIDATE

Validation criteria pass, but independent external generalization is not yet demonstrated.

### D — VALIDATED FOR DEFINED USE

Preregistered validation and external-test criteria pass. Claims remain limited to the validated use/domain.

No benchmark result in this round authorizes a clinical recommendation, GRADE certainty statement or broad evidence-synthesis claim by itself.

## 18. Separate secondary evidence

After the primary benchmark, additional methodology evidence may address:

1. taxonomy validity against independent human classifications;
2. work-level deduplication precision/recall;
3. quarantine recall-loss audit;
4. ranking sensitivity/ablation;
5. leave-one-provider-out contribution;
6. metadata availability bias;
7. controlled user-workload benefit;
8. discovery coverage outside the common candidate pool.

These strengthen the methodology evidence base but do not replace the principal blinded benchmark.

## 19. Artifact preservation

Preserve hashes/copies for each round of at least:

- frozen questions;
- frozen candidate output + audit manifest;
- benchmark rankings + manifest;
- split-specific blinded pools + manifests;
- segregated pool audits;
- assessor packet manifests and immutable raw completed packets;
- raw assessments;
- adjudicated gold standards;
- gold validation reports;
- benchmark result tables;
- paired comparison outputs;
- locked continuation decision;
- exact runtime and tooling SHAs.

Real participant mappings, reviewer credentials/private tokens and contact details remain private operational records and are not public scientific artifacts.

Never rewrite an unfavorable benchmark artifact to produce a cleaner narrative.

## 20. Leakage failure rule

If a validation-stage analyst receives external-test labels, performance, error analysis or system-specific external judgments before the continuation decision is locked, record the breach. The affected external round must not be represented as sealed evidence for `D — VALIDATED FOR DEFINED USE`; a new independent external round is required for that claim.

## 21. Definition of done

Round 01 is scientifically complete only when all applicable items exist:

- [ ] frozen runtime output and audit manifest;
- [ ] label-blind benchmark rankings and manifest;
- [ ] runtime-configured independent assessor packets/sessions;
- [ ] complete independent human judgments;
- [ ] human adjudication of every conflict;
- [ ] validated gold standard;
- [ ] validation metrics and baseline comparison;
- [ ] locked continuation decision;
- [ ] external test if authorized;
- [ ] final B/C/D verdict;
- [ ] updated validation report/limitations;
- [ ] immutable artifact hashes and provenance.

## 22. Current closing assessment

**Engineering/preparation:** ready for benchmark execution under the canonical runbook/protocol.  
**Participant identity/custody tooling:** closed by runtime opaque-ID contract.  
**Independent human benchmark:** not executed/completed.  
**Scientific verdict:** **B — DEMOTE**.  
**Next non-automatable action:** assign qualified independent human participants under private custody and execute the blinded benchmark without exposing system/ranking information.
