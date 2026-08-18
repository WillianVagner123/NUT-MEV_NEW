# Release Checklist — NutEV Reference Engine

This checklist governs stable NutEV Reference Engine releases. Historical pre-v1 releases remain immutable and are documented separately.

## 0. Candidate identity

Record before validation:

- **Software version:** `<VERSION>`
- **New Git tag:** `v<VERSION>`
- **Candidate commit SHA:** `<SHA>`
- **Validation date:** `<DATE>`

The same version must appear in `src/nutev/__version__.py`, `.zenodo.json`, `CITATION.cff`, CHANGELOG, Git tag and GitHub Release metadata.

- [ ] target tag does not already exist;
- [ ] no historical tag will be deleted, moved or force-recreated.

## 1. Product-scope gate

Supported product flow:

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT
```

- [ ] README describes the Reference Engine, not a review workflow;
- [ ] ranking is described as reading/reference priority only;
- [ ] no automatic scientific INCLUDE/EXCLUDE claim;
- [ ] no clinical recommendation claim;
- [ ] Scopus/Web of Science are not simulated;
- [ ] public ranking outputs contain no legacy PRISMA/FORMAL/screening control fields.

## 2. Human metadata gate

Do not invent missing metadata.

- [ ] creator name/order confirmed;
- [ ] ORCID included only if verified;
- [ ] institutional affiliation included only if verified;
- [ ] funding/grant metadata included only if confirmed;
- [ ] DOI added only after a real archive record exists and is verified.

## 3. Provenance and licensing

- [ ] `LICENSE` remains valid for the release;
- [ ] `NOTICE.md` preserves required upstream attribution;
- [ ] protected third-party full text is not bundled;
- [ ] no license change is made by assumption.

## 4. Canonical tests and quality gates

- [ ] Python 3.12 canonical suite passes;
- [ ] Python 3.13 canonical suite passes;
- [ ] Windows smoke passes;
- [ ] full canonical pytest suite passes;
- [ ] compile gate passes;
- [ ] Ruff blocking checks pass;
- [ ] repository typecheck gate passes;
- [ ] CodeQL passes;
- [ ] security scan/gitleaks passes;
- [ ] dependency review actually executes and passes;
- [ ] release artifact validation passes.

## 5. Reference-ranking contract

- [ ] taxonomy changes score as expected;
- [ ] title matches weigh more than abstract-only matches;
- [ ] focus keywords increase relevant priority;
- [ ] document-type weighting works;
- [ ] provider weighting works;
- [ ] recency is secondary and does not dominate relevance;
- [ ] technical deduplication prevents repeated references;
- [ ] identical inputs/configuration produce deterministic order;
- [ ] CSV/JSONL/Markdown order is consistent;
- [ ] missing providers do not fabricate results;
- [ ] provider/source identity remains explicit;
- [ ] LILACS/BVS and SciELO retain correct source identity.

## 6. Build distribution artifacts

- [ ] `python -m build` succeeds;
- [ ] wheel declares candidate version;
- [ ] sdist declares candidate version;
- [ ] `twine check` passes;
- [ ] clean virtual environment can install the wheel;
- [ ] installed distribution reports the expected version;
- [ ] CLI startup succeeds from the clean wheel.

## 7. Documentation consistency

- [ ] README version is correct;
- [ ] package metadata uses Reference Engine identity;
- [ ] `.zenodo.json` uses Reference Engine identity;
- [ ] `CITATION.cff` uses Reference Engine identity;
- [ ] release notes exist;
- [ ] CHANGELOG includes the release;
- [ ] current Quick Start does not point to legacy workflow documentation;
- [ ] legacy scientific-review documents are identified as historical/non-v1 material.

## 8. Security, privacy and repository hygiene

- [ ] no secrets/tokens/private keys;
- [ ] no unsafe `.env`;
- [ ] no identifiable clinical/patient data;
- [ ] no protected PDFs/full texts in release artifacts;
- [ ] no real project-output corpus is accidentally committed;
- [ ] release Actions are pinned/reviewed according to repository policy.

## 9. Metadata validation

### `.zenodo.json`

- [ ] valid JSON;
- [ ] candidate version correct;
- [ ] title/creator/license correct;
- [ ] keywords match supported product scope;
- [ ] no fake DOI.

### `CITATION.cff`

- [ ] valid CFF;
- [ ] candidate version correct;
- [ ] creator/title/license synchronized;
- [ ] release date correct;
- [ ] DOI absent until a real archive exists.

## 10. GO / NO-GO

Required minimum gates:

- VERSIONING — PASS
- TAG COLLISION — PASS
- TESTS — PASS
- BUILD — PASS
- RANKING CONTRACT — PASS
- SECURITY — PASS
- DEPENDENCY REVIEW — PASS
- PRIVACY — PASS
- COPYRIGHT — PASS
- PROVENANCE — PASS
- METADATA — PASS
- CITATION — PASS
- DOCUMENTATION — PASS

Only an explicit `READY FOR RELEASE` decision on the exact validated SHA authorizes publication.

## 11. Publication

After every gate passes:

1. merge the release PR;
2. record the exact final `main` SHA;
3. confirm version/metadata again on that SHA;
4. create a new immutable tag from that exact SHA;
5. publish the GitHub Release;
6. verify Zenodo archival from the actual public record before adding a DOI;
7. never move an already-published tag to add metadata.

## v1.0.0 candidate

For the first stable release, use `docs/RELEASE_V1_0_0.md` and `docs/RELEASE_V1_AUDIT.md` together with this checklist.
