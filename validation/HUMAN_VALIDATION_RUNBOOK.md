# Human Validation Runbook

This runbook executes the first benchmark-grade attempt to move NutEV above **B — DEMOTE** without circular validation.

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

## 3. Build all label-blind rankings

Example:

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

## 4. Build the primary blinded judgment pool

Use only the preregistered primary pair by default:

```bash
python tools/build_blinded_judgment_pool.py \
  --rankings validation/data/BENCHMARK_RANKINGS.csv \
  --metadata <FROZEN_REFERENCE_RANKING.jsonl> \
  --systems nutev_full,lexical_baseline \
  --depth 100 \
  --blinded-output validation/data/BLINDED_PRIMARY_POOL.csv \
  --audit-output validation/data/PRIMARY_POOL_AUDIT.csv \
  --manifest validation/data/PRIMARY_POOL_MANIFEST.json
```

**Segregate `PRIMARY_POOL_AUDIT.csv`.** It contains system membership/ranks and must not be shown to assessors before their initial judgments are locked.

## 5. Generate independent assessor packets

Use pseudonymized assessor IDs. Example with two assessors:

```bash
python tools/build_assessor_packets.py \
  --pool validation/data/BLINDED_PRIMARY_POOL.csv \
  --assessor-id assessor_A \
  --assessor-id assessor_B \
  --output-dir validation/data/assessor_packets \
  --manifest validation/data/ASSESSOR_PACKETS_MANIFEST.json
```

Each assessor gets only their own `ASSESSOR_<id>.csv` plus the frozen question definitions/relevance instructions.

Do not provide:

- `PRIMARY_POOL_AUDIT.csv`;
- `BENCHMARK_RANKINGS.csv`;
- NutEV scores/ranks/taxonomy;
- another assessor's decisions.

## 6. Human initial assessment

Each assessor independently completes every row in their packet:

- `relevance_grade`: `0`, `1`, or `2`;
- `reason`: concise justification;
- `decision_timestamp`;
- keep `assessor_id` unchanged;
- keep `blind_to_nutev = true` only if the assessor actually remained blind.

The grading scale is:

- `0` — irrelevant;
- `1` — relevant/peripheral or useful;
- `2` — directly relevant/key reference.

If blindness is broken for an item/assessor, do not falsely mark it true; the benchmark-grade validator is expected to reject that evidence.

## 7. Consolidate raw assessments

After **all** initial assessor packets are locked, concatenate their rows into:

```text
validation/data/ASSESSMENTS.csv
```

Use the schema in `validation/templates/ASSESSMENTS_TEMPLATE.csv`. Preserve the original completed packets as immutable raw evidence.

Do not average or overwrite disagreeing grades.

## 8. Human adjudication

Create `validation/data/GOLD_STANDARD.csv` using `validation/templates/GOLD_STANDARD_TEMPLATE.csv`.

For each pool item:

- unanimous assessors: copy the common grade and set `adjudication_status = AGREED`;
- disagreement: a human adjudicator sets the final `relevance_grade`, `adjudication_status = RESOLVED`, `adjudicator_id`, and `adjudication_timestamp`.

A script must not choose the winning assessor or resolve conflicts automatically.

The final gold must contain one row for **every** `question_id/reference_id` in `BLINDED_PRIMARY_POOL.csv`.

## 9. Fail-closed process validation

Run:

```bash
python tools/validate_gold_standard.py \
  --pool validation/data/BLINDED_PRIMARY_POOL.csv \
  --assessments validation/data/ASSESSMENTS.csv \
  --gold validation/data/GOLD_STANDARD.csv \
  --output validation/data/GOLD_STANDARD_VALIDATION.json
```

Proceed only if the output reports:

```text
status = PASS
pool_assessment_coverage_fraction = 1.0
pool_gold_coverage_fraction = 1.0
minimum_assessors_per_reference >= 2
```

A validator `PASS` proves process completeness/coherence, not correctness of scientific judgment.

## 10. Calculate metrics only after gold validation PASS

Run:

```bash
python tools/evaluate_scientific_validation.py \
  --gold-standard validation/data/GOLD_STANDARD.csv \
  --rankings validation/data/BENCHMARK_RANKINGS.csv \
  --require-judged-through 100 \
  --output validation/data/BENCHMARK_RESULTS.csv
```

The evaluator fails closed if candidate/baseline results inside the required judged depth are missing judgments. Do not convert unjudged documents to relevance 0.

## 11. Development split

Development may be inspected only to debug the benchmark machinery. It cannot promote the product.

```bash
python tools/compare_scientific_benchmark.py \
  --results validation/data/BENCHMARK_RESULTS.csv \
  --split development \
  --summary-output validation/data/DEVELOPMENT_COMPARISON.json \
  --paired-output validation/data/DEVELOPMENT_PAIRED.csv
```

## 12. Validation split — first possible reversal of B

Run:

```bash
python tools/compare_scientific_benchmark.py \
  --results validation/data/BENCHMARK_RESULTS.csv \
  --split validation \
  --summary-output validation/data/VALIDATION_COMPARISON.json \
  --paired-output validation/data/VALIDATION_PAIRED.csv
```

Only if `validation_evidence_status = CONTINUATION_CRITERIA_PASS` may the frozen candidate be considered for **C — SCIENTIFIC_CANDIDATE** and the sealed external-test result be opened under the preregistered protocol.

If validation fails, keep **B — DEMOTE** for this candidate. Do not alter the same frozen candidate after seeing external-test labels.

## 13. Sealed external test — possible D for a bounded claim

After the validation decision is locked, run:

```bash
python tools/compare_scientific_benchmark.py \
  --results validation/data/BENCHMARK_RESULTS.csv \
  --split external_test \
  --summary-output validation/data/EXTERNAL_TEST_COMPARISON.json \
  --paired-output validation/data/EXTERNAL_TEST_PAIRED.csv
```

A defined-use promotion requires all preregistered criteria, including at least 12 benchmark-grade external questions and `external_evidence_status = DEFINED_USE_CRITERIA_PASS`.

If it passes, the strongest supported claim is limited to prioritization within the common pool and represented benchmark domain/question population. It does not establish global discovery recall, methodological evidence quality or clinical validity.

## 14. Discovery coverage remains separate

Do not use the common-pool result to claim exhaustive retrieval. `DISCOVERY_COVERAGE` requires independently obtained relevant references that may be outside the NutEV corpus and a separately auditable comparison.

## 15. Artifact preservation

For each benchmark round preserve hashes/copies of at least:

- frozen `QUESTIONS.csv`;
- frozen candidate output and `AUDIT_MANIFEST.json`;
- benchmark rankings + manifest;
- blinded primary pool + manifest;
- segregated pool audit;
- assessor packet manifest and completed raw packets;
- consolidated `ASSESSMENTS.csv`;
- adjudicated `GOLD_STANDARD.csv`;
- gold validation report;
- benchmark results;
- paired comparison outputs;
- exact Git SHAs of frozen runtime and benchmark tooling.

Never rewrite unfavorable benchmark artifacts to create a cleaner narrative. A failed validation round is scientific evidence and must remain auditable.
