# Release Checklist — v0.2.0

Prepare the first **citation-grade reconciled release** of the **NutEV Evidence Engine**. The software remains at **alpha scientific maturity**, while the release identifier is **0.2.0** and the Git tag is **v0.2.0**.

The repository already contains historical tags `v0.1.0`–`v0.1.8`; they must remain immutable and must not be reused or moved.

## 0. Candidate identity

- **Software version:** `0.2.0`
- **Planned Git tag:** `v0.2.0`
- **Scientific maturity:** alpha
- **Candidate commit SHA:** record from the final validated `main`
- **Validation date:** record from the final release workflow

The same version must appear in `src/nutev/__version__.py`, `.zenodo.json`, `CITATION.cff`, `CHANGELOG.md`, the Git tag, GitHub Release title and Zenodo version record.

### Blocking tag-collision check

Before publication:

```bash
if git rev-parse -q --verify refs/tags/v0.2.0 >/dev/null; then
  echo "ERROR: v0.2.0 already exists; do not overwrite or move it."
  exit 1
fi
```

- [ ] `v0.2.0` does not already exist.
- [ ] no historical tag will be deleted, moved or force-recreated.

## 1. Human metadata gate

Do not invent missing metadata.

- [ ] creator name/order confirmed;
- [ ] ORCID confirmed if it will be included;
- [ ] exact institutional affiliation confirmed if it will be included;
- [ ] funding/grant metadata confirmed if applicable;
- [ ] Article 1 DOI added only if it exists and the relation is appropriate;
- [ ] upstream derivation point confirmed if stated publicly.

ORCID and affiliation are valuable metadata but absence must be represented as absence, never as fabricated placeholders in the final Zenodo record.

## 2. Provenance and licensing gate

- [ ] `NOTICE.md` matches the current tree;
- [ ] removed inherited paths are historical only;
- [ ] LearningCircuit MIT attribution is preserved;
- [ ] third-party/static/binary assets have documented redistribution rights or are excluded;
- [ ] protected third-party full text is not bundled;
- [ ] no license change is made by assumption.

## 3. Clean-environment installation

Validate Python **3.12** and **3.13**, matching `>=3.12,<3.14`.

- [ ] Python 3.12 canonical suite passes.
- [ ] Python 3.13 canonical suite passes.
- [ ] exact SHA and interpreter versions are recorded.

The release-reconciliation CI already demonstrated 703 passed / 8 skipped / 1 xpassed on both interpreters; the final release candidate must still be validated at its own SHA.

## 4. Zero-key demonstration

```bash
nutev --help
nutev demo-data --project-root ./project_output_demo
test -f project_output_demo/07_logs/run_summary.json
```

- [ ] CLI works;
- [ ] demo requires no private API key;
- [ ] demo requires no protected PDF/full text;
- [ ] `run_summary.json` exists;
- [ ] demo is visibly synthetic and not scientific evidence.

## 5. Canonical tests

```bash
PYTHONPATH=src python -m pytest -q nutev_tests
```

Record exact passed/failed/skipped/xfailed/xpassed values. Any failure capable of changing corpus composition, extraction, deduplication, coding, provenance, screening, export or audit output is a release blocker until resolved or methodologically justified.

- [ ] full canonical suite passes on the final candidate.

## 6. Build distribution artifacts

```bash
python -m pip install build twine
python -m build
python -m twine check dist/*
```

- [ ] wheel builds as `0.2.0`;
- [ ] sdist builds as `0.2.0`;
- [ ] `twine check` passes;
- [ ] installed wheel exposes `nutev`;
- [ ] installed wheel can run the zero-key demo if this is claimed.

## 7. Configuration / package boundary

The repository checkout is the canonical path for complete scientific runs unless wheel-only full-pipeline reproduction is explicitly demonstrated.

- [ ] repository checkout + editable install path validated;
- [ ] wheel-only demo validated;
- [ ] wheel-only full scientific pipeline either verified or explicitly described as not guaranteed.

## 8. Documentation consistency

