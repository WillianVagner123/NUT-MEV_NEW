# Release Checklist — v0.1.0

Prepare the first citable public release of the **NutEV Evidence Engine**. The software remains at **alpha scientific maturity**, but the release identifier is standardized as **0.1.0** and the Git tag as **v0.1.0**.

> **Do not publish automatically.** This checklist defines the gates. A human maintainer performs the final tag/release/Zenodo publication only after every blocking gate is satisfied.

## 0. Candidate identity

Record before validation:

- **Software version:** `0.1.0`
- **Planned Git tag:** `v0.1.0`
- **Scientific maturity:** alpha
- **Candidate commit SHA:** `HUMAN INPUT REQUIRED — fill after final reconciliation commit`
- **Validation date:** `HUMAN INPUT REQUIRED`

The same version must appear in:

- `src/nutev/__version__.py`;
- `pyproject.toml` dynamic version resolution;
- `.zenodo.json`;
- `CITATION.cff`;
- `CHANGELOG.md`;
- Git tag;
- GitHub Release title;
- Zenodo Version record.

Do not mix `0.1.0`, `0.1.0-alpha`, and `v1.0-artigo1` for the same release.

## 1. Human metadata gate

Before DOI minting, confirm without guessing:

- [ ] creator name(s) and order;
- [ ] ORCID(s);
- [ ] exact institutional affiliation(s);
- [ ] funding/grant metadata, if applicable;
- [ ] Article 1 DOI, if already available and intended as a related identifier;
- [ ] exact upstream derivation point if it will be stated publicly.

Missing human metadata must remain explicitly marked `HUMAN INPUT REQUIRED`; it must never be fabricated.

## 2. Provenance and licensing gate

- [ ] `NOTICE.md` matches the current repository tree.
- [ ] Removed inherited paths are described as historical only.
- [ ] LearningCircuit MIT attribution is preserved.
- [ ] Third-party/static/binary assets in the release have redistribution rights documented or are removed.
- [ ] No license changes are made by assumption.

## 3. Clean-environment installation

Validate at least Python **3.12** and **3.13**, matching the declared support window `>=3.12,<3.14`.

Example:

```bash
python3.12 -m venv /tmp/nutev-rel
. /tmp/nutev-rel/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dashboard]"
```

Record OS, Python version, exact command, result and candidate commit SHA.

- [ ] Python 3.12 install succeeds.
- [ ] Python 3.13 install succeeds or an explicitly justified support decision is made before release.

## 4. Zero-key demonstration

```bash
nutev --help
nutev demo-data --project-root ./project_output_demo
test -f project_output_demo/07_logs/run_summary.json && echo "OK: demo output present"
```

- [ ] CLI help works.
- [ ] Demo runs without private API keys or protected data.
- [ ] Demo output is clearly labeled synthetic / not scientific evidence.

## 5. Canonical tests

```bash
PYTHONPATH=src python -m pytest -q nutev_tests
```

Record:

- Python version;
- commit SHA;
- total tests;
- passed;
- failed;
- skipped;
- warnings relevant to scientific output.

- [ ] Full canonical suite passes on the release candidate, or every failure is classified and a release-blocking decision is documented.

Any failure capable of changing scientific corpus composition, extraction, deduplication, coding, provenance, screening, export or audit output is a **release blocker** until resolved or methodologically justified.

## 6. Build distribution artifacts

```bash
python -m pip install build twine
python -m build
python -m twine check dist/*
```

- [ ] wheel builds;
- [ ] sdist builds;
- [ ] `twine check` passes;
- [ ] artifact filenames identify version `0.1.0`.

## 7. Configuration / package boundary

The repository checkout is the canonical path for full scientific runs unless the release validation proves that all required `config/` assets are bundled and resolvable from an installed distribution.

Validate and document separately:

- [ ] clone + editable install path;
- [ ] wheel-only demo path;
- [ ] wheel-only full-pipeline path, if claimed.

Do not claim that wheel-only installation reproduces the complete scientific pipeline unless it is actually verified.

## 8. Documentation consistency

Verify that public documentation agrees with the release candidate on:

- [ ] Python support window;
- [ ] version/tag;
- [ ] output paths;
- [ ] current workflows;
- [ ] current dependency policy;
- [ ] Evidence Engine vs Decision Engine boundary;
- [ ] human-review requirements;
- [ ] protected-content policy.

