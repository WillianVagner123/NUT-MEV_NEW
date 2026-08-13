# Methodology ↔ Software Gap Analysis

Status: **closure control for the v0.3 development line**.

This document implements the mandatory gap-analysis step from the NutEV master specification. It is a control document, not evidence that a scientific gate has been completed.

## Operating rule

The repository is now in **CLOSURE MODE**: prefer completion, reconciliation and tests over new features or vocabulary expansion. Existing scientific boundaries remain binding: generated ≠ validated ≠ frozen ≠ executed ≠ retrieved ≠ screened ≠ included ≠ extracted ≠ recommendation candidate ≠ clinical recommendation.

## Status vocabulary

- **IMPLEMENTED** — supported in current runtime with auditable behavior/tests.
- **PARTIAL** — useful implementation exists but does not yet satisfy the methodological contract.
- **EXTERNAL/HUMAN** — software support may be complete while real evidence/decision must come from a licensed service or human reviewer.
- **MISSING** — required core capability is not yet represented sufficiently.

## Gap matrix

| Requirement | Current status | Current implementation | Remaining gap / risk | Closure action | Priority | Main files/modules | Tests required |
|---|---|---|---|---|---|---|---|
| Scientific state separation | IMPLEMENTED | Governance, strategy/execution state and GF-02 guards separate pilot/formal/PRISMA and human decisions | Keep semantics consistent across future gates | Preserve invariants | P0 | `docs/SCIENTIFIC_GOVERNANCE.md`, search/review modules | generated≠executed; pilot≠formal; human decision guards |
| Source Registry | PARTIAL | `config/source_registry.json` is primarily a provider crosswalk with method tracks | Does not yet represent the full institutional-source registry required by the protocol | Evolve the existing registry; do not create a parallel registry | P0 | `config/source_registry.json`, source loaders | schema + provenance + stopping/version-rule tests |
| Guideline Repository Registry | MISSING/PARTIAL | Repository discovery exists as methodology/config fragments | No single versioned registry with interface, filters, stopping/version rules and pilot/formal state | Add one canonical registry integrated with existing config provenance | P0 | `config/`, search/source modules | schema, identity and route-provenance tests |
| Sentinel suite + identity | PARTIAL | `gf02_evidence.py` validates canonical identity; priority registry contains resolved GF-02 sentinels | Full declared sentinel suite still needs reconciliation in the canonical registry before global recall claims | Expand/reconcile the existing registry only from verified identities | P0 | `config/article1_sentinel_registry.json`, `src/nutev/search/gf02_evidence.py` | identity, duplicate-ID, manifestation tests |
| Recall metrics | PARTIAL | Known-item recall is computed for resolved sentinels | Full provider/route/suite reporting depends on complete registry and real executions | Generalize reporting without changing current GF-02 evidence semantics | P0 | `gf02_evidence.py` | per-provider/version/route recall tests |
| Noise analysis | IMPLEMENTED SOFTWARE / EXTERNAL HUMAN | Deterministic sample scaffolding and validated noise classes exist | Real sample classification/precision is human evidence and is still pending | Keep infrastructure; ingest real classified sample | P0 scientific execution | GF-02 pilot/evidence modules | deterministic sample + invalid-class tests |
| Strategy versioning | IMPLEMENTED/PARTIAL | Immutable strategy identities and exact expressions are preserved | Must remain connected to generic gate/freeze objects | Bind strategy versions to gate/freeze records | P0 | strategy registry/executor | immutability + supersession tests |
| Scientific gates GF-01…GF-10 | PARTIAL | GF-02 has a specialized evidence gate; governance defines broader readiness | No generic gate record/aggregator representing all required gates | Implement a small generic gate model and global blocker evaluation | P0 | new gate module reusing current evidence/state models | blocking, authorization, no-auto-pass tests |
| PRESS | MISSING SOFTWARE OBJECT / EXTERNAL HUMAN | Rules exist in methodology/governance | No canonical machine-readable PRESS submission/review record | Add record model; approval remains human-only | P0 | gate/strategy modules + config/output schema | state-transition and no-inferred-approval tests |
| Freeze | MISSING/PARTIAL | Freeze requirements are documented; formal execution is currently refused by PLAY | No canonical immutable freeze object binding SHA/config/strategies/registries/review evidence | Implement freeze manifest + digest and mutation guards | P0 | gates, strategy, PLAY | freeze immutability + changed-config rejection |
| Scopus / Web of Science evidence | IMPLEMENTED SOFTWARE / EXTERNAL LICENSED EXECUTION | `ManualProviderEvidence` supports exact expression, timestamp, executor, totals, export hash and sentinel results | Real licensed executions/imports are still required | Do not simulate; import real evidence when available | P0 scientific execution | `gf02_evidence.py` | required-field/hash/provider tests |
| Intellectual document unit | IMPLEMENTED/PARTIAL | Current engine has deterministic identity/version/family handling | Must stay aligned with full formal corpus and sentinel unit rules | Verify parity during corpus integration; no denominator inflation | P1 | identity/dedup modules | co-publication/version/manifestation tests |
| PRISMA separation | IMPLEMENTED | GF-02/PLAY explicitly mark pilot as non-PRISMA; governance requires formal+frozen+authorized evidence | Future FORMAL PLAY must enforce all gate/freeze prerequisites | Add final formal authorization check at orchestration boundary | P0 | `play_pipeline.py`, gate module | contamination-prevention tests |
| Human R1/R2/adjudication | IMPLEMENTED/PARTIAL / HUMAN | Screening/adjudication workflow exists and AI-decision prohibition is normative | GF-07 still needs real reviewer identities, calibration and rules for the definitive run | Represent setup evidence; never fabricate decisions | P1 / pre-formal | review modules + gate records | independence/conflict/adjudication tests |
| Citation chasing | PARTIAL/VERIFY | Methodology requires one backward + one forward round per formal seed | Formal route, stopping evidence and ledger integration must be verified before core closure claim | Reuse existing provider/provenance infrastructure; implement only missing ledger/state pieces | P1 | search/provenance modules | round/stopping/dedup/provenance tests |
| Release / Zenodo readiness | PARTIAL / HUMAN+EXTERNAL | Release docs, CFF/Zenodo metadata and validation infrastructure exist | Provenance/license reconciliation (#1014), final metadata and exact candidate SHA remain open | Close only after core/scientific boundaries are honest | P1 release | `LICENSE`, `NOTICE.md`, `CITATION.cff`, `.zenodo.json`, release docs | metadata/build/reproducibility/security checks |
| Legacy workstream semantics | PARTIAL | Executable querypack/workstream pipeline is retired | Active enums/lenses/scoring/config/tests still emit or protect `busca1/busca2a/busca2b/a3` semantics | Complete #1029 with canonical semantic labels + legacy import aliases only | P0 | engine enums/models/validators, lenses, scoring, tests | legacy-input→canonical-output regression tests |
| Normative documentation parity | PARTIAL | Current governance and PLAY docs are largely aligned | Some normative docs still describe retired querypack artifacts/terms | Remove stale active-architecture claims after #1029/gate work | P0 | execution contract, provider docs, hygiene docs | documentation/link checks |

## Definition of SYSTEM CORE COMPLETE

Declare **SYSTEM CORE COMPLETE** only when all conditions below are true:

1. Every P0 row above is `IMPLEMENTED`, `EXTERNAL/HUMAN` with software support complete, or explicitly `NOT_REQUIRED` with recorded rationale.
2. No parallel search engine or active legacy search-route semantics remain.
3. Source and guideline-repository registries are canonical, versioned and provenance-aware.
4. Generic gate records can represent GF-01…GF-10 without inferring human approval.
5. PRESS and Freeze are explicit objects; Freeze binds software SHA, configuration digest, strategy/registry versions and required human evidence.
6. FORMAL/PRISMA execution cannot proceed without recorded authorization/freeze.
7. Execution failures remain failures, never zero-result evidence.
8. Intellectual-document identity preserves manifestations/co-publications/versions without inflating canonical counts.
9. New scientific functions have regression tests and normative documentation matches the active runtime.
10. No open P0 architecture blocker remains.

When these conditions are met, stop architectural expansion. After that point, accept only bug fixes, real scientific execution evidence, human/external gate records, reproducibility work and release preparation unless a versioned methodological amendment explicitly reopens architecture.

## Three distinct closure states

- **SYSTEM CORE COMPLETE** — software architecture and guards are complete.
- **ARTICLE 1 READY FOR FORMAL EXECUTION** — required scientific/human gates through GF-10 are evidenced and authorized.
- **READY FOR ZENODO** — one exact reviewed SHA also passes provenance/license, metadata, security, reproducibility and release gates.

These states must never be inferred from one another.

## Closure sequence

1. Complete #1029 legacy semantic migration.
2. Reconcile Source Registry and Guideline Repository Registry.
3. Implement the generic gate model, PRESS record and immutable Freeze object.
4. Enforce those records at the FORMAL PLAY boundary and remove stale normative querypack language.
5. Run CI/regression validation and declare `SYSTEM CORE COMPLETE` only if the definition above is satisfied.
6. Continue scientific execution in the canonical order: GF-02 real evidence → GF-03 PRESS → GF-06 → GF-07 → GF-10 → formal search → master corpus → screening → full text → extraction.
7. Treat provenance/license and Zenodo publication as a later release gate, not as proof of scientific completion.
