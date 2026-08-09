# Release Checklist — reusable template

This checklist applies to **future NutEV Evidence Engine releases**. The completed historical record for `v0.2.0` is `docs/RELEASE_RECORD_v0.2.0.md`; do not reuse this template to reinterpret or move that immutable tag.

Scientific maturity may remain **alpha** even when a new software version is published. Maturity and version identity are separate concepts.

## 0. Candidate identity

Record before validation:

- **Software version:** `<VERSION>`
- **New Git tag:** `v<VERSION>`
- **Scientific maturity:** `<MATURITY>`
- **Candidate commit SHA:** `<SHA>`
- **Validation date:** `<DATE>`

The same version must appear in the canonical version source, `.zenodo.json`, `CITATION.cff`, CHANGELOG, Git tag and GitHub Release metadata.

### Blocking tag-collision check

- [ ] target tag does not already exist;
- [ ] no historical tag will be deleted, moved or force-recreated.

## 1. Human metadata gate

Do not invent missing metadata.

- [ ] creator name/order confirmed;
- [ ] ORCID included only if verified;
- [ ] exact institutional affiliation included only if verified;
- [ ] funding/grant metadata confirmed if applicable;
- [ ] related publication DOI added only if it exists and the relation is correct;
- [ ] upstream derivation statements verified.

## 2. Provenance and licensing

- [ ] `NOTICE.md` matches the current tree;
- [ ] removed inherited paths are described as historical only;
- [ ] LearningCircuit/Local Deep Research MIT attribution is preserved;
- [ ] third-party assets have redistribution rights or are excluded;
- [ ] protected third-party full text is not bundled;
- [ ] no license change is made by assumption.

## 3. Clean-environment installation

Validate the Python versions declared by the package metadata.

- [ ] canonical suite passes on every declared CI interpreter;
- [ ] exact candidate SHA and interpreter versions are recorded;
- [ ] failures capable of changing scientific outputs are resolved or explicitly block publication.

## 4. Canonical tests and quality gates

- [ ] full canonical pytest suite passes;
- [ ] blocking Ruff checks pass;
- [ ] CodeQL passes;
- [ ] security-scan/gitleaks/repository hygiene passes;
- [ ] dependency review **actually executes** and passes.

### Dependency-review requirement

A green workflow conclusion is insufficient if the dependency-review action was skipped/unsupported. Before treating this gate as PASS:

- [ ] GitHub Dependency Graph is enabled;
- [ ] dependency-review action executes successfully;
- [ ] the step is blocking (no `continue-on-error: true` around the security gate).

The `v0.2.0` release predates this correction; its dependency review is documented as **NOT VALIDATED** in the historical release record.

## 5. Zero-key demonstration

- [ ] CLI works;
- [ ] demo requires no private API key;
- [ ] demo requires no protected PDF/full text;
- [ ] `run_summary.json` exists;
- [ ] demo is visibly synthetic and not scientific evidence.

## 6. Build distribution artifacts

- [ ] wheel builds with candidate version;
- [ ] sdist builds with candidate version;
- [ ] `twine check` passes;
- [ ] clean installed wheel exposes `nutev`;
- [ ] zero-key demo works from the installed artifact if claimed.

## 7. Configuration/package boundary

- [ ] repository-checkout scientific path is validated;
- [ ] wheel-only claims match what was actually tested;
- [ ] configuration assets required for scientific runs are available through the documented route.

## 8. Search provenance and Article 1 scientific contract

If the release can be used for Article 1 execution, verify `docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md`.

- [ ] generated queries are stored separately from executed queries;
- [ ] every expression described as executed maps to an actual attempt record;
- [ ] `query_execution_ledger.json/.csv` is generated for generic-pipeline runs;
- [ ] frozen indexed-database runs preserve exact expressions, snapshots and SHA-256 values;
- [ ] official-source track preserves manifest/config provenance and artifact hashes where applicable;
- [ ] provider limits/pagination/truncation are explicit;
- [ ] SciELO-prefix retrieval is not described as comprehensive native SciELO search;
- [ ] computational completion is separate from `scientific_readiness`;
- [ ] manuscript readiness cannot be inferred without explicit human/manuscript gates.

## 9. Documentation consistency

- [ ] Python support matches package metadata;
- [ ] release identity is consistent everywhere;
- [ ] alpha/beta/etc. is described as maturity rather than a competing version;
- [ ] output locations match code;
- [ ] workflow names match `.github/workflows/`;
- [ ] Evidence Engine vs Decision Engine boundary is consistent;
- [ ] human review requirements are consistent;
- [ ] protected-content policy is consistent;
- [ ] provider documentation matches the current tree/runtime;
- [ ] release documentation uses published/past tense only after publication;
- [ ] relative Markdown link check passes.

## 10. Security, privacy and repository hygiene

- [ ] no secrets/tokens/private keys;
- [ ] no unsafe `.env`;
- [ ] no patient/participant/identifiable clinical data;
- [ ] no local DB/dumps;
- [ ] no protected PDFs/full texts;
- [ ] no real `project_output*` tree;
- [ ] no unreviewed gitleaks suppression;
- [ ] security Actions used for release gating are pinned/reviewed according to repository policy.

## 11. Reproducibility record

Capture for the candidate:

- software version/tag/SHA;
- runner OS and Python version;
- exact resolved dependency snapshot;
- build artifacts;
- canonical test result;
- zero-key demo result;
- documentation-link validation;
- security results;
- known limitations.

For manuscript scientific runs additionally retain:

- protocol/search-strategy version;
- `config_digest` and per-config hashes;
- exact query execution ledger;
- retrieval dates;
- provider limits/truncation/pagination;
- raw snapshots/checksums where required;
- official-source manifest/artifact provenance;
- deduplication state;
- full-text/recoverability state;
- coverage-loss state;
- human screening/adjudication state;
- final PRISMA/manuscript export identifiers.

## 12. Metadata validation

### `.zenodo.json`

- [ ] valid JSON;
- [ ] candidate version correct;
- [ ] title/creator/license correct;
- [ ] no fake DOI;
- [ ] optional human metadata included only when confirmed.

### `CITATION.cff`

- [ ] valid CFF;
- [ ] candidate version correct;
- [ ] creator/title/license synchronized;
- [ ] release date only when known;
- [ ] DOI only after a real archive exists.

## 13. GO / NO-GO

Required minimum gates:

- VERSIONING — PASS
- TAG COLLISION — PASS
- TESTS — PASS
- BUILD — PASS
- ZERO-KEY DEMO — PASS
- REPRODUCIBILITY — PASS
- SECURITY — PASS
- DEPENDENCY REVIEW — PASS (actually executed)
- PRIVACY — PASS
- COPYRIGHT — PASS
- PROVENANCE — PASS
- METADATA — PASS
- CITATION — PASS
- SCIENTIFIC CONSISTENCY — PASS
- DOCUMENTATION — PASS

Only an explicit `READY FOR RELEASE` decision authorizes a new publication.

## 14. Publication and post-release record

After every gate passes:

- create a **new** immutable tag from the exact validated SHA;
- publish the GitHub Release;
- record release date, tag, commit SHA and known limitations;
- verify any Zenodo archival from the actual public record before adding a DOI;
- never move an already-published tag to add metadata;
- make DOI/documentation corrections in later commits/releases while preserving historical immutability.