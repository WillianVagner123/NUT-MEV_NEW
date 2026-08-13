# Article 1 search execution contract

Status: **normative for definitive Article 1 executions**.

## Core rule

No query, source, provider, navigation rule or result count may be described as executed without attempt-level evidence for the exact run. Generated ≠ executed; PILOT ≠ FORMAL; FORMAL ≠ PRISMA unless the scientific gates and freeze authorize it.

## Formal authorization boundary

`nutev.search.strategy_executor` is the canonical indexed-database execution boundary. A strategy marked `FORMAL` or PRISMA-eligible must be bound to persisted scientific-gate evidence and an immutable freeze record before a run is created.

Authorization must match:

- exact strategy `version_id`;
- GF-02…GF-09 prerequisite state;
- human-authorized GF-10;
- freeze identifier;
- exact Git SHA;
- configuration digest.

Missing or mismatched evidence blocks execution. A PILOT run remains non-PRISMA.

## Track A — indexed databases

Use the immutable strategy registry/executor for provider expressions covered by the registered strategy version. Preserve at minimum:

- strategy/version identity and search type;
- exact provider expression and provider-specific filter;
- timestamp, status and executor context;
- provider limit/pagination/truncation state;
- rows returned and provider-reported total when available;
- raw snapshot and SHA-256;
- run manifest and hash;
- formal-authorization record when required;
- PRISMA eligibility.

Scopus and Web of Science remain valid manual/licensed routes when direct integration is unavailable. Their evidence must preserve exact executed expression, timestamp, executor, interface/database, total reported, export identity/hash, sentinel results and limitations. Never substitute another provider for them.

## Track B — official / institutional sources

Official organizations, food guidelines and society documents are not a homogeneous bibliographic database. Use the canonical source-registry view and preserve source identity, route, retrieval date, configuration provenance, URL/resolved URL, retrieval/download/extraction state, failures and artifact hash when a local copy may lawfully be retained.

Candidate registry entries are not frozen sources. Formal use requires verified operational rules, including search mechanism, stopping/version rules and reviewer evidence as required by the registry contract.

## Track C — guideline repositories

The canonical guideline-repository registry declares G-I-N, G-I-N BIGG, AWMF, Dutch Richtlijnendatabase, Minds and Ukraine Registry as candidate methodological routes. A repository remains `NOT_AUTHORIZED` until its operational search fields are verified. Repository identification and issuer confirmation must preserve distinct provenance.

## Track D — supplementary discovery

Optional providers may be used only when protocol-declared. Technical capability does not imply inclusion in the Article 1 formal search. Missing credentials and provider failures stay visible; they are never converted into zero-result evidence.

The current SciELO connector is DOI-prefix/Crossref scoped (`10.1590`), not a comprehensive native SciELO platform search.

## Canonical generated-versus-executed evidence

The retired `querypack_*` runtime/artifact family is historical compatibility only and is not the current execution contract.

Current manuscript-grade evidence is based on:

- immutable strategy registry/version;
- persisted scientific gates and freeze evidence;
- strategy execution records;
- provider raw snapshots and hashes;
- execution artifacts/run manifest;
- generic provider performance/failure ledgers where applicable;
- configuration provenance and `config_digest`.

No generated expression is proof of submission.

## Scientific readiness

Computational completion and scientific readiness are separate. Provider success cannot infer PRESS approval, freeze authorization, R1/R2/adjudication, inclusion or manuscript readiness.

## Definitive execution checklist

Before describing an execution as definitive for Article 1, preserve:

1. software version and exact Git SHA;
2. strategy versions and exact expressions/navigation rules;
3. source/repository/sentinel registry versions;
4. PRESS evidence and GF-02…GF-10 records;
5. real formal-search date and provider-specific filters;
6. `config_digest` and relevant config hashes;
7. every actual attempt, error, limit and truncation state;
8. raw snapshots/exports plus hashes where required;
9. route-preserving identity resolution/deduplication;
10. human screening/adjudication state;
11. PRISMA-eligible counts only from authorized formal evidence.

If required evidence is missing, the run may remain useful as development/PILOT evidence but must not be represented as the definitive manuscript execution.
