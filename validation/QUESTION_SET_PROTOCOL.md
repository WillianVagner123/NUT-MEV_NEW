# Independent Question Set Protocol

## Purpose

Define and freeze benchmark questions without using NutEV rankings, scores, taxonomy matches or performance to choose questions that favor the system.

The final question set is a **human/editorial input** to the benchmark. Software may validate its schema and declarations, but it cannot self-certify a generated question set as scientifically independent.

## Canonical file

Final approved questions must be stored as:

```text
validation/data/QUESTIONS.csv
```

using:

```text
validation/templates/QUESTIONS_TEMPLATE.csv
```

Do not create or overwrite `QUESTIONS.csv` until the editorial content is approved.

## Required audit fields

Every row must contain:

- `question_id` — stable and unique;
- `question_text` — complete relevance question shown to assessors;
- `split` — `development`, `validation`, or `external_test`;
- `sampling_stratum` — sampling/audit category only;
- `outside_historical_focus` — explicit boolean declaration used to enforce the pre-specified outside-focus floor;
- `freeze_date` — ISO `YYYY-MM-DD`;
- `human_approved_by` — pseudonymized or otherwise auditable human editor/reviewer identifier;
- `human_approval_date` — ISO `YYYY-MM-DD`, not later than the freeze date;
- explicit inclusion context through population/exposure/outcome and/or `notes`.

Other template fields should be completed whenever applicable so that independent assessors can apply the question consistently.

`human_approved_by` is a **declaration**, not proof that software can verify human identity or scientific independence.

## Coverage targets

The complete benchmark should deliberately represent multiple use cases, including:

- dietary patterns;
- cardiometabolic prevention/risk;
- diabetes;
- obesity;
- behavior/adherence;
- food literacy/cooking;
- social determinants/food environment;
- implementation/models of care;
- at least two topics outside the Engine's historical focus;
- multilingual questions or eligible literature in English, Portuguese and Spanish when scientifically appropriate.

These are sampling strata, not relevance labels.

## Independence safeguards

Before question freeze, editors may use external scientific/clinical domain knowledge and independently chosen source frameworks. They must **not** use:

- NutEV result counts for candidate wording;
- NutEV rank positions;
- NutEV score/taxonomy matches;
- observed benchmark performance;
- external-test labels.

If a question is changed because of a NutEV retrieval result, it is not independent for the same sealed test round and must be moved to development or a future round.

## Split policy

- `development`: pipeline debugging only; may be inspected repeatedly and cannot support scientific promotion.
- `validation`: used to decide whether the already frozen candidate has sufficient signal to justify sealed external testing.
- `external_test`: sealed until validation decisions are final. Its labels cannot modify the frozen candidate.

The pre-registered defined-use criterion requires at least **12 benchmark-grade external-test questions**. More questions may be needed for adequate domain representation and precision; 12 is only the operational minimum floor.

The complete set must contain all three splits before the benchmark-grade freeze.

## Automated freeze gate

After humans have approved the content, run:

```bash
python tools/freeze_validation_questions.py \
  --questions validation/data/QUESTIONS.csv \
  --manifest validation/data/QUESTIONS_FREEZE_MANIFEST.json
```

The default gate checks:

- complete template schema;
- valid/unique question IDs;
- nonempty question text and no exact normalized duplicate question wording;
- valid split and at least one question in every split;
- at least 12 `external_test` questions;
- at least two questions declared `outside_historical_focus = true`;
- nonempty sampling stratum;
- explicit inclusion context;
- ISO freeze/approval dates;
- nonempty human approval declaration;
- human approval date not later than freeze date.

A successful manifest records SHA-256 of the exact `QUESTIONS.csv`, split counts, strata counts, outside-focus count and declared approvers.

The manifest explicitly records:

```text
semantic_independence_verified_by_software = false
```

because schema validation cannot prove scientific independence, representativeness or quality of question wording.

## Freeze checklist

Before a row becomes part of the benchmark-grade question set:

1. wording and eligibility criteria are understandable without NutEV output;
2. `question_id` is stable and unique;
3. split is fixed;
4. languages/document types/time window are explicit where relevant;
5. `sampling_stratum` is assigned for sampling/audit only, not used to define relevance automatically;
6. `outside_historical_focus` is truthfully declared;
7. question is approved by a human editor/reviewer and approval metadata are recorded;
8. `freeze_date` is recorded;
9. `freeze_validation_questions.py` returns PASS and writes the freeze manifest;
10. `QUESTIONS.csv` and `QUESTIONS_FREEZE_MANIFEST.json` are preserved unchanged before label-blind rankings and human relevance labeling begin.

If the question file changes after the manifest is produced, its SHA changes and the old manifest no longer describes the active question set. Generate a new benchmark round/freeze rather than silently replacing the file.

## Prohibition on retroactive optimization

After any `external_test` relevance label is observed, do not rewrite external questions, change their split, remove difficult questions or add favorable questions to the same benchmark round.

A materially changed question set is a new benchmark round and must receive a new freeze and audit trail.

## Current state

**PROTOCOL_AND_FREEZE_GATE_READY / FINAL_QUESTIONS_NOT_YET_HUMAN_APPROVED.**

No question wording is declared scientifically independent merely because it passes the automated freeze gate.