Relative-link check:

```bash
python - <<'PY'
import re, pathlib, sys
root = pathlib.Path('.')
bad = []
for md in root.rglob('*.md'):
    if any(p in md.parts for p in ('.git','node_modules','.venv')):
        continue
    text = md.read_text(encoding='utf-8', errors='ignore')
    for m in re.finditer(r'\]\(([^)]+)\)', text):
        link = m.group(1).split('#')[0].strip()
        if not link or link.startswith(('http://','https://','mailto:')):
            continue
        if not (md.parent / link).exists():
            bad.append(f"{md}: {link}")
print("\n".join(bad) if bad else "OK: no broken relative links")
sys.exit(1 if bad else 0)
PY
```

- [ ] No broken relative documentation links.

## 9. Security, privacy and repository hygiene

- [ ] `security-scan` / gitleaks passes on the exact release candidate SHA.
- [ ] no secrets, tokens, private keys or credentials are tracked;
- [ ] no `.env` files are tracked except safe examples/templates;
- [ ] no patient, participant or identifiable clinical data is tracked;
- [ ] no local DB/dump is tracked;
- [ ] no protected PDFs/full texts are tracked;
- [ ] no real `project_output*` directory is tracked;
- [ ] `.gitleaksignore` contains only manually triaged false positives, if any.

## 10. Reproducibility manifest

Create or update a release-specific reproducibility record containing:

- version;
- commit SHA;
- tag;
- OS / Python used for validation;
- dependency snapshot or constraints/lock used for the release;
- config files and `config_digest` where applicable;
- external services/API dependencies;
- zero-key demo result;
- canonical test result;
- known limitations.

- [ ] Reproducibility manifest exists and points to the exact release candidate.

## 11. Scientific traceability gate

Before citing the software in Article 1, create/verify the mapping:

`method claim → software module → configuration/rule → test → output artifact → human decision point`

- [ ] No manuscript claim attributes a function to this release that the release does not implement.
- [ ] No automated output is described as a final scientific/clinical decision.

## 12. Metadata validation

- [ ] `.zenodo.json` is valid JSON and identifies version `0.1.0`.
- [ ] `CITATION.cff` validates as CFF 1.2.0.
- [ ] title, version, creator identity and license are synchronized across both files.
- [ ] ORCID and affiliation are confirmed before DOI minting.
- [ ] no placeholder DOI is represented as real.

For the GitHub→Zenodo archival workflow, treat `.zenodo.json` as the deposit metadata source and keep `CITATION.cff` synchronized for citation tooling/GitHub presentation.

## 13. Final GO / NO-GO

Produce a signed-off report with:

- VERSIONING — PASS/FAIL
- TESTS — PASS/FAIL
- REPRODUCIBILITY — PASS/FAIL
- SECURITY — PASS/FAIL
- PRIVACY — PASS/FAIL
- COPYRIGHT — PASS/FAIL
- PROVENANCE — PASS/FAIL
- METADATA — PASS/FAIL
- CITATION — PASS/FAIL
- SCIENTIFIC CONSISTENCY — PASS/FAIL
- DOCUMENTATION — PASS/FAIL

Only `READY FOR RELEASE` authorizes publication.

## 14. Tag and GitHub Release — manual after GO

After every gate passes:

```bash
git tag -a v0.1.0 -m "NutEV Evidence Engine v0.1.0"
git push origin v0.1.0
```

Create a GitHub Release titled:

**NutEV Evidence Engine v0.1.0**

Keep the repository/software maturity description explicit as **alpha** in the release notes.

Do not retag or move an already published tag silently.

## 15. Zenodo archival

After GitHub Release publication and only when the GitHub→Zenodo integration is enabled:

- [ ] verify that Zenodo archived the exact `v0.1.0` release;
- [ ] record the Version DOI;
- [ ] record the Concept DOI when applicable;
- [ ] verify title, creators, version, license, keywords and related identifiers in the actual Zenodo record;
- [ ] update later repository commits with the DOI badge / citation metadata without rewriting the archived release.

## 16. Post-release record

Record:

- release date;
- tag;
- commit SHA;
- GitHub Release URL;
- Zenodo Version DOI;
- Zenodo Concept DOI, if applicable;
- final metadata snapshot;
- known limitations carried into the release.

The archived `v0.1.0` release must remain immutable as the historical software object cited by the study.
