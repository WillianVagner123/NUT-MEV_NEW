# Human Validation Runbook

This runbook executes the first benchmark-grade attempt to move NutEV above **B — DEMOTE** without circular validation.

Canonical participant identity and custody rules are defined in:

```text
validation/RUNTIME_PARTICIPANT_IDENTITY_AND_CUSTODY_PROTOCOL.md
```

That protocol is normative for participant setup. Real assessor, adjudicator and custodian identities are private runtime/operational data and must not be hard-coded or committed as production configuration.

Frozen runtime under test:

```text
6aa7a5fe6009776e611ca3e1506486606b05f4f6
```

The current `main` may contain benchmark tooling newer than that SHA. The runtime itself must not be changed for this benchmark round.

## 0. Human gate before execution

Do not start benchmark labeling until a human/editorial reviewer approves and freezes:

```text
validation/data/QUESTIONS.csv
```

according to `validation/QUESTION_SET_PROTOCOL.md`.

No script in this repository is authorized to invent final independent questions or human relevance labels.

Assign an **external-test custodian** before labeling. The real identity and contact mapping for this role remain private operational data outside Git. This person/team may hold sealed external-test packets and labels, but must not provide them to the analyst/developer making the validation-stage continuation decision.

## 1. Produce a real frozen-runtime output

In a clean clone/worktree, checkout the exact candidate:

```bash
git checkout 6aa7a5fe6009776e611ca3e1506486606b05f4f6
```

Run the normal NutEV reference-engine workflow. Preserve, without editing:

- the eligible `reference_ranking.jsonl` used for the benchmark;
- `AUDIT_MANIFEST.json`;
- source/run manifests and hashes produced by that run.

The benchmark must use the output of the frozen candidate, not a later `main` ranking silently substituted for it.

## 2. Return to current benchmark tooling

Return to current `main` after the frozen output is safely preserved:

```bash
git checkout main
git pull --ff-only origin main
```

Do not overwrite the preserved frozen-run files.

## 3. Build all label-blind rankings once

```bash
python tools/build_scientific_benchmark_rankings.py \
  --questions validation/data/QUESTIONS.csv \
  --frozen-ranking <FROZEN_REFERENCE_RANKING.jsonl> \
  --candidate-sha 6aa7a5fe6009776e611ca3e1506486606b05f4f6 \
  --output validation/data/BENCHMARK_RANKINGS.csv \
  --manifest validation/data/BENCHMARK_RANKINGS_MANIFEST.json
```

The manifest must show:

```text
label_blind_build = true
gold_standard_consumed = false
candidate_runtime_sha = 6aa7a5fe6009776e611ca3e1506486606b05f4f6
```

Do not calculate scientific metrics at this stage.

## 4. Build physically separate primary pools by split

The primary pool uses only `nutev_full` and `lexical_baseline`, depth 100.

### Validation pool

```bash
python tools/build_blinded_judgment_pool.py \
  --rankings validation/data/BENCHMARK_RANKINGS.csv \
  --metadata <FROZEN_REFERENCE_RANKING.jsonl> \
  --systems nutev_full,lexical_baseline \
  --split validation \
  --depth 100 \
  --blinded-output validation/data/VALIDATION_BLINDED_POOL.csv \
  --audit-output validation/data/VALIDATION_POOL_AUDIT.csv \
  --manifest validation/data/VALIDATION_POOL_MANIFEST.json
```

### External-test pool

Build this under the external custodian's control:

```bash
python tools/build_blinded_judgment_pool.py \
  --rankings validation/data/BENCHMARK_RANKINGS.csv \
  --metadata <FROZEN_REFERENCE_RANKING.jsonl> \
  --systems nutev_full,lexical_baseline \
  --split external_test \
  --depth 100 \
  --blinded-output <SEALED>/EXTERNAL_BLINDED_POOL.csv \
  --audit-output <SEALED>/EXTERNAL_POOL_AUDIT.csv \
  --manifest <SEALED>/EXTERNAL_POOL_MANIFEST.json
```

Pool audit files contain system membership/ranks. They must not be shown to assessors before initial judgments are locked.

Development may be built analogously with `--split development`, but development evidence cannot promote the product.

## 5. Generate independent assessor packets

