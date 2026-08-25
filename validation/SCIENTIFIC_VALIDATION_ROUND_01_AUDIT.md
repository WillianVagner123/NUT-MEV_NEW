# Scientific Validation Round 01 — Closing Audit

Date: 2026-08-25

Issue tracker: #1123

## Objective
Close the first benchmark-grade scientific validation round for the frozen NutEV runtime without modifying the candidate under test.

## Frozen scientific candidate

`6aa7a5fe6009776e611ca3e1506486606b05f4f6`

Current scientific verdict: **B — DEMOTE**.

The stable `v1.0.0` release and Zenodo archive remain immutable and outside this validation round.

## Configuration rule — no participant hard-coding

Human participants are **runtime/private configuration**, never source-code constants and never repository metadata.

Do not commit reviewer names, e-mails, phone numbers, personal identifiers, custodian identity, or adjudicator identity to Git.

The validation system must use:

- a generated `round_id` for each scientific round;
- opaque per-participant `assessor_id` values supplied/generated at round preparation time;
- private reviewer tokens generated at runtime;
- participant-to-role mapping stored only in the private operational layer;
- a minimum of two independent assessors enforced by validation logic, without assuming exactly two forever;
- role capabilities (`assessor`, `adjudicator`, `external_custodian`) as configuration/state, not hard-coded people.

Labels such as “A/B” in documentation are explanatory placeholders only. They are not canonical IDs and must not be embedded as production identities.

The existing packet builder already accepts repeated runtime `--assessor-id` arguments, and the validation server creates unique round IDs and private reviewer tokens dynamically. The canonical operating flow must preserve that behavior.

## Release boundary

The following are already closed for this round:

- stable software identity `v1.0.0`;
- GitHub release and Zenodo archive;
- engineering gate for the frozen validation candidate;
- deterministic runtime and guardrail checks;
- frozen benchmark question set and manifest;
- blinded reviewer, adjudication, gold-standard, metrics, and decision-lock tooling.

No new feature is required before beginning human validation.

## Critical blocker

The remaining blocker is **independent human scientific evidence**.

The round is not complete until blinded human judgments produce an adjudicated gold standard and NutEV is compared against the preregistered lexical baseline.

## Human-role gate

Before execution, configure the required roles in the private/runtime layer:

- [ ] at least two independent assessors;
- [ ] one external-test custodian;
- [ ] one human adjudicator or an explicitly documented adjudication arrangement.

A person may only hold multiple roles where the preregistered blinding and custody rules still remain valid. External-test information must remain inaccessible to the validation-stage analyst until the continuation decision is locked.

No real person identity belongs in this repository.

## Phase 1 — frozen runtime reproduction

- [ ] Checkout the exact frozen candidate SHA.
- [ ] Execute the canonical NutEV reference-engine workflow.
- [ ] Preserve the eligible `reference_ranking.jsonl`.
- [ ] Preserve `AUDIT_MANIFEST.json`.
- [ ] Preserve source/run manifests and hashes.
- [ ] Do not substitute a later `main` ranking.

## Phase 2 — label-blind benchmark build

- [ ] Build `validation/data/BENCHMARK_RANKINGS.csv`.
- [ ] Build `validation/data/BENCHMARK_RANKINGS_MANIFEST.json`.
- [ ] Verify `label_blind_build = true`.
- [ ] Verify `gold_standard_consumed = false`.
- [ ] Verify `candidate_runtime_sha = 6aa7a5fe6009776e611ca3e1506486606b05f4f6`.

## Phase 3 — blinded pools

Primary systems:

- `nutev_full`
- `lexical_baseline`

Primary depth: 100.

Validation:

- [ ] Build `VALIDATION_BLINDED_POOL.csv`.
- [ ] Build `VALIDATION_POOL_AUDIT.csv`.
- [ ] Build `VALIDATION_POOL_MANIFEST.json`.

External test:

- [ ] Build physically separate external pool under custodian control.
- [ ] Keep external audit membership/ranks sealed.
- [ ] Do not expose external judgments or metrics before the validation decision lock.

## Phase 4 — independent human assessment

Each assessor receives only their own private session/packet plus frozen question definitions and relevance instructions.

They must not receive:

- pool audit files;
- benchmark rankings;
- NutEV scores/ranks/taxonomy;
- another assessor's decisions.

For every item, each assessor records:

- `relevance_grade`: 0, 1, or 2;
- concise reason;
- timestamp;
- unchanged opaque assessor identifier;
- truthful blindness status.

