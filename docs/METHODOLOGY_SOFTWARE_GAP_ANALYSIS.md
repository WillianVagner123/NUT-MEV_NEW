# Methodology ↔ Software Gap Analysis

Status: **closure control for the v0.3 development line**.

This is a control document, not evidence that any scientific, licensed or human gate has been completed. The repository is in **CLOSURE MODE**: finish reconciliation, tests and documentation; do not create parallel search systems or expand vocabulary without a versioned methodological amendment.

The governing separation remains: generated ≠ validated ≠ frozen ≠ executed ≠ retrieved ≠ screened ≠ included ≠ extracted ≠ recommendation candidate ≠ clinical recommendation.

## Gap matrix

| Requirement | Software status | Remaining scientific/external work | Priority |
|---|---|---|---|
| Scientific state separation | IMPLEMENTED | Preserve generated≠executed, PILOT≠FORMAL and human-decision boundaries | P0 |
| Source Registry | IMPLEMENTED SOFTWARE / CANDIDATE DATA | Candidate institutional records still require verified search mechanism, stopping/version rules, reviewer and verification evidence before `FROZEN` | pre-formal |
| Guideline Repository Registry | IMPLEMENTED SOFTWARE / CANDIDATE DATA | G-I-N, BIGG, AWMF, Dutch Richtlijnendatabase, Minds and Ukraine Registry remain `NOT_AUTHORIZED` until operational fields are verified | pre-formal |
| Sentinel identity + recall | IMPLEMENTED SOFTWARE / PARTIAL DATA | Reconcile the full declared sentinel suite and run real provider/route evidence before global recall claims | GF-02 |
| Noise analysis | IMPLEMENTED SOFTWARE / HUMAN | Classify the real deterministic noise sample and record reviewer evidence | GF-02 |
| Strategy versioning | IMPLEMENTED | Bind only exact immutable versions to execution and freeze evidence | P0 |
| Scientific gates GF-01…GF-10 | IMPLEMENTED SOFTWARE / HUMAN INPUTS | Actual evidence, owners, dates and decisions remain scientific/human records | pre-formal |
| PRESS | IMPLEMENTED SOFTWARE / HUMAN | Real submission/reviewer/decision evidence remains pending; approval is never inferred | GF-03 |
| Freeze | IMPLEMENTED SOFTWARE / HUMAN | Real GF-10 authorization and definitive frozen values remain pending | GF-10 |
| Scopus / Web of Science | IMPLEMENTED SOFTWARE / LICENSED EXECUTION | Import real licensed/manual execution evidence; never simulate another database as a substitute | GF-02/formal |
| FORMAL/PRISMA execution guard | IMPLEMENTED | Canonical strategy executor requires persisted gates plus exact freeze, strategy version, Git SHA and config digest; PLAY remains PILOT-only | P0 |
| Intellectual document unit | IMPLEMENTED/PARTIAL VALIDATION | Verify manifestations/co-publications/version behavior on the definitive multi-route corpus | P1 |
| R1/R2/adjudication | IMPLEMENTED WORKFLOW / HUMAN | Real reviewer identities, calibration and decisions remain pending | GF-07 |
| Citation chasing | PARTIAL/VERIFY | Verify formal backward/forward round, stopping and ledger evidence before claiming completion | P1 |
| Legacy workstream semantics | IMPLEMENTED | #1029 closed: new runtime outputs are semantic; historical `busca*`/article labels are ingest aliases only | P0 closed |
| Normative documentation parity | IN THIS CLOSURE PR | Merge the current execution/provider/PLAY contract and rerun canonical validation | P0 |
| Release / Zenodo | PARTIAL / HUMAN+EXTERNAL | #1014 provenance/license reconciliation plus final metadata and exact release SHA remain open | release |

## Implemented software controls that must not be confused with scientific completion

- `SourceRegistryRecord` and `GuidelineRepositoryRecord` validate candidate versus formal/frozen states and expose explicit registry blockers; candidate data cannot silently become formal.
- `GateRecord`, `PressRecord` and immutable `FreezeRecord` persist scientific state without inferring human approval.
- FORMAL/PRISMA execution is blocked before run creation unless persisted evidence authorizes the exact strategy version and matches the frozen Git SHA and configuration digest.
- PLAY remains a PILOT convenience/audit orchestrator; it is not the definitive multi-track FORMAL Article 1 runner.

## SYSTEM CORE COMPLETE

Do **not** declare `SYSTEM CORE COMPLETE` from this document edit alone. After this documentation PR is green and merged, perform one final P0 audit against the current `main` and open architecture issues.

Declare **SYSTEM CORE COMPLETE** only when:

1. every P0 software requirement is implemented, explicitly external/human with software support complete, or `NOT_REQUIRED` with recorded rationale;
2. no parallel search engine or active legacy search-route output remains;
3. registries are canonical/versioned and cannot silently become formal/frozen;
4. GF-01…GF-10, PRESS and Freeze are explicit persisted objects without inferred approval;
5. FORMAL/PRISMA cannot execute without the exact authorized freeze, Git SHA and configuration digest;
6. failures remain failures and intellectual-document identity does not inflate canonical counts;
7. normative docs describe the active runtime and canonical regression/security/release checks are green;
8. no open P0 architecture blocker remains.

After that state, stop architectural expansion. Accept only bug fixes, real execution evidence, human/external gate records, reproducibility work and release preparation unless a versioned methodological amendment explicitly reopens architecture.

## Distinct states

- **SYSTEM CORE COMPLETE** — software architecture and guards complete.
- **ARTICLE 1 READY FOR FORMAL EXECUTION** — real scientific/human gates through GF-10 evidenced and authorized.
- **READY FOR ZENODO** — one exact reviewed SHA also passes provenance/license, metadata, security and reproducibility gates.

Never infer one state from another.

## Remaining sequence

1. merge this normative-document parity update and rerun canonical CI/security/release validation;
2. audit remaining open P0 architecture issues and declare `SYSTEM CORE COMPLETE` only if its definition is actually satisfied;
3. continue science separately: GF-02 real evidence → GF-03 PRESS → GF-06 → GF-07 → GF-10 → formal search → master corpus → screening → full text → extraction;
4. keep #1014/Zenodo as a later release gate, not as proof of scientific completion.
