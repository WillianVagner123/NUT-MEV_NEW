# Regional route pre-freeze validation

Status: operational workflow for Article 1 GF-01.

## Purpose

The regional routes screen documents technical validation of the official LILACS/BVS and SciELO search interfaces when automated retrieval is denied (for example HTTP 403). It is deliberately **not** a formal search runner.

Current routes:

- `B-NORM-LILACS` — LILACS via the official BVS search portal.
- `B-SUPP-SCIELO` — SciELO native search using the `subject:(...)` query scope.

The canonical regional query remains the query defined by the existing Latin-source runner and the Article 1 search plan:

```text
(diet OR dietary OR nutrition OR "healthy eating") AND (guideline OR guidance OR recommendation OR consensus OR statement OR standard)
```

## Why browser-assisted evidence is allowed

The existing automated native route records HTTP 401/403 as `unavailable` and must never convert those states to zero results. The canonical Article 1 method permits an official human/visual or otherwise validated endpoint as a prospective technical-route amendment, provided the conceptual query and chain of custody are preserved.

The regional screen therefore opens the official provider search, asks the operator to enter the count shown by that interface, and hashes locally selected evidence files (RIS/CSV/BibTeX/text/HTML/image/PDF). This allows technical validation without claiming that automation succeeded.

## Required evidence

For each route the operator records:

1. exact canonical query;
2. official search URL;
3. actual execution date;
4. result count displayed by the official interface;
5. evidence scope (full export, chunked export, validation sample, or screen capture);
6. one or more evidence files, hashed with SHA-256 in the browser;
7. explicit confirmation that the official interface was used;
8. explicit confirmation that error/403/unavailable was not recoded as zero;
9. explanatory notes when the evidence is not a full export.

When a parseable RIS/BibTeX/CSV is labelled `FULL_EXPORT`, the detected file record count must match the official result count or the route remains `REVIEW_REQUIRED`.

## Gate semantics

If both routes have complete technical evidence the exported JSON reports:

- `technical_route_gate: PASS`;
- `gf01_candidate_complete: true`;
- `freeze_authorized: false`;
- `formal_search: false`;
- `prisma_eligible: false`.

This means the evidence is ready for incorporation into the canonical CONTROL CENTER. It does **not** itself mutate GF-01, authorize GF-10, or create a PRISMA count.

## Formal search separation

After every required freeze gate is closed and GF-10 is explicitly authorized, the formal searches must be executed **from zero** with the frozen strategies. Pre-freeze validation counts and exports remain QA/audit artifacts only and must never be copied into the formal PRISMA flow.
