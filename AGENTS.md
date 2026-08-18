# AGENTS.md — NutEV Reference Engine

This repository contains the NutEV Reference Engine, a stable reference-discovery and ranking product for Lifestyle Nutrition research.

## Supported v1 product scope

The supported path is deliberately narrow:

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT
```

The engine discovers references from configured bibliographic and institutional sources, normalizes and deduplicates records, matches them against the NutEV taxonomy and configurable focus keywords, applies transparent ranking weights, and exports a prioritized reading/reference queue.

It is not a clinical decision engine. Ranking does not mean scientific inclusion/exclusion and does not produce a clinical recommendation.

## Canonical thesis governance — mandatory for A1-A4 runs

The canonical thesis axis is versioned in `config/nutev_governance_manifest.json`. Any article-specific discovery or ranking run must declare exactly one scope: `A1`, `A2`, `A3`, or `A4`, and must preserve the governance version and digest in its run summary/manifest.

Canonical boundaries:

- **A1** — recommendations and dietary direction in normative/structuring documents: what is recommended and how recommendations are operationalized.
- **A2** — current dietary prescriptions/interventions + their operational package + executability difficulties. Implementation, competencies/repertoires and context are explanatory dimensions, not the autonomous object of the article.
- **A3** — development of the NutEV Dietary Protocol: reference dietary expression, individualization, progression/titration, competencies needed for executability, adaptation and sustainability. A3 is not a separate evidence-review engine.
- **A4** — conceptual clinical-decision framework for longitudinal interpretation between prescription, conditions/repertoires, context/contingencies, execution, consequences, outcomes, care relationship and clinical revision. A4 is not CFD-I, CFD-8, a score, flag engine, algorithm or computational clinical decision engine.

`CFD-I` remains a parallel manuscript product outside A1-A4. `CFD-8` remains postdoctoral Article 6.

For article-aware ranking, use `tools/run_governed_rank_references.py --article A1|A2|A3|A4`. The wrapper builds an ephemeral article profile and never mutates the canonical base ranking configuration. Scientific eligibility and clinical decisions remain human-only.

## Non-negotiable product invariants

1. Never fabricate provider results, counts, identifiers, URLs, metadata or full text.
2. Missing credentials, provider errors, timeouts, rate limits and interface changes remain explicit.
3. Scopus and Web of Science are never simulated or silently represented by other databases.
4. Ranking is information-retrieval priority only; it must not be converted into INCLUDE/EXCLUDE decisions.
5. Provider/source identity must survive normalization, deduplication and ranking.
6. Taxonomy and focus-keyword configuration must remain inspectable and versionable.
7. Ranking must be deterministic for identical inputs and configuration.
8. Public ranking exports must not expose legacy PRISMA/FORMAL/screening control fields.
9. Published releases and tags are immutable. Never move or overwrite a published tag.
10. Every PASS claim must be traceable to the exact SHA/ref and actual executed check.
11. Do not invent DOI, ORCID, affiliation, authorship, funding or dates.
12. Do not redistribute protected full text or private research data without rights to do so.
13. Article-specific A1-A4 runs must use the canonical governance manifest and an explicit article scope.
14. Governance metadata must never be used to automate scientific inclusion/exclusion or clinical decisions.

## Supported outputs

The v1 reference-ranking outputs are:

- `project_output_reference/reference_ranking/TOP_REFERENCIAS.md`
- `project_output_reference/reference_ranking/reference_ranking.csv`
- `project_output_reference/reference_ranking/reference_ranking.jsonl`
- `project_output_reference/reference_ranking/latest.json`

Legacy research-review modules and documents may remain in the repository for compatibility or historical provenance, but they are not part of the supported v1 workflow unless a future release explicitly reintroduces them.

## Source hierarchy

When determining software truth, prefer:

1. code at the exact SHA/ref;
2. tests/workflows at the same SHA/ref;
3. canonical governance and configuration;
4. generated ranking artifacts;
5. current v1 documentation;
6. Git history;
7. legacy/historical research documents.

## Change workflow

For non-trivial changes:

1. inspect current `main`;
2. work on a dedicated branch;
3. keep the change inside the supported v1 product scope unless a new product decision explicitly expands it;
4. add/update regression tests when ranking, provider behavior or canonical governance behavior changes;
5. run or obtain relevant CI/security/build checks;
6. use a PR before merge;
7. never hide failing checks with bypasses.

Avoid feature creep. The v1 product is complete when it reliably discovers, normalizes, deduplicates, ranks and exports references while preserving the declared A1-A4 scientific context for article-specific runs.

## Versioning and releases

For a stable release, package version, Git tag, GitHub Release, `CITATION.cff`, `.zenodo.json`, changelog and release notes must describe one exact release identity.

A DOI must not be added before an actual Zenodo archive record is created and verified.

## Legacy boundary

Historical systematic/scoping-review, screening, PRISMA, PRESS, FREEZE and scientific-gate material is legacy research-workflow context, not an active requirement of the NutEV Reference Engine v1 runtime.

See `docs/legacy/README.md` and `docs/RELEASE_V1_AUDIT.md` for the release boundary.
