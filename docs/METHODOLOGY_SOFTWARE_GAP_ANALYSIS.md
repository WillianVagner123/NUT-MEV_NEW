# Methodology ↔ Software Gap Analysis

Status: **SYSTEM CORE COMPLETE — software-only; Article 1 scientific execution remains pre-PRESS.**

Original software-core declaration: **2026-08-13**. Scientific-state reconciliation updated: **2026-08-18**.

`SYSTEM CORE COMPLETE` means architecture, guards and P0 software controls are complete. It does **not** mean GF-02, PRESS, FREEZE, FORMAL execution or PRISMA are complete.

The governing separation remains:

`generated ≠ validated ≠ frozen ≠ executed ≠ retrieved ≠ screened ≠ included ≠ extracted ≠ recommendation candidate ≠ clinical recommendation`

## Current Article 1 state

- **Software core:** COMPLETE (software-only).
- **Current B-NORM-PUBMED candidate:** **v0.5**, PILOT, non-PRISMA.
- **v0.4:** superseded historical evidence of a PubMed Boolean-semantics bug; not executable.
- **GF-02 pre-PRESS:** OPEN until real v0.5 PubMed evidence, sentinel assessment, human rescue-only noise review and explicit human `READY_FOR_PRESS`/`NOT_READY_FOR_PRESS` decision are persisted.
- **GF-03 PRESS:** downstream of GF-02 READY_FOR_PRESS; never inferred.
- **Scopus/Web of Science:** not operationally available in the current project environment because licensed access is unavailable. They must not be simulated or left represented as executed/pending mandatory routes.
- **LILACS/BVS:** adopted as a native regional bibliographic route; software capture layer implemented, scientific validation/execution evidence still required.
- **SciELO:** adopted as a native regional supplementary route through the official SciELO search interface; this is distinct from the historical Crossref DOI-prefix approximation.
- **Europe PMC/OpenAlex/Crossref/DOAJ/Semantic Scholar:** open supplementary discovery/metadata routes; they broaden retrieval but are not claimed equivalents of Scopus/Web of Science.
- **FREEZE / FORMAL / PRISMA:** downstream and not authorized.

See `docs/ARTICLE1_OPEN_DATABASES_DECISION.md` for the provider decision and provenance rules.

## Canonical sequence

1. execute and audit the exact current **B-NORM-PUBMED v0.5 PILOT**;
2. preserve provider totals, exact expressions, NCBI query translation/warnings, snapshots/hashes, truncation/capping and software SHA;
3. audit the declared sentinel suite and the NORM-035/NORM-063 mechanism controls;
4. complete human classification/reviewer evidence for the deterministic rescue-only sample;
5. record the human GF-02 decision: `READY_FOR_PRESS` or `NOT_READY_FOR_PRESS`;
6. if ready, proceed to **GF-03 PRESS**;
7. incorporate material PRESS changes in a new version and retest affected PubMed behavior;
8. validate and document the final native LILACS/BVS and SciELO routes plus the declared open supplementary providers actually retained by protocol;
9. close remaining applicable scientific/human gates;
10. authorize **GF-10 FREEZE** binding exact Git SHA, strategy versions, provider routes, registries, PRESS evidence, filters/date rule, reviewers and configuration digest;
11. execute FORMAL identification only from the authorized frozen state;
12. only legitimate FORMAL/frozen runs can feed PRISMA accounting, followed by corpus, R1/R2, full text and extraction/codebook.

## Software controls

| Requirement | Software state | Scientific/external state |
|---|---|---|
| Scientific-state separation | IMPLEMENTED | Preserve PILOT ≠ FORMAL and software ≠ human decision |
| Sentinel registry | IMPLEMENTED | Declared identity suite resolved; observed retrieval still requires current execution evidence |
| GF-02 PubMed runner | IMPLEMENTED / CURRENT-CANDIDATE AWARE | v0.5 real PILOT + human noise review pending |
| PubMed parser evidence | IMPLEMENTED | Query translation/warnings must be preserved; semantic Boolean warnings fail the PILOT package |
| GF-02 pre-PRESS gate | IMPLEMENTED | Human READY_FOR_PRESS decision required |
| PRESS | IMPLEMENTED SOFTWARE / HUMAN | Submission/reviewer/decision pending |
| LILACS/BVS native capture | IMPLEMENTED BASELINE | Real search evidence + parser verification required |
| SciELO native capture | IMPLEMENTED BASELINE | Real search evidence + parser verification required |
| Scopus/WoS | NOT AVAILABLE / NOT SIMULATED | If unavailable at FREEZE, report as non-executed licensed databases and limitation |
| Open supplementary providers | IMPLEMENTED BASELINE | Protocol must declare which are retained and how they are used |
| GF-01…GF-10 records | IMPLEMENTED SOFTWARE / HUMAN INPUTS | Actual evidence/owners/dates/decisions remain scientific records |
| FREEZE | IMPLEMENTED SOFTWARE / HUMAN | Exact authorization pending |
| FORMAL/PRISMA guard | IMPLEMENTED | Execution remains blocked until exact authorized freeze |
| R1/R2/adjudication | IMPLEMENTED WORKFLOW / HUMAN | Real reviewer/calibration decisions remain human |
| Release/Zenodo | PARTIAL / EXTERNAL | Separate release gate; never proof of scientific completion |

## Single-source UI rule

The NutEV Engine must derive and display one current Article 1 phase from persisted evidence. The UI must distinguish, rather than combine ambiguously:

1. `SYSTEM CORE COMPLETE` (software-only);
2. `GF02_PUBMED_PILOT`;
3. `GF02_NOISE_REVIEW`;
4. `GF02_HUMAN_DECISION`;
5. `GF03_PRESS`;
6. `POST_PRESS_PROVIDER_VALIDATION` — LILACS/BVS, SciELO and any declared open supplementary routes;
7. `FREEZE`;
8. `FORMAL/PRISMA`.

A generic message such as “GF-02, PRESS, FREEZE and formal search are open” may be true but is insufficient as the primary state because it hides sequencing. The UI should state the **current** phase and mark later gates as downstream.

## Invariants

- PILOT and `REAL_DISCOVERY_NONFORMAL` outputs are never FORMAL or PRISMA-eligible.
- A successful software run does not infer scientific interpretation, READY_FOR_PRESS, PRESS approval or FREEZE authorization.
- v0.4 historical evidence must not be rewritten; it documents the Boolean failure that justified v0.5.
- Scopus/WoS must not be simulated through another provider.
- LILACS/BVS, SciELO, Europe PMC, OpenAlex, Crossref, DOAJ and Semantic Scholar must not be described as equivalents of Scopus/WoS.
- Parser failure, HTTP failure, missing credentials, truncation or layout change never become “zero results”.
- Scientifically meaningful strategy/provider changes require explicit versioning and affected-gate re-evaluation.
