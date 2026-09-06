# NutEV — Search & Classification First

Status: canonical product-surface direction.

## Product identity

NutEV is primarily a scientific article search, ranking, classification and exploration engine.

Primary flow:

```text
QUERY
  -> multi-provider discovery
  -> normalize + traceability + dedupe
  -> NutEV ranking
  -> explainable article classification
  -> taxonomy / query-match explanation
  -> article library / dossier / evidence map
```

The core product must answer:

1. What articles are relevant to this query?
2. What kind of article/study is each result?
3. Which NutEV topics/taxonomies are associated with it?
4. Why did this result appear?
5. What source/provenance supports the record?
6. How can the user filter, inspect and reuse it?

## Classification boundary

Search-time classification may use provider article type, title/abstract signals, canonical NutEV taxonomy and query overlap. It is an indexing aid and must remain explainable.

Literal query-overlap explanations are lexical and token-bounded. They must not claim a match from a substring inside another token (for example, `men` inside `women` or `rat` inside `strategy`). This explanation layer does not change retrieval or NutEV ranking; it only describes literal overlap that can be demonstrated from the record text.

It must not silently become:

- eligibility/inclusion decision;
- methodological quality;
- risk of bias;
- certainty/GRADE;
- causal inference;
- clinical recommendation.

## Hibernated/advanced workflows

Rayyan-like screening, Review Control, Review Routes, PRESS, PRISMA-oriented workflows, adjudication, scientific validation, synthesis governance and recommendation governance remain implemented but are not primary navigation or prerequisites for CORE records.

They live under `Laboratório avançado` and can be reactivated for a project that explicitly needs them.

## Product guardrail

A future UI change must not reintroduce QA/PRESS/Review/PRISMA/Validation as top-level primary navigation unless the canonical product direction is explicitly changed.
