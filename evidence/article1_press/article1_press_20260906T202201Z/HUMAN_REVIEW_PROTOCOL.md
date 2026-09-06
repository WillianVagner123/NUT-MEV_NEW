# Article 1 PRESS — independent human review protocol

## Scope

This protocol applies only to the PubMed incremental samples from technical run `article1_press_20260906T202201Z`.

Scientific question:

> Quais parâmetros nutricionais, competências alimentares e contextos sociais da alimentação são atualmente recomendados, estruturados e utilizados por diretrizes e modelos operacionais para orientar avaliação, aconselhamento, prescrição e monitoramento alimentar aplicáveis à Medicina do Estilo de Vida?

The durable sample contains 100 records: 25 each from D02 (`healthy eating`), D03 (`meal plan*`), D04 (C3 implementation), and D05 (C4 social context). D01 has no incremental PubMed records and therefore no precision sample.

## Reviewer procedure

1. Generate the packets with `tools/build_article1_press_human_review_packets.py`.
2. Two different human reviewers complete `REVIEWER_A.csv` and `REVIEWER_B.csv` independently.
3. Allowed decisions are:
   - `Y`: relevant to the Article 1 question / route purpose;
   - `N`: not relevant;
   - `U`: uncertain; abstract or full-text inspection is still required.
4. Every non-blank decision requires a brief reason, reviewer identity, and timezone-aware ISO-8601 timestamp.
5. `U` is unresolved. It is never converted mechanically to `N` and never contributes to precision.
6. After both reviewers are complete, run `tools/validate_article1_press_human_review.py`.
7. If the result is `READY_FOR_ADJUDICATION`, resolve only the disagreements in an adjudication CSV and run the validator again.
8. Final per-delta precision is emitted only when the validator reaches `HUMAN_DELTA_REVIEW_COMPLETE`.

## Independence and fail-closed rules

- Reviewer A and Reviewer B must be different human identities.
- The two packets contain the same records in different deterministic orders.
- A blank decision, unresolved `U`, missing identity/timestamp/reason, invalid label, or unresolved disagreement prevents final precision.
- This review result does **not** itself record PRESS PASS.
- This review result does **not** decide C4 automatically.
- It does **not** authorize GF-10, freeze provider queries, execute formal search, create eligibility decisions, or emit PRISMA.
- Scopus and Web of Science are not simulated by this protocol.

## Commands

```bash
python tools/build_article1_press_human_review_packets.py \
  --sample evidence/article1_press/article1_press_20260906T202201Z/HUMAN_REVIEW_SAMPLE_MANIFEST.json \
  --output-dir /path/to/review_packets

python tools/validate_article1_press_human_review.py \
  --manifest /path/to/review_packets/REVIEW_PACKET_MANIFEST.json \
  --reviewer-a /path/to/review_packets/REVIEWER_A.csv \
  --reviewer-b /path/to/review_packets/REVIEWER_B.csv \
  --output /path/to/HUMAN_REVIEW_RESULT.json
```

When adjudication is required, add `--adjudication /path/to/ADJUDICATION.csv`.
