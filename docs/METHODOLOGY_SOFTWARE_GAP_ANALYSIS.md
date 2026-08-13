# Methodology ↔ Software Gap Analysis

Status: **closure control for the v0.3 development line**.

This is a control document, not evidence that any scientific/human gate has been completed. The repository is in **CLOSURE MODE**: finish required architecture and reconciliation; do not expand vocabulary or create parallel systems.

## Gap matrix

| Requirement | Software status | Remaining scientific/external work | Priority |
|---|---|---|---|
| Scientific state separation | IMPLEMENTED | Preserve generated≠executed, PILOT≠FORMAL and human-decision boundaries | P0 |
| Source Registry | IMPLEMENTED SOFTWARE | Candidate institutional records still need verified operational fields before freeze | external/pre-formal |
| Guideline Repository Registry | IMPLEMENTED SOFTWARE | G-I-N/BIGG/AWMF/Dutch/Minds/Ukraine operational fields remain `NOT_AUTHORIZED` until verified | external/pre-formal |
| Sentinel identity + recall | IMPLEMENTED SOFTWARE / PARTIAL DATA | Complete/reconcile the declared suite before global recall claims; real executions still required | GF-02 |
| Noise analysis | IMPLEMENTED SOFTWARE | Human classification of the real frozen sample remains pending | GF-02 |
| Strategy versioning | IMPLEMENTED | Bind only exact versions to freeze/execution evidence | P0 |
| Scientific gates GF-01…GF-10 | IMPLEMENTED SOFTWARE | Actual evidence/owners/dates remain scientific/human inputs | pre-formal |
| PRESS | IMPLEMENTED SOFTWARE / HUMAN | Real reviewer submission/decision remains external; approval is never inferred | GF-03 |
| Freeze | IMPLEMENTED SOFTWARE / HUMAN | Real GF-10 authorization and definitive frozen values remain pending | GF-10 |
| Scopus / Web of Science | IMPLEMENTED SOFTWARE / LICENSED EXECUTION | Import real licensed/manual execution evidence | GF-02/formal |
| PRISMA separation | IMPLEMENTED | FORMAL/PRISMA strategy executor requires persisted gates + exact freeze/SHA/config digest; PLAY remains PILOT-only | P0 |
| Intellectual document unit | IMPLEMENTED/PARTIAL VALIDATION | Verify behavior on definitive multi-route corpus | P1 |
| R1/R2/adjudication | IMPLEMENTED WORKFLOW / HUMAN | Real reviewer identities, calibration and decisions remain pending | GF-07 |
| Citation chasing | PARTIAL/VERIFY | Formal round/stopping/ledger integration can remain P1; representable as GF-08 blocker meanwhile | P1 |
| Legacy workstream semantics | PARTIAL | Semantic enum/lenses are active; finish retirement/canonicalization of residual unused scoring/source outputs under #1029 | P0 |
| Normative documentation parity | IMPLEMENTED IN CLOSURE BRANCH | Merge current execution/provider/PLAY contract; keep historical terms only as history | P0 |
| Release / Zenodo | PARTIAL / HUMAN+EXTERNAL | #1014 provenance/license + final metadata/exact release SHA remain open | release |

## SYSTEM CORE COMPLETE

Declare **SYSTEM CORE COMPLETE** only when:

1. every P0 software row above is implemented or explicitly external/human with software support complete;
2. no parallel search engine or active legacy search-route output remains;
3. registries are canonical/versioned and cannot silently become formal/frozen;
4. GF-01…GF-10, PRESS and Freeze are explicit persisted objects without inferred approval;
5. FORMAL/PRISMA cannot execute without the exact authorized freeze, Git SHA and configuration digest;
6. failures remain failures and document identity does not inflate canonical counts;
7. normative docs describe the active runtime and regression/security/release checks are green;
8. no open P0 architecture blocker remains.

After that state, stop architectural expansion. Accept only bug fixes, real execution evidence, human/external gate records, reproducibility work and release preparation unless a versioned methodological amendment explicitly reopens architecture.

## Distinct states

- **SYSTEM CORE COMPLETE** — software architecture/guards complete.
- **ARTICLE 1 READY FOR FORMAL EXECUTION** — real scientific/human gates through GF-10 evidenced and authorized.
- **READY FOR ZENODO** — one exact reviewed SHA also passes provenance/license, metadata, security and reproducibility gates.

Never infer one state from another.

## Remaining closure sequence

1. finish #1029 residual legacy-semantic cleanup;
2. merge the normative-document parity;
3. rerun canonical CI/security/release validation and audit P0 blockers;
4. only then declare `SYSTEM CORE COMPLETE` if the definition above is satisfied;
5. continue science separately: GF-02 real evidence → PRESS → GF-06 → GF-07 → GF-10 → formal search → corpus → screening → full text → extraction;
6. handle #1014/Zenodo as a later release gate.