- [ ] Python support is `>=3.12,<3.14`;
- [ ] release identity is `0.2.0` / `v0.2.0`;
- [ ] alpha is described as maturity only;
- [ ] output locations match code;
- [ ] workflow names match `.github/workflows/`;
- [ ] Evidence Engine vs Decision Engine boundary is consistent;
- [ ] human review requirements are consistent;
- [ ] protected-content policy is consistent;
- [ ] no current instruction tells maintainers to publish a historical `v0.1.x` tag.

- [ ] relative Markdown link check passes.

## 9. Security, privacy and repository hygiene

- [ ] security-scan/gitleaks passes on exact candidate SHA;
- [ ] CodeQL passes;
- [ ] no secrets/tokens/private keys;
- [ ] no unsafe `.env`;
- [ ] no patient/participant/identifiable clinical data;
- [ ] no local DB/dumps;
- [ ] no protected PDFs/full texts;
- [ ] no real `project_output*` tree;
- [ ] no unreviewed gitleaks suppression.

## 10. Reproducibility record

The release-validation workflow must capture:

- version;
- candidate SHA;
- runner OS;
- Python version;
- exact installed dependency snapshot;
- built wheel and sdist;
- test result;
- zero-key demo result.

Scientific runs cited in manuscripts should additionally record `config_digest`, config provenance, frozen search strategy, reviewer/adjudication ledger, coverage-loss/full-text report and exact publication tables.

- [ ] release environment artifact exists.

## 11. Scientific traceability gate

Verify `docs/ARTICLE1_SOFTWARE_TRACEABILITY.md`.

- [ ] method claim → module → test → output → human boundary is documented;
- [ ] no manuscript claim exceeds the tagged implementation;
- [ ] no automated output is described as a final scientific/clinical decision.

## 12. Metadata validation

### `.zenodo.json`

- [ ] valid JSON;
- [ ] version `0.2.0`;
- [ ] title/creator/license correct;
- [ ] no fake DOI;
- [ ] optional human metadata included only when confirmed.

### `CITATION.cff`

- [ ] valid CFF 1.2.0;
- [ ] version `0.2.0`;
- [ ] creator/title/license synchronized;
- [ ] release date added only when known;
- [ ] DOI added only after Zenodo minting.

For GitHub→Zenodo archival, `.zenodo.json` is the deposit metadata file; keep `CITATION.cff` synchronized for citation tooling.

## 13. GO / NO-GO

Required statuses:

- VERSIONING — PASS
- TAG COLLISION — PASS
- TESTS — PASS
- BUILD — PASS
- ZERO-KEY DEMO — PASS
- REPRODUCIBILITY — PASS
- SECURITY — PASS
- PRIVACY — PASS
- COPYRIGHT — PASS
- PROVENANCE — PASS
- METADATA — PASS
- CITATION — PASS
- SCIENTIFIC CONSISTENCY — PASS
- DOCUMENTATION — PASS

Only `READY FOR RELEASE` authorizes publication.

## 14. Tag and GitHub Release

After every gate passes, create **new** tag `v0.2.0` from the exact validated `main` SHA. Never retag an existing release.

Release title:

**NutEV Evidence Engine v0.2.0**

The release notes must state **alpha research-software maturity** and link to `docs/RELEASE_NOTES_v0.2.0.md`.

## 15. Zenodo archival

When the GitHub→Zenodo integration is enabled:

- [ ] publish the GitHub Release;
- [ ] verify Zenodo archived exact tag `v0.2.0`;
- [ ] record Version DOI;
- [ ] record Concept DOI if applicable;
- [ ] verify actual Zenodo title/creators/version/license/keywords;
- [ ] use the Version DOI for manuscript reproducibility.

Do not claim a DOI until the Zenodo record actually exists.

## 16. Post-release record

Record release date, tag, commit SHA, GitHub Release, Zenodo Version DOI, Concept DOI if applicable, final metadata snapshot and known limitations. The archived `v0.2.0` release must remain immutable.
