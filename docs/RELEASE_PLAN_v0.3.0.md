# Release plan — prospective v0.3.0

Status: **PRE-RELEASE PLAN — DO NOT TAG OR MINT DOI YET**.

The current source tree remains `0.3.0.dev1`. This document defines the evidence required before deciding whether the next public/citable software object should be `v0.3.0`.

## Why this release could be meaningful

The development line now includes the canonical one-global-search workflow, the gate-aware `nutev play` PILOT orchestrator, lawful full-text/OCR handling and removal of the obsolete parallel workstream/querypack runtime. A future `v0.3.0` can be a defensible software milestone if the exact release SHA is validated and the provenance/license boundary is resolved.

A release is not evidence that GF-02/PRESS/GF-10 or the Article 1 formal search are complete. If those gates remain open at publication time, release notes and metadata must state that the software supports PILOT execution and human-review workflows while formal scientific authorization remains separate.

## Hard blockers before tag/release

### R-01 — PLAY validation

- `nutev play --metadata-only` succeeds on a real local scientific project root;
- a bounded full PLAY succeeds with lawful full-text retrieval/extraction/OCR;
- output package contains `play_summary.json`, `play_summary.sha256`, state/provider/fulltext/download/extraction ledgers;
- summary checksum verifies against the exact JSON bytes;
- failures/truncation remain visible;
- no PILOT execution enters PRISMA.

### R-02 — provenance / MIT decision

Close or explicitly resolve #1014:

- confirm upstream Local Deep Research repository/license evidence;
- establish the best-supported derivation point if known, otherwise state unknown;
- audit any substantial inherited material still present;
- human-confirm the copyright holder/name for original NutEV contributions;
- decide the final license/copyright presentation for current NutEV contributions;
- preserve upstream notices where required;
- reconcile `LICENSE`, `NOTICE.md`, `docs/PROVENANCE_AND_LICENSE.md`, `pyproject.toml`, `CITATION.cff`, `.zenodo.json` and release notes.

### R-03 — code hygiene

- the obsolete `master_pipeline.py`, `querypacks/**`, legacy `busca1/busca2a/busca2b` domain modules/configs and default CLI `--workstreams` mode must remain absent from the candidate tree;
- legacy-only tests/examples/docs must remain removed or migrated to the canonical PLAY/global-search path;
- repository docs must describe the current tree, not superseded migration plans;
- no supported current runtime may import deleted legacy modules;
- #1015 may close only after the retirement PR passes the canonical gates.

### R-04 — search/filter hardening

Before the software is presented as ready to support a definitive FORMAL search:

- validate date ranges and reject inverted/invalid ranges;
- normalize/validate language filters;
- normalize publication-type filters and record provider support explicitly;
- sanitize/escape query input so user text cannot silently alter provider syntax;
- add negative/adversarial tests for quotes, Boolean operators, field tags and special characters;
- preserve exact normalized input and rendered expression in the immutable strategy record.

These filter gates are separate from the human scientific decision about what final date/language/publication filters the protocol should use (GF-06).

### R-05 — exact-SHA validation

On the candidate SHA:

- Python 3.12 canonical tests pass;
- Python 3.13 canonical tests pass;
- coverage gate passes where configured;
- Windows smoke passes;
- compile/Ruff blocking gates pass;
- type-check provenance core passes;
- dependency review passes by actually executing;
- security scan and CodeQL pass;
- release artifact validation passes;
- wheel/sdist metadata are valid;
- clean installation exposes `nutev play`.

### R-06 — release identity reconciliation

Only after R-01–R-05:

1. choose the final semantic version;
2. change `src/nutev/__version__.py` from the development identity to the release identity;
3. update `CITATION.cff`;
4. update `.zenodo.json`;
5. update CHANGELOG and release notes;
6. verify `pyproject.toml` resolves the intended package version;
7. verify no existing Git tag uses the proposed tag;
8. run the release checks again on the final candidate SHA.

The tag, GitHub Release, package metadata, citation metadata and Zenodo metadata must describe the same software object.

## Zenodo sequence

After the repository is enabled in the Zenodo GitHub integration and the exact release candidate is approved:

```text
approved candidate SHA
        ↓
create immutable Git tag
        ↓
create GitHub Release for that tag
        ↓
Zenodo processes the GitHub release
        ↓
verify the actual Zenodo record + DOI
        ↓
record the real DOI in post-release metadata/documentation
```

Do not invent a DOI in advance.

Because this repository contains both `.zenodo.json` and `CITATION.cff`, release preparation must keep the Zenodo deposit metadata and citation metadata synchronized around one exact software object.

## Files that must NOT enter the citable software archive intentionally

- project output roots (`project_output*`);
- downloaded third-party full-text PDFs unless redistribution rights are explicit;
- local OCR corpora derived from protected material;
- `.env` files, API keys, cookies or credentials;
- private research data;
- patient/participant data;
- local databases containing non-redistributable scientific content.

Release artifacts should contain the software, configuration, documentation and safe demonstration material required to reproduce software behavior, not the protected evidence corpus itself.

## Go / no-go

The release decision should end with one of:

- `NO-GO — technical/provenance blocker`;
- `TECHNICALLY READY — scientific/human gate remains open but accurately documented`;
- `GO — exact release SHA approved for tag/GitHub Release/Zenodo archive`.

Zenodo publication is not performed merely because this checklist exists; it follows an explicit GO decision on one exact SHA.
