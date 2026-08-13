# Methodology ↔ Software Gap Analysis

Status: **SYSTEM CORE COMPLETE — software-only closure for the v0.3 development line**.

Declaration date: **2026-08-13**. Audited software baseline before this documentation-only record: `9e41aa895f716367ae394f429abc21e5bfee20a4`.

This declaration means the core software architecture, scientific-state guards and P0 closure controls are complete. It is **not** evidence that any scientific, licensed or human gate has been completed. The repository remains in **CLOSURE MODE**: no parallel search systems or open-ended vocabulary expansion without a versioned methodological amendment.

The governing separation remains: generated ≠ validated ≠ frozen ≠ executed ≠ retrieved ≠ screened ≠ included ≠ extracted ≠ recommendation candidate ≠ clinical recommendation.

## Gap matrix

| Requirement | Software status | Remaining scientific/external work | Priority |
|---|---|---|---|
| Scientific state separation | IMPLEMENTED | Preserve generated≠executed, PILOT≠FORMAL and human-decision boundaries | closed core |
| Source Registry | IMPLEMENTED SOFTWARE / CANDIDATE DATA | Candidate institutional records still require verified search mechanism, stopping/version rules, reviewer and verification evidence before `FROZEN` | pre-formal |
| Guideline Repository Registry | IMPLEMENTED SOFTWARE / CANDIDATE DATA | G-I-N, BIGG, AWMF, Dutch Richtlijnendatabase, Minds and Ukraine Registry remain `NOT_AUTHORIZED` until operational fields are verified | pre-formal |
| Sentinel identity + recall | IMPLEMENTED SOFTWARE / PARTIAL DATA | Reconcile the full declared sentinel suite and run real provider/route evidence before global recall claims | GF-02 |
| Noise analysis | IMPLEMENTED SOFTWARE / HUMAN | Classify the real deterministic noise sample and record reviewer evidence | GF-02 |
| Strategy versioning | IMPLEMENTED | Bind only exact immutable versions to execution and freeze evidence | closed core |
| Scientific gates GF-01…GF-10 | IMPLEMENTED SOFTWARE / HUMAN INPUTS | Actual evidence, owners, dates and decisions remain scientific/human records | pre-formal |
| PRESS | IMPLEMENTED SOFTWARE / HUMAN | Real submission/reviewer/decision evidence remains pending; approval is never inferred | GF-03 |
| Freeze | IMPLEMENTED SOFTWARE / HUMAN | Real GF-10 authorization and definitive frozen values remain pending | GF-10 |
| Scopus / Web of Science | IMPLEMENTED SOFTWARE / LICENSED EXECUTION | Import real licensed/manual execution evidence; never simulate another database as a substitute | GF-02/formal |
| FORMAL/PRISMA execution guard | IMPLEMENTED | Canonical strategy executor requires persisted gates plus exact freeze, strategy version, Git SHA and config digest; PLAY remains PILOT-only | closed core |
| Global search input safety/UI | IMPLEMENTED | #1020 closed after validated normalization, unsafe-input rejection and controlled dashboard/provider-filter warnings | closed core |
| Intellectual document unit | IMPLEMENTED/PARTIAL VALIDATION | Verify manifestations/co-publications/version behavior on the definitive multi-route corpus | P1 scientific validation |
| R1/R2/adjudication | IMPLEMENTED WORKFLOW / HUMAN | Real reviewer identities, calibration and decisions remain pending | GF-07 |
| Citation chasing | PARTIAL/VERIFY | Verify formal backward/forward round, stopping and ledger evidence before claiming scientific completion | P1 scientific execution |
| Legacy workstream semantics | IMPLEMENTED | #1029 closed: new runtime outputs are semantic; historical `busca*`/article labels are ingest aliases only | closed core |
| Normative documentation parity | IMPLEMENTED | #1044 merged with full CI/security/release validation | closed core |
| Release / Zenodo | PARTIAL / HUMAN+EXTERNAL | #1014 provenance/license reconciliation plus final metadata and exact release SHA remain open | release |

## Implemented software controls that must not be confused with scientific completion

- `SourceRegistryRecord` and `GuidelineRepositoryRecord` validate candidate versus formal/frozen states and expose explicit registry blockers; candidate data cannot silently become formal.
- `GateRecord`, `PressRecord` and immutable `FreezeRecord` persist scientific state without inferring human approval.
- FORMAL/PRISMA execution is blocked before run creation unless persisted evidence authorizes the exact strategy version and matches the frozen Git SHA and configuration digest.
- Global search input validation rejects unsafe Boolean/provider syntax, normalizes declared filters and exposes unsupported-provider filters without silently claiming they were applied.
- PLAY remains a PILOT convenience/audit orchestrator; it is not the definitive multi-track FORMAL Article 1 runner.

## SYSTEM CORE COMPLETE — declaration

**DECLARED: YES, software-only.**

The final P0 audit after #1044 and #1045 found no open architecture/software-core issue. The remaining open issues are deliberately outside the core-software-complete state:

- **#1010** — canonical scientific execution path;
- **#1012** — current GF-02 scientific blocker requiring real PubMed/noise/Scopus/WoS evidence;
- **#1011** — downstream extraction/codebook work;
- **#1014** — provenance/license and next-release/Zenodo gate.

The declaration criteria are satisfied at the software level:

1. every P0 software requirement is implemented or represented as external/human with software support complete;
2. no parallel search engine or active legacy search-route output remains;
3. registries are canonical/versioned and cannot silently become formal/frozen;
4. GF-01…GF-10, PRESS and Freeze are explicit persisted objects without inferred approval;
5. FORMAL/PRISMA cannot execute without the exact authorized freeze, Git SHA and configuration digest;
6. failures remain failures and intellectual-document identity has explicit controls against denominator inflation;
7. normative docs describe the active runtime and canonical regression/security/release checks are green;
8. no open P0 architecture blocker remains.

From this point, stop architectural expansion. Accept only bug fixes, real execution evidence, human/external gate records, reproducibility work and release preparation unless a versioned methodological amendment explicitly reopens architecture.

## Distinct states

- **SYSTEM CORE COMPLETE: YES** — software architecture and guards complete.
- **ARTICLE 1 READY FOR FORMAL EXECUTION: NO** — GF-02 is still open; PRESS/GF-06/GF-07/GF-10 real evidence is not authorized.
- **READY FOR ZENODO: NO** — #1014 remains open and no new release/DOI is authorized by this declaration.

Never infer one state from another.

## Remaining sequence

1. continue GF-02 with real evidence: exact PubMed v0.2/v0.3 execution, sentinel reconciliation/recall, classified noise sample and genuine Scopus/WoS licensed/manual evidence;
2. only after GF-02 is ready, proceed to GF-03 PRESS → GF-06 → GF-07 → GF-10;
3. execute the formal multi-route search only after the exact freeze is authorized;
4. then build the master corpus → R1/R2 screening → full text → extraction/codebook;
5. keep #1014/Zenodo as a later release gate, not as proof of scientific completion.
