# AGENTS.md — NutEV Evidence Engine

This repository is scientific research software. Agents working here must optimize for reproducibility, provenance, methodological fidelity, security, and transparent human oversight — not merely for passing tests or producing plausible outputs.

## Scope

NutEV Evidence Engine supports evidence-synthesis workflows such as search strategy construction, traceable retrieval, normalization, deduplication, assisted screening/extraction, evidence matrices, audit trails, and manuscript-facing methodological exports.

It is **not** a clinical decision engine. It does not independently prescribe, diagnose, validate clinical recommendations, or replace scientific adjudication.

## Non-negotiable scientific invariants

1. A generated query is not an executed query. Never report an expression as executed without attempt-level execution evidence for the exact run.
2. Computational completion is not scientific readiness. Keep `execution_status` distinct from `scientific_readiness`.
3. `manuscript_ready` requires explicit human-review and manuscript gates; never infer it from provider or pipeline success.
4. `RecommendationCandidate` is not a final clinical recommendation.
5. Provider capability does not imply protocol inclusion.
6. Search tracks with different sampling logic must remain distinct in methods and PRISMA accounting.
7. Missing credentials, provider errors, timeouts, rate limits, and unsupported operations must remain visible; do not convert them silently into evidence absence or zero results.
8. Do not invent DOI, ORCID, affiliation, authorship, funding, dates, study results, or provenance.
9. Published releases/tags are immutable. Never move or overwrite a published tag.
10. Every PASS claim must be traceable to the exact SHA/ref and actual executed check.

## Article 1 search contract

`docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md` is normative for definitive Article 1 executions.

Minimum expectations include:

- immutable software/version/SHA identity;
- frozen protocol/search-strategy identity;
- exact provider expressions or official-source navigation rules;
- attempt-level execution ledger;
- timestamps, counts, errors, limits and pagination/truncation rules;
- raw snapshots and hashes where applicable;
- configuration digests;
- human screening/adjudication state;
- PRISMA-compatible accounting appropriate to each search track.

The current SciELO connector is Crossref retrieval scoped by DOI prefix `10.1590`; do not describe it as a comprehensive native SciELO free-text search.

## Source hierarchy

When determining software truth, prefer:

1. code at the exact SHA/ref;
2. tests/workflows at the same SHA/ref;
3. configuration;
4. generated ledgers/artifacts;
5. current documentation;
6. Git history;
7. historical audit reports.

Historical audit documents are evidence of past state, not automatically the operational truth of `main`.

## Change workflow

For non-trivial changes:

1. inspect current `main` and relevant normative docs;
2. work on a dedicated branch;
3. make the smallest defensible change;
4. add/update regression tests for scientific invariants when behavior changes;
5. run or obtain the relevant CI/security checks;
6. document methodological impact when applicable;
7. use a PR before merge;
8. do not hide failing checks with `continue-on-error` or equivalent bypasses.

## Versioning and releases

The source tree may carry a development version after a public release while citation/archive metadata still describes the latest immutable release. Before the next public release, reconcile package version, Git tag, GitHub Release, `CITATION.cff`, Zenodo metadata, changelog, and release notes to one exact release identity.

Do not create a new release merely because code improved. A scientific release should correspond to a clearly identifiable research-software object used in a scientific stage or deliberately frozen for reproducibility.

## Security, privacy, and copyright

Never commit or expose secrets, `.env` files, credentials, private keys, authenticated URLs, identifiable clinical/patient data, or private research data.

Do not redistribute full-text articles, figures, datasets, or other third-party material without a clear right to redistribute. Open-source software licensing does not imply redistribution rights for processed scientific content.

A security/dependency workflow is PASS only if the underlying analysis actually executed successfully.

## Human oversight and AI/LLM use

AI/LLM outputs are assistance, not independent scientific evidence. Record relevant provider/model/configuration when needed for reproducibility and preserve human review for scientific inclusion, exclusion, coding, adjudication, and manuscript gates.

## Documentation expected from agents

When a change is scientifically meaningful, state:

- what changed;
- why it changed;
- exact files/modules affected;
- methodological consequence;
- tests/checks used;
- unresolved limitations;
- whether the change affects manuscript language, reproducibility artifacts, or future release metadata.

## Release gate

Use `docs/RELEASE_CHECKLIST.md` and the scientific governance documentation before a release. A release is not ready while version identity, tests, provenance, security/privacy, copyright, metadata/citation, scientific consistency, or required human gates remain unresolved.
