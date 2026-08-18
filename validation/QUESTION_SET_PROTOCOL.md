# Independent Question Set Protocol

## Purpose

Define and freeze benchmark questions without using NutEV rankings, scores, taxonomy matches or performance to choose questions that favor the system.

The final question set is a **human/editorial input** to the benchmark. Software may validate its schema, but it cannot self-certify a generated question set as independent.

## Canonical file

Final approved questions must be stored as:

```text
validation/data/QUESTIONS.csv
```

using:

```text
validation/templates/QUESTIONS_TEMPLATE.csv
```

Do not create or overwrite `QUESTIONS.csv` until the editorial freeze is approved.

## Required fields

Every row must contain at least:

- `question_id` — stable and unique;
- `question_text` — complete relevance question shown to assessors;
- `split` — `development`, `validation`, or `external_test`;
- `freeze_date`;
- explicit inclusion context through population/exposure/outcome and/or notes when needed.

The remaining template fields should be completed whenever applicable so that two independent assessors can apply the question consistently.

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

## Freeze checklist

Before a row becomes part of the benchmark-grade question set:

1. wording and eligibility criteria are understandable without NutEV output;
2. `question_id` is stable and unique;
3. split is fixed;
4. languages/document types/time window are explicit where relevant;
5. topic is assigned for sampling/audit only, not used to define relevance automatically;
6. question is approved by a human editor/reviewer;
7. `freeze_date` is recorded;
8. the full `QUESTIONS.csv` hash is preserved by the ranking benchmark manifest before labels are opened.

## Prohibition on retroactive optimization

After any `external_test` relevance label is observed, do not rewrite external questions, change their split, remove difficult questions or add favorable questions to the same benchmark round.

A materially changed question set is a new benchmark round and must receive a new freeze and audit trail.

## Current state

**PROTOCOL_READY / FINAL_QUESTIONS_NOT_YET_HUMAN_APPROVED.**

No question wording is declared scientifically independent merely by this protocol.
