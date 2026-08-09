# Roadmap

High-level direction. Scientific correctness, reproducibility and human oversight take precedence over speed.

## Historical v0.1.x line

The repository contains historical tags `v0.1.0` through `v0.1.8`. They record earlier development states and are preserved unchanged. Historical package/tag version alignment was not consistently synchronized, so those tags are not reused as the citation-grade release line.

## v0.2.0 — citation-grade reconciled Evidence Engine

- [x] Public release audit and provenance reconciliation.
- [x] Canonical package identity/version under `src/nutev/`.
- [x] Inherited Local Deep Research runtime removed from the current source tree while MIT attribution is preserved.
- [x] Core vs optional dependency architecture.
- [x] Canonical test location `nutev_tests/`.
- [x] CI on Python 3.12 and 3.13.
- [x] Security scan, gitleaks/repository hygiene, dependency review and CodeQL.
- [x] Zero-key synthetic demonstration.
- [x] Search-strategy registry/execution traceability.
- [x] Auditable normalization/deduplication and document identity/version/family handling.
- [x] Full-text recoverability and OCR failure visibility.
- [x] Article 1 A/B/C/D assistive coding with traceable evidence snippets.
- [x] Two-reviewer screening/adjudication workflow and export gate.
- [x] PRISMA-oriented exports without automatic declaration of a final included corpus.
- [x] Config provenance and `config_digest`.
- [x] Article 1 software traceability matrix.
- [x] Zenodo/CFF metadata reconciliation.
- [x] Dedicated release-validation workflow: version/tag collision, tests, build, twine, clean wheel demo, link check and environment snapshot.
- [x] Gated publisher that can create `v0.2.0` only after successful release validation of the exact `main` SHA.
- [ ] Verify the actual Zenodo record and insert the real Version DOI after GitHub Release ingestion.
- [ ] Add ORCID/affiliation only when exact values are confirmed.

## Next release — scientific usability and corpus execution

- Complete and document the definitive Article 1 search execution used in the manuscript.
- Freeze protocol/search-strategy versions and record retrieval dates.
- Complete dual-reviewer screening and adjudication records.
- Complete human validation of A/B/C/D domain coding.
- Produce manuscript-facing matrices/tables from the frozen scientific run.
- Reconcile manuscript method claims with `docs/ARTICLE1_SOFTWARE_TRACEABILITY.md`.
- Improve reviewer UX without weakening human-decision gates.

## Later

- Strengthen evidence-quality appraisal where required by each study design.
- Expand implementation/adherence corpus work for Article 2.
- Maintain the behavioral framework as a downstream scientific product rather than silently mixing it into the Article 1 evidence object.
- Publish subsequent software versions as new immutable tags/Zenodo versions.

### Architectural rule

Large refactors that can alter scientific outputs must remain parity-gated and methodologically reviewed. Query generation, provider behavior, deduplication, coding rules, screening/export gates and configuration semantics must never change silently.

## Permanently out of scope for the Evidence Engine

- Git history rewrite merely to make old tags look cleaner.
- Moving or overwriting an already published tag.
- Presenting automated output as a final clinical recommendation.
- Embedding the separate Clinical Decision Engine in this repository without an explicit project-level architecture decision.

Track changes via GitHub Issues/PRs and record scientific-method changes in `docs/CHANGELOG_METODOLOGICO.md`.
