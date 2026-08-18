# Release checklist

Use this checklist against the exact candidate SHA.

## Identity

- [ ] `src/nutev/__version__.py` matches the intended release version.
- [ ] `CITATION.cff` matches the same version and product title.
- [ ] `.zenodo.json` matches the same version and product title.
- [ ] `README.md` describes the current Reference Engine scope.
- [ ] No DOI is present unless an actual archive record has issued it.

## Product validation

- [ ] Python 3.12 test job passes.
- [ ] Python 3.13 test job passes.
- [ ] Windows smoke passes.
- [ ] `python -m compileall -q src tools nutev_tests` passes.
- [ ] blocking Ruff checks pass.
- [ ] repository type-check job passes.
- [ ] ranking tests confirm taxonomy, focus, provider weight, recency, deduplication and deterministic export behavior.
- [ ] provider failures are explicit and do not fabricate records.
- [ ] LILACS/BVS and SciELO provider identity is preserved.

## Security and dependency gates

- [ ] secret scan passes.
- [ ] dependency review passes.
- [ ] CodeQL passes.

## Distribution

- [ ] `python -m build` produces wheel and sdist.
- [ ] `twine check` passes.
- [ ] clean wheel installation passes `pip check`.
- [ ] installed `nutev --version` reports the intended version.

## GitHub and archive

- [ ] release PR is merged without bypassing required checks.
- [ ] exact final `main` SHA is recorded.
- [ ] tag points exactly to that SHA and is not moved afterward.
- [ ] GitHub Release uses the same tag/version/title.
- [ ] archive ingestion is verified after GitHub Release publication.
- [ ] archive metadata and files are checked before claiming an archive DOI.
