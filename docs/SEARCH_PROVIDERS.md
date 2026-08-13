# NutEV search providers

`src/nutev` is the canonical runtime. Provider capability and methodological inclusion are different: protocol plus frozen strategy/registry state determine whether a route belongs to a definitive Article 1 execution.

## Indexed providers

The immutable strategy registry/executor is the manuscript-grade boundary for supported indexed searches. PubMed uses NCBI E-utilities with pagination/checkpoints; Europe PMC, Crossref and OpenAlex have independent implementations. Provider failures remain explicit.

A `FORMAL` or PRISMA-eligible strategy cannot start through the canonical executor without persisted scientific-gate and freeze authorization matching the exact strategy version, Git SHA and configuration digest.

Scopus and Web of Science are protocol providers but may remain `MANUAL_EXECUTION_REQUIRED` when licensed direct integration is unavailable. Import only real execution evidence: exact expression, timestamp, executor, interface, total, exported file/hash, sentinel results and limitations. Never simulate either database through another provider.

## Official / institutional sources

`official_sources_manifest.json` remains the source manifest. The scientific-registry layer converts entries to canonical candidate records, deduplicates them and normalizes historical analytical labels. Candidate entries cannot become `FROZEN` until required reproducibility fields are verified, including search mechanism, stopping/version rules and reviewer evidence.

## Guideline repositories

`config/guideline_repository_registry.json` is the canonical candidate registry for G-I-N, G-I-N BIGG, AWMF, Dutch Richtlijnendatabase, Minds and Ukraine Registry. Blank operational fields are deliberate: populate them only from verified pilot evidence. `NOT_AUTHORIZED` is not execution evidence.

## Supplementary providers

DOAJ, ClinicalTrials.gov, Semantic Scholar, arXiv and optional web-search providers remain supplementary capabilities unless protocol-declared. Missing credentials are recorded as skipped/failure state rather than evidence absence.

The current SciELO connector is Crossref retrieval restricted to DOI prefix `10.1590`; it must not be described as a comprehensive native SciELO search.

## Provenance

For actual attempts preserve run/strategy identity, exact expression/filter, timestamp/status, totals/rows, pagination/limit/truncation, checkpoint/resume evidence, failures, raw snapshot/export and SHA-256, and configuration provenance with `config_digest`.

The retired `querypack_*` artifact family is historical compatibility only and is not active manuscript-grade execution evidence.

A completed provider call is never equivalent to scientific approval. See `docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md` and `docs/SCIENTIFIC_GOVERNANCE.md`.