Interpretation:

- `0`: irrelevant;
- `1`: relevant/peripheral or useful;
- `2`: directly relevant/key reference.

## Phase 5 — consolidation and adjudication

- [ ] Preserve completed raw assessor packets/sessions immutably.
- [ ] Build `VALIDATION_ASSESSMENTS.csv`.
- [ ] Mark unanimous judgments `AGREED`.
- [ ] Resolve disagreements only through a human adjudicator.
- [ ] Build `VALIDATION_GOLD_STANDARD.csv`.
- [ ] Do not average conflicting grades automatically.

## Phase 6 — gold-standard gate

Run canonical gold validation and require:

- [ ] `status = PASS`;
- [ ] `pool_assessment_coverage_fraction = 1.0`;
- [ ] `pool_gold_coverage_fraction = 1.0`;
- [ ] `minimum_assessors_per_reference >= 2`.

Do not compute promotional scientific metrics if this gate fails.

## Phase 7 — validation-only metrics

Generate at minimum:

- precision/recall@k;
- MRR;
- MAP;
- nDCG;
- preregistered workload milestones;
- paired comparison outputs.

Required artifacts:

- [ ] `VALIDATION_BENCHMARK_RESULTS.csv`;
- [ ] `VALIDATION_COMPARISON.json`;
- [ ] `VALIDATION_PAIRED.csv`.

## Phase 8 — continuation decision

Only two valid locked decisions:

- `CONTINUE_TO_EXTERNAL`
- `STOP_AT_B`

Before external evidence is released, preserve:

- gold validation report;
- validation metrics;
- paired output;
- comparison summary;
- exact runtime and tooling SHAs;
- dated locked decision.

If validation fails, retain **B — DEMOTE** and do not inspect external evidence to rescue or tune the same candidate.

## Phase 9 — external test

Run only after a locked `CONTINUE_TO_EXTERNAL` decision.

- [ ] Custodian releases the sealed external evidence.
- [ ] Validate external gold completeness.
- [ ] Compute external-test-only metrics.
- [ ] Apply preregistered defined-use criteria.
- [ ] Require at least the preregistered external-question floor.
- [ ] Record the final scientific verdict.

## Final verdict interpretation

### B — DEMOTE
Scientific incremental benefit not demonstrated.

### C — SCIENTIFIC CANDIDATE
Validation evidence passes, but external generalization is not yet demonstrated.

### D — VALIDATED FOR DEFINED USE
Preregistered validation and external-test criteria pass. Claims must remain limited to the represented benchmark domain/question population and prioritization task.

Passing this benchmark does not establish exhaustive global discovery, methodological study quality, or clinical validity.

## Secondary evidence after the primary benchmark

After the principal validation round, prioritize:

1. taxonomy validation against independent human classifications;
2. work-level deduplication benchmark;
3. quarantine recall-loss audit;
4. ranking sensitivity/ablation analysis;
5. leave-one-provider-out contribution;
6. metadata availability bias;
7. controlled user-workload benefit.

These strengthen a methodology paper but do not replace the primary blinded benchmark.

## Product-development boundary

Product work on `main` may continue separately, including global-search and deployment work.

For this scientific round, do not change or retroactively attribute to the frozen candidate:

- ranking weights;
- queries;
- taxonomy;
- identity rules;
- provider logic;
- runtime implementation.

Any runtime change creates a new scientific candidate.

## Definition of done

Scientific Validation Round 01 is complete only when all applicable items below exist:

- [ ] frozen runtime output and audit manifest;
- [ ] label-blind benchmark rankings and manifest;
- [ ] runtime-configured independent assessor sessions and completed judgments;
- [ ] 100% judged validation pool;
- [ ] human adjudication of every conflict;
- [ ] validated gold standard;
- [ ] validation metrics and baseline comparison;
- [ ] locked continuation decision;
- [ ] external test if authorized;
- [ ] final A/B/C/D verdict;
- [ ] updated scientific validation report and limitations;
- [ ] preserved hashes and immutable round artifacts;
- [ ] next release decision made only after the scientific verdict.

## Immediate owner actions

The only non-automatable actions required to start the round are operational, not code changes:

1. choose the qualified people who will fill the required roles;
2. configure them in the private/runtime layer using opaque IDs;
3. distribute each private reviewer link only to its intended participant;
4. keep the external-test custody mapping outside Git and inaccessible to the validation-stage analyst.

Everything downstream should follow the canonical validation tooling and fail closed when required artifacts or human decisions are absent.
