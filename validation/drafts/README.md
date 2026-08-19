# Benchmark question drafts

Files in this directory are **not canonical benchmark inputs**.

They may be used only as editorial working material before a human independently reviews the wording, scope, split assignment and domain coverage. They must not be passed to the benchmark freeze tool as if they were approved.

The canonical benchmark file remains `validation/data/QUESTIONS.csv`, which must not be created or overwritten until the final question content is human/editorially approved under `validation/QUESTION_SET_PROTOCOL.md`.

For a draft to become eligible for human freeze preparation, the reviewer must explicitly determine at least:

- final `question_text` and eligibility context;
- `split` and `sampling_stratum`;
- truthful `outside_historical_focus` declarations, including at least two `true` rows in the final set;
- languages, document types and time window when applicable;
- `human_approved_by`, `human_approval_date` and `freeze_date`.

Machine-generated draft wording is not evidence of scientific independence. Do not infer human approval, relevance labels or benchmark performance from these files.
