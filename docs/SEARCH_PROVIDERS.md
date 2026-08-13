# NutEV search providers

`src/nutev` is the canonical NutEV Evidence Engine runtime. The historical Local Deep Research runtime is not present in the active tree; required attribution remains in `LICENSE`, `NOTICE.md` and Git history.

Provider capability and methodological inclusion are different. The protocol and frozen strategy/registry state determine whether a route belongs to a definitive Article 1 execution.

## Indexed providers

The immutable strategy registry/executor is the manuscript-grade boundary for supported indexed searches. PubMed uses NCBI E-utilities with pagination/checkpoints; Europe PMC, Crossref and OpenAlex have independent provider implementations. Failures remain explicit provider failures.

A `FORMAL` or PRISMA-eligible strategy cannot start through the canonical executor without persisted scientific-gate and freeze authorization matching the exact strategy version, Git SHA and configuration digest.

Scopus and Web of Science are protocol providers but may remain `MANUAL_EXECUTION_REQUIRED` when licensed direct integration is unavailable. Import only real execution evidence: exact expression, timestamp, executor, interface, total, exported file/hash, sentinel results and limitations. Never simulate either database through Google or another provider.

## Official / institutional sources

`official_sources_manifest.json` remains the operational source manifest. The scientific-registry layer converts those entries to canonical candidate source records, deduplicates them and normalizes historical analytical labels. Candidate entries cannot become `FROZEN` until required reproducibility fields are verified, including search mechanism, stopping/version rules and reviewer evidence.

## Guideline repositories

`config/guideline_repository_registry.json` is the canonical candidate registry for G-I-N, G-I-N BIGG, AWMF, Dutch Richtlijnendatabase, Minds and Ukraine Registry. Blank operational fields are deliberate: they must be populated only from verified pilot evidence. `NOT_AUTHORIZED` is not execution evidence.

## Supplementary providers

DOAJ, ClinicalTrials.gov, Semantic Scholar, arXiv and optional web search providers remain supplementary capabilities unless the protocol explicitly includes them. Missing credentials are recorded as skipped/failure state rather than evidence absence.

The current SciELO connector is Crossref retrieval restricted to DOI prefix `10.1590`; it must not be described as a comprehensive native SciELO search.

## Provenance and checkpoints

For actual provider attempts preserve, as applicable:

- run/strategy identity;
- exact expression/filter;
- timestamp and status;
- total found and rows returned;
- pagination/limit/truncation;
- checkpoint/resume evidence;
- error/failure state;
- raw snapshot/export and SHA-256;
- configuration provenance and `config_digest`.

The active manuscript-grade execution contract no longer uses the retired `querypack_*` artifact family as canonical evidence. Historical references remain in Git history only where needed for provenance.

A completed provider call is never equivalent to scientific approval. See `docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md` and `docs/SCIENTIFIC_GOVERNANCE.md`.