The canonical production path generates opaque assessor IDs at runtime. It does not require names, emails, GitHub accounts or fixed `assessor_A` / `assessor_B` identities in source control.

For validation, with the current scientific minimum of two independent assessors:

```bash
python tools/build_assessor_packets.py \
  --pool validation/data/VALIDATION_BLINDED_POOL.csv \
  --assessor-count 2 \
  --output-dir validation/data/validation_assessor_packets \
  --manifest validation/data/VALIDATION_ASSESSOR_PACKETS_MANIFEST.json
```

`--assessor-count` is runtime configurable and may be greater than two without changing application source code. The real-person mapping from each generated opaque ID to the human participant must remain in a private operational registry outside Git.

An advanced path may supply explicit `--assessor-id` values only when they are already opaque, non-identifying runtime IDs. Synthetic labels such as `assessor_A` may remain in unit tests/examples but are not the canonical production identity model.

For external test, run the same tool against `<SEALED>/EXTERNAL_BLINDED_POOL.csv` and write all outputs under `<SEALED>` under custodian control.

Each assessor receives only their own packet plus the frozen question definitions/relevance instructions. Do not provide:

- any pool audit file;
- `BENCHMARK_RANKINGS.csv`;
- NutEV scores/ranks/taxonomy;
- another assessor's decisions.

## 6. Human initial assessment

Each assessor independently completes every row in their packet:

- `relevance_grade`: `0`, `1`, or `2`;
- `reason`: concise justification;
- `decision_timestamp`;
- keep the generated opaque `assessor_id` unchanged;
- keep `blind_to_nutev = true` only if the assessor actually remained blind.

Scale:

- `0` — irrelevant;
- `1` — relevant/peripheral or useful;
- `2` — directly relevant/key reference.

If blindness is broken for an item/assessor, do not falsely mark it true; the benchmark-grade validator must reject that evidence.

External-test assessors/custodian may complete their work before the validation decision, but the external completed packets, labels, gold, metrics and error analysis must remain sealed from the validation-stage analyst.

## 7. Consolidate raw assessments separately

After initial assessor packets are locked, concatenate rows by split.

Validation:

```text
validation/data/VALIDATION_ASSESSMENTS.csv
```

External, under custody:

```text
<SEALED>/EXTERNAL_ASSESSMENTS.csv
```

Preserve original completed packets as immutable raw evidence. Do not average or overwrite disagreeing grades.

## 8. Human adjudication separately by split

Validation final gold:

```text
validation/data/VALIDATION_GOLD_STANDARD.csv
```

External final gold, kept sealed:

```text
<SEALED>/EXTERNAL_GOLD_STANDARD.csv
```

For every pool item:

- unanimous assessors: common grade + `adjudication_status = AGREED`;
- disagreement: human adjudicator supplies final `relevance_grade`, `adjudication_status = RESOLVED`, opaque `adjudicator_id`, and `adjudication_timestamp`.

The real adjudicator identity remains private operational data outside Git unless separately disclosed through an approved scientific reporting process.

A script must not choose the winning assessor or resolve conflicts automatically.

## 9. Validate the validation gold before metrics

```bash
python tools/validate_gold_standard.py \
  --pool validation/data/VALIDATION_BLINDED_POOL.csv \
  --assessments validation/data/VALIDATION_ASSESSMENTS.csv \
  --gold validation/data/VALIDATION_GOLD_STANDARD.csv \
  --output validation/data/VALIDATION_GOLD_VALIDATION.json
```

Proceed only if:

```text
status = PASS
pool_assessment_coverage_fraction = 1.0
pool_gold_coverage_fraction = 1.0
minimum_assessors_per_reference >= 2
```

A validator `PASS` proves process completeness/coherence, not correctness of scientific judgment.

## 10. Calculate **validation-only** metrics

```bash
python tools/evaluate_scientific_validation.py \
  --gold-standard validation/data/VALIDATION_GOLD_STANDARD.csv \
  --rankings validation/data/BENCHMARK_RANKINGS.csv \
  --split validation \
  --require-judged-through 100 \
  --output validation/data/VALIDATION_BENCHMARK_RESULTS.csv
```

The evaluator reads only validation rankings. External gold is not needed and must remain sealed.

## 11. Apply the validation continuation gate

