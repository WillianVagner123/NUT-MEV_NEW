# Publish NutEV Reference Engine on Zenodo

This document describes the publication path for **NutEV Reference Engine v1.0.0**.

The GitHub repository is the development source. Zenodo should archive the exact immutable GitHub Release and issue the persistent software DOI.

## Release identity

- Product: **NutEV Reference Engine**
- Version: **1.0.0**
- Git tag: **v1.0.0**
- License: **MIT**
- Creator: **Schneider, Willian Vagner Dorneles**
- DOI: **PENDING until a real Zenodo archive exists and is verified**

Do not infer a DOI, ORCID or institutional affiliation.

## Metadata sources

The release keeps two synchronized metadata files:

- `.zenodo.json` — archive/deposit metadata;
- `CITATION.cff` — software citation metadata.

Both must describe the same title, version, creator, license and product scope before the tag is created.

## Product scope represented in Zenodo

The archived software is a taxonomy-guided multi-source reference discovery and ranking engine for Lifestyle Nutrition research.

Supported flow:

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT
```

The archive must not present ranking as scientific inclusion/exclusion or as a clinical recommendation. Historical pre-v1 systematic/scoping-review workflow material is provenance/legacy context, not the supported v1 product workflow.

## Pre-publication gate

Before creating `v1.0.0`:

- [ ] release PR merged;
- [ ] exact final `main` SHA recorded;
- [ ] package version is `1.0.0`;
- [ ] `.zenodo.json` version is `1.0.0`;
- [ ] `CITATION.cff` version is `1.0.0`;
- [ ] README and CHANGELOG describe the Reference Engine v1;
- [ ] canonical CI is green on the exact candidate/final SHA;
- [ ] release-artifact validation is green;
- [ ] security scan, dependency review and CodeQL are green;
- [ ] no secrets/private data/protected full text are included;
- [ ] target tag `v1.0.0` does not already exist.

See `RELEASE_CHECKLIST.md`, `RELEASE_V1_0_0.md` and `RELEASE_V1_AUDIT.md`.

## Enable/verify GitHub–Zenodo integration

In the Zenodo account used for publication:

1. open the GitHub integration;
2. synchronize repositories if needed;
3. locate `WillianVagner123/NutEV-Evidence-Engine`;
4. enable archival for GitHub releases;
5. verify the repository remains enabled before publishing `v1.0.0`.

This external-account state cannot be inferred from repository files.

## Publish

Only after the final release SHA is validated:

```text
validated main SHA
      ↓
create immutable tag v1.0.0
      ↓
create GitHub Release "NutEV Reference Engine v1.0.0"
      ↓
wait for Zenodo ingestion
      ↓
open the real Zenodo record
      ↓
verify metadata/files/version
      ↓
record the real DOI
```

Do not move `v1.0.0` after publication.

## Verify the real Zenodo record

Check:

| Field | Expected |
|---|---|
| title | NutEV Reference Engine: taxonomy-guided reference discovery and ranking for Lifestyle Nutrition |
| version | 1.0.0 |
| Git tag | v1.0.0 |
| creator | Schneider, Willian Vagner Dorneles |
| license | MIT |
| description | Reference Engine discovery/ranking scope |
| keywords | synchronized with `.zenodo.json` |
| files | archive of the exact GitHub Release |
| Version DOI | value observed on the real Zenodo record |
| Concept DOI | record only if shown/verified |

Do not declare the release archived while any material mismatch remains.

## After DOI issuance

The `v1.0.0` tag remains immutable. Add the verified DOI only in a **later documentation commit** on `main`, for example in:

- `CITATION.cff`;
- README citation/badge;
- a post-release record.

Do not recreate or move the archived tag merely to insert the DOI.

## Status language

Use:

- `V1 RELEASE PREPARATION IN PROGRESS` while the release PR/checks are incomplete;
- `V1 READY FOR ZENODO` after the exact release SHA/tag/GitHub Release are ready but before verified ingestion;
- `NUTEV REFERENCE ENGINE v1.0.0 — RELEASED / ZENODO ARCHIVED` only after the real Zenodo record and DOI are verified.
