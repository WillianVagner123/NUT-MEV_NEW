# NutEV Evidence Engine — Release Validation Report

**Release candidate:** `0.1.0`  
**Planned tag:** `v0.1.0`  
**Scientific maturity:** alpha  
**Validation status:** **NOT YET EXECUTED ON THE FINAL RELEASE-CANDIDATE SHA**

This document is the release-specific validation record. Historical test counts from older branches/commits must not be reused as proof that the final citable release passed validation.

## 1. Candidate identity

Fill only after the reconciliation branch is finalized:

- **Commit SHA:** `HUMAN INPUT REQUIRED`
- **Validation date:** `HUMAN INPUT REQUIRED`
- **Validator/environment:** `HUMAN INPUT REQUIRED`
- **Operating system:** `HUMAN INPUT REQUIRED`
- **Python versions tested:** `HUMAN INPUT REQUIRED`

The candidate SHA recorded here must be the same SHA later tagged as `v0.1.0`.

## 2. Scope

The NutEV Evidence Engine supports reproducible computational workflows for evidence identification, organization, deduplication, retrieval, extraction, structured coding, auditing, human-review queues and evidence matrices related to the NutEV research program.

It is **not** the separate Clinical Decision Engine and does not provide diagnosis, individualized prescription or final clinical recommendations.

A `RecommendationCandidate` remains a candidate pending human review/adjudication.

## 3. Required clean-environment installation tests

Run on the final candidate SHA.

### Python 3.12

```bash
python3.12 -m venv /tmp/nutev-312
. /tmp/nutev-312/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dashboard]"
nutev --help
```

Record:

- result: `PENDING`
- install warnings/errors: `PENDING`

### Python 3.13

```bash
python3.13 -m venv /tmp/nutev-313
. /tmp/nutev-313/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dashboard]"
nutev --help
```

Record:

- result: `PENDING`
- install warnings/errors: `PENDING`

## 4. Canonical test suite

```bash
PYTHONPATH=src python -m pytest -q nutev_tests
```

Record the exact result instead of writing only “tests passed”:

| Field | Result |
|---|---|
| Python | PENDING |
| total collected | PENDING |
| passed | PENDING |
| failed | PENDING |
| skipped | PENDING |
| xfailed/xpassed | PENDING |
| relevant warnings | PENDING |
| duration | PENDING |

### Failure classification

If any test fails, classify it:

- **BLOCKER:** can change scientific corpus, extraction, coding, deduplication, screening, provenance, audit or exported result;
- **HIGH:** affects an important release capability;
- **MODERATE:** real limitation with documented workaround;
- **LOW:** does not compromise the research-software object being archived.

Do not release with an unresolved BLOCKER.

## 5. Zero-key demonstration

```bash
nutev demo-data --project-root ./project_output_demo
nutev dashboard --project-root ./project_output_demo --port 8501
```

Required checks:

- [ ] no private API key required;
- [ ] no protected PDF/full text required;
- [ ] synthetic/demo status clearly visible;
- [ ] `07_logs/run_summary.json` generated;
- [ ] dashboard can load the generated project;
- [ ] demo output is never represented as scientific evidence.

**Result:** `PENDING`

## 6. Offline pipeline / integration path

Run the canonical no-network integration tests and, where applicable, an offline pipeline smoke run.

Required checks:

- [ ] deterministic configuration path resolves correctly;
- [ ] configuration provenance is written;
- [ ] `config_digest` is recorded where expected;
- [ ] audit artifacts are written to their current canonical locations;
- [ ] derived matrices/tables are generated without relying on removed runtime shims;
- [ ] no hidden network call occurs in tests marked no-network.

**Result:** `PENDING`

## 7. Build validation

```bash
python -m pip install build twine
python -m build
python -m twine check dist/*
```

Record:

| Artifact | Expected version | Result |
|---|---:|---|
| wheel | `0.1.0` | PENDING |
| sdist | `0.1.0` | PENDING |
| twine check | — | PENDING |

## 8. Package/repository boundary

Validate separately:

### Repository checkout

- [ ] complete documented workflow can locate required `config/` assets.