```bash
python tools/compare_scientific_benchmark.py \
  --results validation/data/VALIDATION_BENCHMARK_RESULTS.csv \
  --split validation \
  --summary-output validation/data/VALIDATION_COMPARISON.json \
  --paired-output validation/data/VALIDATION_PAIRED.csv
```

Only if:

```text
validation_evidence_status = CONTINUATION_CRITERIA_PASS
```

may the frozen candidate be considered for **C — SCIENTIFIC_CANDIDATE** and the sealed external-test evidence be released for analysis.

If validation fails, keep **B — DEMOTE** for this candidate. Do not inspect external labels to rescue, retune or narratively optimize the same candidate.

## 12. Lock the validation decision

Before any external-test label/result is released, preserve:

- validation gold validation report;
- validation benchmark results;
- validation paired output;
- validation comparison summary;
- a dated decision stating `CONTINUE_TO_EXTERNAL` or `STOP_AT_B`;
- exact runtime and tooling SHAs.

If the decision is `STOP_AT_B`, the sealed external set should remain unopened for this candidate unless the protocol explicitly documents a non-promotional diagnostic analysis.

## 13. Release and validate external-test evidence only after CONTINUE

The custodian releases the external pool/assessments/gold only after the locked validation decision.

First validate process completeness:

```bash
python tools/validate_gold_standard.py \
  --pool <SEALED_RELEASE>/EXTERNAL_BLINDED_POOL.csv \
  --assessments <SEALED_RELEASE>/EXTERNAL_ASSESSMENTS.csv \
  --gold <SEALED_RELEASE>/EXTERNAL_GOLD_STANDARD.csv \
  --output validation/data/EXTERNAL_GOLD_VALIDATION.json
```

Require the same 100% pool coverage and at least two assessors per item.

## 14. Calculate external-test-only metrics

```bash
python tools/evaluate_scientific_validation.py \
  --gold-standard <SEALED_RELEASE>/EXTERNAL_GOLD_STANDARD.csv \
  --rankings validation/data/BENCHMARK_RANKINGS.csv \
  --split external_test \
  --require-judged-through 100 \
  --output validation/data/EXTERNAL_BENCHMARK_RESULTS.csv
```

Then apply the preregistered comparison:

```bash
python tools/compare_scientific_benchmark.py \
  --results validation/data/EXTERNAL_BENCHMARK_RESULTS.csv \
  --split external_test \
  --summary-output validation/data/EXTERNAL_TEST_COMPARISON.json \
  --paired-output validation/data/EXTERNAL_TEST_PAIRED.csv
```

A defined-use promotion requires all preregistered criteria, including at least 12 benchmark-grade external questions and:

```text
external_evidence_status = DEFINED_USE_CRITERIA_PASS
```

If it passes, the strongest supported claim is limited to prioritization within the common pool and represented benchmark domain/question population. It does not establish global discovery recall, methodological evidence quality or clinical validity.

## 15. Discovery coverage remains separate

Do not use the common-pool result to claim exhaustive retrieval. `DISCOVERY_COVERAGE` requires independently obtained relevant references that may be outside the NutEV corpus and a separately auditable comparison.

## 16. Artifact preservation

For each benchmark round preserve hashes/copies of at least:

- frozen `QUESTIONS.csv`;
- frozen candidate output and `AUDIT_MANIFEST.json`;
- benchmark rankings + manifest;
- split-specific blinded pools + manifests;
- segregated pool audits;
- assessor packet manifests and completed raw packets;
- split-specific raw assessments;
- split-specific adjudicated gold standards;
- gold validation reports;
- split-specific benchmark results;
- paired comparison outputs;
- locked validation continuation decision;
- exact Git SHAs of frozen runtime and benchmark tooling.

Participant real-identity/contact mappings and reviewer credentials remain private operational records and are not part of the public artifact bundle.

Never rewrite unfavorable benchmark artifacts to create a cleaner narrative. A failed validation round is scientific evidence and must remain auditable.

## Leakage failure rule

If an analyst responsible for validation-stage candidate decisions obtains external-test relevance labels, external performance, external error analysis or system-specific external judgments before the continuation decision is locked, record the breach. The affected external round must not be presented as sealed evidence for `D — VALIDATED_FOR_DEFINED_USE`; use a new independent external round for that claim.
