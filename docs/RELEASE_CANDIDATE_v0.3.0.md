# NutEV Evidence Engine v0.3.0 — Release Candidate Record

Status: **CANDIDATE — NOT YET PUBLISHED**

This document records the candidate scientific-software object before any tag, GitHub Release, Zenodo archive or DOI exists.

## Object identity

**NutEV Evidence Engine v0.3.0** freezes the unified global-search, generated-versus-executed provenance, master-corpus, curation/human-review and reproducible release-validation architecture used to support the evidence-synthesis workflow of the NutEV project.

This is a **software/reproducibility release** at alpha scientific maturity. It does not assert that human screening is complete, that the Article 1 manuscript is ready, or that any `RecommendationCandidate` is a final clinical recommendation.

## Candidate lineage

- Candidate branch: `release/0.3.0-candidate`
- Candidate base main SHA: `b3a98095372ad74a72737bcc81776089f4d686c7`
- Previous immutable release: `v0.2.0`
- Proposed tag: `v0.3.0`
- Proposed package version: `0.3.0`
- Zenodo DOI: **not yet assigned / must not be invented**
- Release date: **not yet assigned**

The exact final candidate SHA must be captured only after the candidate PR stops changing and all required workflows pass on that exact head.

## Scientific invariants

The candidate preserves these release-critical contracts:

- generated query is not an executed query;
- actual provider attempts are the authority for executed-query ledgers;
- `execution_status` is distinct from `scientific_readiness`;
- `manuscript_ready` requires explicit human/manuscript gates;
- one global frozen research strategy is rendered per provider and produces one governed run/master corpus before article-specific screening;
- Track A, Track B and optional Track C retain distinct sampling/provenance semantics;
- metadata-only is not silently promoted to full text;
- the current SciELO connector is Crossref retrieval scoped to DOI prefix `10.1590`, not a comprehensive native SciELO free-text search;
- operational prioritization is not scientific inclusion;
- Evidence Engine is not a Clinical Decision Engine.

## Candidate validation requirements

The following must all run successfully on the **same exact candidate SHA** before merge/publication:

- canonical CI on Python 3.12 and 3.13;
- blocking coverage threshold;
- Windows smoke and zero-key demo;
- compileall and blocking Ruff checks;
- mypy provenance-core checks;
- CodeQL;
- security scan / Gitleaks / repository hygiene;
- dependency review actually executed;
- wheel and sdist build;
- metadata validation (`twine check` or current equivalent);
- clean wheel install, CLI startup and zero-key demo from the installed artifact.

Prior green runs on development SHAs are supporting history, not release-candidate PASS evidence.

## Metadata boundary

The candidate synchronizes package version, `CITATION.cff`, `.zenodo.json`, CHANGELOG and README to `0.3.0` candidate identity.

Until publication:

- no `date-released` is asserted in `CITATION.cff`;
- no Zenodo DOI is asserted;
- ORCID and affiliation remain omitted unless explicitly confirmed;
- `v0.2.0` remains the latest published/citable release.

## Publication gate

No `v0.3.0` tag or GitHub Release may be published until:

1. exact-SHA candidate validation is green;
2. tag collision remains absent;
3. the GitHub↔Zenodo repository integration is confirmed enabled;
4. release metadata is rechecked against current official Zenodo guidance;
5. privacy/copyright/provenance red-team checks have no unresolved release blocker.

After GitHub publication, a Zenodo DOI must be copied only from the real processed Zenodo record. The published tag remains immutable; DOI documentation updates occur on post-release `main`, not by moving the tag.
