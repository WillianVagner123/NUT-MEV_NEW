# NutEV Review Control Center

The Article 1 Review Control Center is intentionally fail-closed.

The current discovery/Tier A corpus can be used for rank-blind reading, taxonomy calibration and strategy development. It is not a formal title/abstract screening corpus.

The page reads `SEARCH_STATE.json` and `ARTICLE_SUMMARIES.jsonl` to show calibration availability and formal-search gates. It does not write decisions.

The canonical article-screening contract remains:

```text
ReviewerDossier
  -> human review / adjudication
  -> one resolved final ScreeningDecision
  -> science-screening import
  -> explicit scientific events / derived PRISMA counts
```

Current `science-screening` does not implement reviewer-level blinded assessments or article conflict/adjudication UI. Therefore the Control Center must not expose active include/exclude actions until a separate canonical reviewer-level contract is implemented and the Article 1 formal corpus exists.

Route membership, calibration reading and full-text availability remain separate from scientific eligibility.
