# NutEV — Exact Review Strategy Mode

Status: **CANONICAL FOR VERSIONED ELECTRONIC SEARCH EXECUTION**

## Purpose

Use Exact Review Strategy Mode when a bibliographic strategy has already been designed, versioned, piloted, peer reviewed, or otherwise approved in provider-native syntax and must be executed without reinterpretation by NutEV.

This mode exists because review-grade searches can contain provider-specific field tags, subject headings, publication types, exclusions, nested Boolean branches, date windows, and syntax choices that must not be reconstructed from a generic PCC/PICO/PECO builder.

## Core rule

**The exact provider query is an input artifact, not a prompt for NutEV to improve.**

NutEV must preserve the supplied query literally except for trimming leading/trailing whitespace required by transport. It must not:

- translate `[ti]`, `[tiab]`, `[Majr]`, `[pt]`, date filters, headings or equivalent provider-native syntax;
- add disease terms, synonyms, MeSH, DeCS or filters;
- simplify Boolean branches;
- infer missing provider queries;
- copy a PubMed query into another provider and call that a translation.

## Runtime fields

An exact strategy run records:

```text
strategy_id
strategy_version
run_class
provider_queries
```

Allowed run classes:

```text
PREFLIGHT
PILOT
DEVELOPMENT
SUPPLEMENTARY
FORMAL
```

`FORMAL` is metadata only. Selecting it in the UI does not authorize a formal systematic/scoping-review search, PRISMA count, freeze, publication claim, or scientific gate. External protocol authorization remains required.

## Provider selection

Every selected provider must have an explicit exact query. Missing queries fail closed.

In Exact Review Strategy Mode, `Busca global` means **remove NutEV's internal result ceiling for the selected exact-provider routes**. It does not automatically select every connected provider, because doing so would require inventing queries for providers that do not have an approved strategy.

## PubMed Search Details

For review-grade PubMed runs, NutEV performs a separate auditable ESearch inspection and preserves:

```text
count
query_translation
warninglist
errorlist
warnings_present
errors_present
search_details_complete
```

These are stored in:

```text
providers[].search_details
```

If PubMed Search Details cannot be obtained, contain an ESearch error, or disagree with the retrieval count, NutEV records an audit gap and the run becomes:

```text
COMPLETE_WITH_AUDIT_GAPS
```

A retrieval run with an audit gap must not be represented as a fully auditable review-grade execution.

Warnings are not silently discarded. They remain visible in the web result and persisted JSON so syntax problems such as `quotedphrasesnotfound` can be evaluated prospectively.

## Audit trail

Each run persists at least:

- human-readable review question;
- exact strategy ID/version/run class;
- exact provider query;
- query dialect (`exact_provider_syntax`);
- provider returned count/status;
- PubMed Search Details when PubMed is used;
- audit gaps;
- deduplicated/ranked output;
- search mode;
- timestamp and persisted run location.

Exact search modes are:

```text
exact_review_bounded
exact_review_global_exhaustive
```

## Boundary with structured strategy builder

Use the PCC/PICO/PECO builder while designing or translating concept-based strategies.

Use Exact Review Strategy Mode once provider-native syntax itself is part of the scientific protocol and must remain unchanged.

The two modes are intentionally separate so an approved search is never silently regenerated from concepts at execution time.