### Wheel/package demo

- [ ] zero-key demo works from the built/installed package if this is claimed.

### Wheel-only full scientific pipeline

- [ ] verified, **or**
- [ ] explicitly documented as unsupported/not yet guaranteed.

Do not overstate package-only reproducibility.

## 9. Security and privacy validation

On the exact candidate SHA:

- [ ] gitleaks/secret scan passes;
- [ ] repository-hygiene workflow passes;
- [ ] no `.env` with credentials;
- [ ] no tokens/private keys;
- [ ] no patient/participant/clinical data;
- [ ] no local SQLite/DB/dumps;
- [ ] no protected PDFs/full texts;
- [ ] no real `project_output*` tree in the release;
- [ ] no unreviewed ignore fingerprints suppressing findings.

**Result:** `PENDING`

## 10. Documentation consistency validation

Check current documentation against code/configuration:

- [ ] Python requirement is `>=3.12,<3.14` everywhere public;
- [ ] software version is `0.1.0` everywhere for this release;
- [ ] Git tag is `v0.1.0` everywhere for this release;
- [ ] alpha is described as maturity, not an alternate version;
- [ ] output locations match the current implementation;
- [ ] current CI/workflow names match `.github/workflows/`;
- [ ] removed Dependabot/runtime-shim statements are not presented as current;
- [ ] Evidence Engine vs Decision Engine boundary is consistent;
- [ ] human review requirements are consistent;
- [ ] protected-content policy is consistent.

**Result:** `PENDING`

## 11. Metadata validation

### `.zenodo.json`

- [ ] valid JSON;
- [ ] version `0.1.0`;
- [ ] title matches citation metadata;
- [ ] creator name(s) confirmed;
- [ ] ORCID(s) confirmed before DOI;
- [ ] affiliation(s) confirmed before DOI;
- [ ] license correct;
- [ ] no fake DOI.

### `CITATION.cff`

- [ ] validates against CFF 1.2.0;
- [ ] version `0.1.0`;
- [ ] creator metadata synchronized;
- [ ] release date added only after actual release date is known;
- [ ] DOI added only after Zenodo minting.

**Result:** `PENDING`

## 12. Provenance/copyright validation

- [ ] `NOTICE.md` matches current tree;
- [ ] removed inherited paths are described as historical only;
- [ ] LearningCircuit attribution is preserved;
- [ ] exact upstream derivation point confirmed if publicly stated;
- [ ] third-party/static assets reviewed;
- [ ] release contains no non-redistributable third-party content.

**Result:** `PENDING`

## 13. Article 1 software traceability

Before manuscript citation, verify a matrix covering the relevant method claims:

| Manuscript/method claim | Module/function | Config/rule | Test | Output artifact | Human decision point | Status |
|---|---|---|---|---|---|---|
| search strategy execution | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| normalization/deduplication | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| guide/document coding | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| screening/adjudication | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| evidence matrix/export | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |

No manuscript claim should exceed the capability actually present in the tagged release.

## 14. Release environment snapshot

Because normal development dependencies are version-ranged, capture the exact validated environment for the citable release.

Recommended record:

```bash
python --version
python -m pip freeze > RELEASE_ENVIRONMENT_0.1.0.txt
```

Store or archive an equivalent dependency snapshot/constraints artifact as part of the reproducibility record.

**Result:** `PENDING`

## 15. GO / NO-GO

| Gate | Status |
|---|---|
| VERSIONING | PENDING |
| TESTS | PENDING |
| REPRODUCIBILITY | PENDING |
| SECURITY | PENDING |
| PRIVACY | PENDING |
| COPYRIGHT | PENDING |
| PROVENANCE | PENDING |
| METADATA | PENDING |
| CITATION | PENDING |
| SCIENTIFIC CONSISTENCY | PENDING |
| DOCUMENTATION | PENDING |

## Final release decision

**Current state: NOT READY FOR ZENODO — validation has not yet been executed on the final release-candidate SHA.**

After every blocking gate passes, replace this statement with the signed-off decision and record the exact SHA that will receive tag `v0.1.0`.
