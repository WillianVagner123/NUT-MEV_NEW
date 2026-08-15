# NutEV Evidence Engine — Master Scope and Definition of Done

Status: **canonical implementation scope for the current PhD evidence workflow**.

This document defines what NutEV Evidence Engine must do, what is already implemented, what still requires software work, what requires human/external scientific evidence, and when the Engine may be considered complete enough to stop architectural expansion and return focus to manuscript writing.

The study protocol, ABCD-NutEV codebook and versioned D-xxx methodological decisions remain the scientific-method authority. The exact Engine SHA defines what software actually executed. Human reviewers remain authoritative for scientific inclusion/exclusion, final ABCD coding, explicit relations, consensus and adjudication.

---

## 1. Mission

NutEV Evidence Engine is the **single canonical computational execution layer** for the NutEV evidence workflow. It must provide a reproducible and auditable chain from protocol-defined evidence identification through manuscript-facing outputs without creating a second review engine in Google Sheets, ad hoc scripts, notebooks or external patches.

The canonical chain is:

```text
QUESTION / PROTOCOL
        ↓
METHOD DECISIONS + CODEBOOK
        ↓
SEARCH STRATEGY VERSION
        ↓
PILOT EXECUTION
        ↓
PRESS / SCIENTIFIC GATES
        ↓
FREEZE
        ↓
FORMAL EXECUTION
        ↓
RAW RECORDS + PROVENANCE
        ↓
NORMALIZATION + DEDUPLICATION
        ↓
CORPUS MASTER
        ↓
TITLE/ABSTRACT SCREENING
        ↓
FULL-TEXT RETRIEVAL / OCR
        ↓
FULL-TEXT SCREENING
        ↓
ABCD 34/34 EXTRACTION
        ↓
EXPLICIT ABCD RELATIONS
        ↓
DIVERGENCES / ADJUDICATION
        ↓
SYNTHESIS + PRISMA
        ↓
GOOGLE SHEET AUDIT VIEW
        ↓
MANUSCRIPT PACKAGE
```

The Engine **does not become a Clinical Decision Engine** and does not transform computational output into a final clinical recommendation.

---

## 2. Status legend

- **DONE — software**: implemented in the Engine and covered by the current software architecture.
- **PARTIAL — software**: architecture exists, but one or more runtime/UX/integration paths still need completion.
- **READY FOR EXECUTION**: software path exists, but the real scientific run has not yet occurred.
- **HUMAN / EXTERNAL**: cannot be truthfully completed by software alone.
- **FUTURE / NOT REQUIRED NOW**: useful later, but must not delay Article 1/2 writing unless the protocol explicitly requires it.

---

## 3. Non-negotiable architecture rules

1. The Engine is the execution authority; Google Sheets is an **audit/export mirror**, not a second engine.
2. Generated query is not executed query.
3. PILOT, STAGING and CALIBRATION are not FORMAL and contribute zero PRISMA counts.
4. FORMAL cannot start without persisted scientific authorization matching the exact strategy/configuration/freeze.
5. Human decisions cannot be fabricated, inferred from blanks or replaced by model output.
6. Machine assistance may suggest, classify or prefill candidates, but cannot become independent R2/adjudication.
7. Missing data are not negative evidence.
8. Provider failure, timeout, missing credential, truncation or unsupported route are never represented as zero results.
9. Co-occurrence of ABCD codes is not an explicit relation.
10. No global ABCD score, mean depth, maturity score or document ranking is valid for Article 1.
11. Protected full text is not redistributed without rights.
12. Published releases/tags remain immutable.
13. Scientific changes to ontology, coding, search or provenance semantics must be versioned and tested.

---

# PART A — EVERYTHING THE ENGINE MUST DO

## 4. Project, run and provenance identity

**Status: DONE — software baseline; must be present in every definitive run.**

The Engine must identify every scientifically relevant execution by:

- project/run/session identifier;
- software package version;
- exact Git SHA;
- operating environment and Python version;
- configuration digest and relevant config hashes;
- strategy version(s);
- codebook version;
- corpus build identifier;
- timestamps;
- input/output manifests;
- artifact hashes;
- reviewer/adjudication ledgers where applicable.

### Definition of done

A manuscript-facing table or count must be traceable back to the exact Engine SHA, configuration, corpus and human decision lineage that generated it.

---

## 5. Search-strategy registry

**Status: DONE — software architecture; Article 1 canonical versions still require real registration/execution evidence.**

The Engine must:

- store immutable search-strategy versions;
- render provider-specific expressions without silently changing concepts;
- separate generated expressions from actual submitted expressions;
- preserve filters, date limits and interface-specific transformations;
- version every scientifically meaningful modification;
- connect the registered strategy to the protocol/D-xxx decision set.

For Article 1, the canonical protocol candidates currently include B-NORM-PUBMED v0.4 and C-STRUCT-PUBMED v0.3 and their post-PRESS translations. Their definitive Engine records must reflect the exact expressions actually executed.

### Definition of done

The exact manuscript methods string can be reconstructed from the Engine registry and the exact execution record.

---

## 6. PILOT execution

**Status: READY FOR EXECUTION; real Article 1 PILOT remains scientific work.**

The Engine must execute PILOT runs as explicitly non-PRISMA and preserve:

- exact provider/database;
- exact expression submitted;
- timestamp;
- provider-reported total where available;
- number actually retrieved;
- pagination/limit/truncation state;
- raw snapshot/export and hash where applicable;
- sentinel recovery;
- route incompatibilities;
- representative structural off-target mechanisms/noise review;
- failure records;
- version/config digest.

The Article 1 D-104 gate must be represented faithfully: PILOT advances to PRESS only when syntax/fields are reproducible, expected sentinels are recovered or route incompatibility is pre-specified, and there is no recurrent correctable structural off-target mechanism that materially distorts scope.

### Engine must not

- declare recall adequate without actual sentinel evidence;
- invent a noise percentage after the fact;
- send PILOT counts to PRISMA;
- convert an execution failure into zero records.

---

## 7. PRESS support and external search review

**Status: HUMAN / EXTERNAL with software recording support required.**

The Engine must **record and enforce** PRESS status, but it does not self-certify PRESS.

It must preserve:

- strategy version submitted for PRESS;
- reviewer identity when legitimately available;
- date;
- comments/recommendations;
- disposition of every requested change;
- resulting version;
- provenance linking pre-PRESS and post-PRESS versions.

### Definition of done

A FORMAL strategy cannot be authorized merely because the software runs. The Engine must be able to show which PRESS-reviewed strategy version led to the frozen execution.

---

## 8. Scientific gates and freeze

**Status: DONE — guard architecture; HUMAN / EXTERNAL gate evidence remains pending.**

The Engine must persist gate states and block inappropriate transitions.

For Article 1 this includes, at minimum:

- GF-01 search-architecture alignment;
- GF-02 sentinel/noise PILOT adequacy;
- GF-03 external PRESS;
- GF-04 institutional-source register;
- GF-05 guideline-repository routes;
- GF-06 temporal rule;
- GF-07 real R2 + adjudicator / human-review prerequisite;
- GF-08 citation chasing rule;
- GF-09 legacy provenance separation;
- GF-10 explicit freeze authorization.

The freeze record must bind:

- strategy version;
- prerequisite gate evidence;
- human authorization where required;
- Git SHA;
- config digest;
- date/time;
- freeze identifier.

### Definition of done

No FORMAL run is created if the freeze evidence does not match the exact strategy/SHA/configuration being executed.

---

## 9. Indexed-database execution — Track A

**Status: DONE — provider execution framework; real Article 1 formal runs pending.**

The Engine must preserve attempt-level evidence for each supported provider.

Required fields include:

- provider/interface/database identity;
- exact expression;
- timestamp;
- reported total;
- retrieved total;
- pagination;
- truncation;
- errors/retries;
- raw snapshot/export;
- artifact hash;
- strategy/freeze/config identity.

Scopus and Web of Science may remain licensed/manual routes until authorized direct integration exists. The Engine must ingest their real execution evidence without pretending another provider is equivalent.

### Definition of done

Every record entering the formal corpus has a route back to a real retrieval attempt or declared formal institutional/manual route.

---

## 10. Official/institutional sources — Track B

**Status: DONE/PARTIAL depending route; formal execution evidence still required.**

The Engine must manage official organizations and food-guideline sources as a distinct sampling track, preserving:

- organization/source identity;
- route/navigation method;
- retrieval date;
- URL and resolved URL;
- document/version identity;
- stopping/version rule;
- download/extraction status;
- lawful artifact hash when retained;
- failure state;
- downstream inclusion/coding state.

A discovery list is not automatically a frozen sampling frame.

---

## 11. Guideline repositories — Track C

**Status: route registry exists; real operational executions/verification remain scientific records.**

The Engine must retain repository-specific provenance for routes such as:

- G-I-N;
- G-I-N BIGG;
- AWMF;
- Dutch Richtlijnendatabase;
- Minds;
- Ukraine Registry.

Repository route verification, issuer identity and document identity must remain separate concepts.

---

## 12. Supplementary discovery — Track D

**Status: DONE as governed optional capability.**

The Engine may support supplementary providers only when declared by protocol.

Technical availability never equals methodological authorization.

The current SciELO-labeled connector must remain explicitly described as Crossref DOI-prefix scoped (`10.1590`), not a comprehensive native SciELO free-text search.

---

## 13. Raw-record preservation, normalization and deduplication

**Status: DONE — software baseline.**

The Engine must:

- preserve source/provenance before normalization;
- normalize bibliographic identity audibly;
- deduplicate once at corpus level rather than separately by article;
- retain all source-route links after deduplication;
- preserve ambiguous identity/version cases for human review;
- create immutable corpus manifests and hashes.

A single document may later be associated with multiple articles without duplicate retrieval/storage.

### Definition of done

The corpus master can explain both why two retrieved records were merged and which original routes contributed to the surviving document identity.

---

## 14. Full-text discovery, lawful acquisition, parsing and OCR

**Status: DONE — software framework.**

The Engine must:

- resolve legal full-text routes;
- prioritize PMC/PMCID, OA locations and authorized sources;
- record paywall/unavailable states without circumvention;
- download where permitted;
- hash artifacts;
- extract native text where available;
- use OCR only when necessary/available;
- preserve OCR/extraction failures;
- keep full-text status auditable.

### Definition of done

No full-text decision is represented as based on content that the Engine/reviewer never actually had access to.

---

## 15. Human reviewer identity and role governance

**Status: PARTIAL — software guards exist; real people remain HUMAN / EXTERNAL.**

The Engine must support real, distinct identities for:

- R1;
- R2;
- adjudicator.

It must reject placeholder/blank/duplicated identities in FORMAL workflows where independence is required.

### Remaining software completion

Reviewer-slot and blindness semantics must be consistent across all persistent screening/full-text ledgers and every UI route, not only service-layer helpers and the Article 1 runtime.

### Human dependency

GF-07 cannot be closed until real R2/adjudicator identities and required calibration are present.

---

## 16. Screening calibration

**Status: DONE — software metrics/gates; real calibration pending GF-07 and PILOT corpus.**

The Engine must keep screening calibration distinct from ABCD calibration.

### Title/abstract

- decisions: INCLUDE / EXCLUDE / DOUBT;
- DOUBT operationally advances;
- original DOUBT is preserved;
- completeness must be 100%;
- binary ADVANCE vs EXCLUDE raw agreement candidate signal ≥80%;
- recurring rule contradiction blocks release;
- GF-07 must be resolved.

### Full text

- decisions: INCLUDE / EXCLUDE / DOUBT;
- DOUBT blocks closure;
- primary exclusion reason preserved;
- family classification evaluated when applicable;
- completeness 100%;
- eligibility raw agreement candidate signal ≥80%;
- family agreement candidate signal ≥80% when calculable;
- recurring conceptual contradiction blocks release.

Numeric agreement is a revision signal, not proof of validity.

---

## 17. Title/abstract screening

**Status: DONE/PARTIAL — core semantics exist; persistent route convergence remains to be finished.**

The Engine must:

- assign blinded records to R1/R2;
- preserve original independent decisions;
- treat INCLUDE and DOUBT as ADVANCE;
- exclude only when the exclusion decision is appropriately resolved;
- classify divergence mechanism;
- never overwrite original decisions with consensus/adjudication;
- expose unresolved decisions in audit views;
- keep calibration and FORMAL lineages separate.

---

## 18. Full-text screening

**Status: DONE/PARTIAL — core semantics exist; persistent route convergence remains to be finished.**

The Engine must:

- preserve R1/R2 independent decisions;
- retain DOUBT as a real unresolved state;
- require consensus/adjudication when needed;
- preserve exclusion reason taxonomy;
- preserve family classification;
- retain original decisions after final resolution;
- block downstream inclusion while unresolved.

Divergence mechanisms should include population, concept/ABCD, dietary-care context, document type, family, unit/version, insufficient information/content, ambiguous rule, application error and other specified.

---

## 19. ABCD-NutEV 34-component codebook

**Status: DONE — canonical software contract.**

The Engine must use the current 34-component scientific object:

- A1–A5;
- B1–B9;
- C1–C10;
- D1–D10.

It must preserve version identity and enforce:

- presence first;
- YES requires depth 1–3;
- NO requires depth 0;
- DOUBT requires unresolved/blank depth;
- missing is unassessed, not NO;
- N/A is not a valid presence state;
- final document closure requires exactly 34 unique resolved components.

The old broad four-domain heuristic remains compatibility/assistive only.

---

## 20. ABCD reviewer persistence and adjudication

**Status: DONE — Article 1 runtime P2.**

The Engine must persist the coding unit as, effectively:

`session × document × ABCD component × reviewer slot × codebook version × execution mode`

It must preserve:

- R1/R2 decisions;
- presence;
- depth;
- evidence passage/paraphrase;
- source locator/page/section;
- provenance/source of suggestion where relevant;
- revision history;
- adjudication;
- final state;
- STAGING/CALIBRATION/FORMAL isolation.

FORMAL coding requires the document to belong to the formal included corpus and the applicable human gate to be satisfied.

---

## 21. ABCD calibration — D-102

**Status: DONE — software metrics; real calibration requires human pairs.**

The Engine must calculate:

- expected unit count = 34 × number of calibration documents;
- completeness = binary-comparable paired decisions / expected units;
- presence agreement using all complete paired final observed states YES/NO/DOUBT;
- presence candidate signal ≥80%;
- exact depth agreement only when both reviewers say YES;
- exact depth candidate signal ≥70%;
- depth difference ≤1 candidate signal ≥90%;
- recurring conceptual contradiction as a blocking qualitative signal.

The Engine must not remove DOUBT from the presence denominator and must not treat blanks as disagreement, absence or zero.

---

## 22. Explicit ABCD relations — D-100 / D-103

**Status: DONE — Article 1 runtime P3.**

The Engine must maintain relations separately from co-occurrence.

Canonical relation unit:

`document × source_code × target_code × direction × relation_type`

It must preserve:

- source code;
- target code;
- direction;
- relation type;
- evidence passage/localizer;
- R1/R2 provenance;
- revisions;
- adjudication;
- explicit relation-review completion, including a valid reviewed-empty set.

Multiple evidence passages may support one relation without multiplying the relation count.

### Calibration

Use set-based descriptive comparison:

- R1 set size;
- R2 set size;
- intersection;
- union;
- descriptive Jaccard.

Do not construct artificial 34×34 negative agreement and do not impose an arbitrary Jaccard pass threshold.

---

## 23. Methodological/document characterization

**Status: DONE — separate descriptive layer.**

The Engine may store descriptive methodological/document fields separately from ABCD.

AGREE II/AGREE-REX are not mandatory Article 1 extraction steps unless separately authorized by protocol.

Methodological characterization must never be silently converted into an ABCD quality score.

---

## 24. Divergences, consensus and adjudication

**Status: DONE for Article 1 runtime; broader screening-ledger convergence still PARTIAL.**

The Engine must:

- expose R1/R2 disagreement;
- preserve the original submissions;
- record consensus/adjudication as additional records;
- preserve adjudicator identity when applicable;
- record rationale;
- identify whether a rule/codebook change resulted;
- never rewrite prior raw decisions to improve agreement retrospectively.

---

## 25. Article 1 synthesis

**Status: DONE — Article 1 runtime P4.**

The Engine must synthesize only FORMAL included/closed documents and keep these outputs distinct:

1. component presence;
2. component depth distribution;
3. co-occurrence;
4. explicit relations;
5. descriptive methodological characterization.

Denominators must be preserved by documentary family.

### Forbidden synthesis

- global ABCD score;
- mean depth across components;
- maturity/ranking of documents;
- claim that greater depth means better evidence;
- claim that more explicit relations means a better document;
- co-occurrence interpreted as integration.

---

## 26. PRISMA generation

**Status: DONE — software guard; final counts require real FORMAL execution.**

The Engine must generate PRISMA only from eligible FORMAL lineage.

Before final PRISMA, it must require:

- FORMAL execution mode;
- GF-10 freeze authorization;
- screening calibration release;
- no unresolved title/abstract decisions;
- no unresolved full-text decisions;
- formal search/corpus lineage.

PILOT/STAGING/CALIBRATION counts are always zero contributors to the formal PRISMA flow.

---

## 27. Google Sheet synchronization

**Status: PARTIAL — payload is implemented; direct Sheets transport remains to be completed.**

The Engine currently generates an `ENGINE_TO_SHEET` payload for controlled Article 1 views. The final architecture must include the actual transport/update command inside the Engine rather than relying on manual copying.

Canonical targets:

- `08_CODEBOOK_ABCD`;
- `10_EXTRACAO_ABCD`;
- `10A_RELACOES_ABCD`;
- `11_DIVERGENCIAS`;
- `13_SINTESE`.

### Required sync behavior

The sync command must:

1. authenticate through an explicit user-controlled Google integration/credential path;
2. validate spreadsheet identity;
3. read current target ranges before writing;
4. compare Engine payload to Sheet state;
5. preserve richer scientific codebook definitions in the Sheet;
6. update only fields/rows owned by the Engine contract;
7. never copy STAGING/CALIBRATION into FORMAL result views;
8. preserve historical/manual audit rows that are outside the Engine-owned namespace;
9. be idempotent;
10. record sync timestamp, Engine SHA, payload hash and outcome;
11. support dry-run/diff mode;
12. fail safely on schema mismatch rather than truncating data.

### Target CLI/UX

A canonical operation should exist, conceptually:

```bash
nutev article1 sync-sheet --project-root ... --spreadsheet ...
```

The exact command name may differ, but the function must live inside the Engine.

---

## 28. Manuscript-facing package

**Status: DONE/PARTIAL — manifest/export foundation exists; final package depends on real execution.**

For every manuscript-bound Article 1 snapshot, the Engine must be able to export:

- exact Git SHA/software version;
- codebook version;
- strategy/freeze/config identities;
- corpus manifest and hash;
- search attempt/provider evidence;
- screening counts/status;
- final ABCD 34/34 matrix;
- explicit-relations matrix;
- divergence/adjudication audit;
- synthesis by family;
- PRISMA-eligible counts;
- methodological characterization;
- manuscript table-ready CSV/JSON outputs;
- audit manifest with hashes.

The package should be sufficient to reconstruct every number used in the manuscript without retyping values by hand.

---

## 29. Dashboard / UX

**Status: DONE/PARTIAL.**

The Engine must offer a usable human workflow without forcing investigators to edit SQLite manually.

Required workspaces include:

- search strategy;
- gate/freeze status;
- runs/providers;
- corpus/deduplication;
- full text/OCR;
- title/abstract screening;
- full-text screening;
- Article 1 ABCD 34/34;
- relations;
- divergences/adjudication;
- synthesis/export;
- audit status.

### Remaining requirement

Reviewer blindness and reviewer-slot semantics must be consistently enforced in the actual persistent UI path, not just as a backend helper.

---

## 30. Automation (`nutev play`)

**Status: DONE for authorized computational chain; intentionally constrained.**

`nutev play` may automate only the computational stages that are scientifically authorized.

While formal gates remain incomplete, full automatic mode stays PILOT-only.

Automation must stop rather than infer:

- PRESS approval;
- freeze authorization;
- human reviewer identity;
- human inclusion/exclusion;
- adjudication;
- final clinical recommendation.

---

## 31. Failure semantics

**Status: DONE principle; must remain regression-tested.**

Every external failure must remain explicit.

Examples:

- credential missing;
- timeout;
- 403/429;
- provider unavailable;
- unsupported provider;
- partial pagination;
- truncation;
- download failure;
- OCR failure;
- malformed export;
- schema mismatch;
- reviewer incompleteness.

Failure is not zero evidence.

---

## 32. AI/LLM assistance boundary

**Status: DONE governance principle.**

AI may support:

- organization;
- candidate classification;
- evidence-location assistance;
- code suggestions;
- drafting;
- inconsistency detection;
- audit preparation.

AI may not be represented as:

- independent R2;
- adjudicator;
- PRESS reviewer;
- source of scientific evidence;
- final inclusion authority;
- final clinical recommendation authority.

Every machine-supported field that can affect scientific interpretation should preserve its machine/human provenance.

---

## 33. Security, privacy, copyright and data governance

**Status: DONE governance/CI baseline.**

The Engine must:

- keep secrets out of repository history;
- avoid identifiable clinical/patient data;
- not circumvent paywalls;
- not redistribute protected full texts in public releases;
- keep rights/provenance metadata;
- keep release artifacts free of private/protected local outputs;
- preserve upstream attribution/licensing.

---

## 34. Testing and scientific regression protection

**Status: DONE baseline; permanent requirement.**

CI must continue to cover:

- supported Python versions;
- Windows smoke;
- canonical test suite;
- coverage gate;
- Ruff/compile checks;
- critical type checking;
- CodeQL/security scan;
- dependency review;
- package/release-artifact validation.

Scientifically meaningful invariants need direct regression tests, especially:

- generated ≠ executed;
- PILOT ≠ FORMAL;
- freeze guard;
- missing ≠ absence;
- DOUBT semantics;
- 34/34 closure;
- STAGING/CALIBRATION/FORMAL isolation;
- co-occurrence ≠ relation;
- PRISMA firewall;
- Engine-to-Sheet schema safety.

---

## 35. Release and Zenodo

**Status: FUTURE / NOT REQUIRED NOW for Article writing; do not fabricate.**

A new public release should be created only when there is a stable scientific software object worth citing.

Before release:

- reconcile package/CITATION/Zenodo/changelog/version metadata;
- validate exact release-candidate SHA;
- keep tests/security/reproducibility green;
- publish a new unused tag;
- create GitHub Release;
- verify the actual Zenodo record/DOI after it exists.

A DOI must never be invented in advance.

---

# PART B — WHAT REMAINS BEFORE WE STOP BUILDING THE ENGINE

## 36. Remaining software work — minimal closure list

These are the items that should be completed before declaring the current Article 1 Engine architecture functionally closed:

### S1 — persistent screening convergence

**Status: PARTIAL**

Wire reviewer-slot, blindness and D-105/D-106/D-107 behavior through every persistent title/abstract and full-text ledger/UI route. Eliminate any remaining path where a reviewer can see the other reviewer's decision before permitted unblinding or where legacy MAYBE/UNCERTAIN semantics can bypass canonical DOUBT handling.

### S2 — real Engine → Google Sheets transport

**Status: PENDING SOFTWARE**

Implement the authenticated, schema-safe, idempotent `ENGINE_TO_SHEET` transport described in Section 27. The current JSON payload is not yet the complete transport layer.

### S3 — canonical Article 1 strategy import/registration workflow

**Status: PARTIAL / EXECUTION PREP**

Ensure the exact approved protocol strategy versions can be imported/registered from the methodological source of truth without manual retyping and are version-locked before PILOT/FORMAL execution.

### S4 — end-to-end Article 1 execution rehearsal

**Status: PENDING EXECUTION TEST**

Run a zero-risk development rehearsal with public/synthetic or explicitly PILOT inputs through:

strategy → PILOT run → corpus → screening calibration path → ABCD calibration path → relation calibration path → synthesis/export → Sheet dry-run.

The rehearsal must prove orchestration, not scientific validity, and must remain non-PRISMA.

### S5 — manuscript package finalization

**Status: PARTIAL**

Create one canonical export command/workspace that emits the complete Article 1 manuscript bundle and audit manifest from a selected frozen session.

---

## 37. Scientific/human work that software cannot close

These are not software bugs and must remain explicit:

1. execute the real PubMed PILOT for the current strategy versions;
2. inspect sentinel recovery and structural off-target mechanisms;
3. obtain external PRESS review;
4. incorporate PRESS changes and version the resulting strings;
5. translate/validate Scopus and Web of Science expressions;
6. execute licensed/manual PILOT routes where required;
7. designate real R2 and adjudicator;
8. execute title/abstract calibration;
9. execute full-text calibration;
10. execute ABCD calibration;
11. execute relation calibration as applicable;
12. close GF-01/GF-02/GF-03/GF-07;
13. authorize GF-10 freeze;
14. execute formal searches from zero;
15. complete human screening/extraction/adjudication;
16. generate final PRISMA and manuscript outputs from formal lineage.

The Engine must facilitate and record all of these stages but cannot truthfully invent their completion.

---

# PART C — STOP RULE FOR ENGINE DEVELOPMENT

## 38. “Engine complete enough” criterion

For the current PhD phase, stop expanding the Engine architecture when all five software closure items S1–S5 are complete and green in CI.

At that point:

- new feature ideas become backlog unless they block a protocol requirement;
- scientific execution continues inside the frozen architecture;
- manuscript writing becomes the primary activity;
- only defects that threaten scientific correctness, provenance, security or reproducibility interrupt writing.

This stop rule is intentional. The thesis objective is not to build software indefinitely.

---

# PART D — ARTICLE 1 AND ARTICLE 2 BOUNDARY

## 39. Article 1

The Engine directly supports the Article 1 methodological chain:

- evidence identification;
- source/document ecosystem mapping;
- human screening;
- ABCD 34/34 extraction;
- explicit relations;
- synthesis across documentary families;
- PRISMA/audit/manuscript outputs.

Article 1 writing can proceed in parallel with remaining execution, as long as Methods use prospective/actual tense correctly and Results do not report unexecuted formal findings.

---

## 40. Article 2

Article 2 should **reuse frozen Article 1 outputs and provenance**, but a new Article 2 software architecture is not required now.

The Engine may later support Article 2 by exporting structured evidence inputs such as:

- component-level evidence maps;
- operational examples;
- source-to-framework traceability;
- explicit relations;
- implementation patterns;
- candidate protocol elements for human synthesis.

However, the Engine must not automatically convert Article 1 frequencies/depths into clinical recommendations or a NutEV protocol score.

The clinical/protocol synthesis for Article 2 remains a separate scientific reasoning layer with explicit evidence justification and human authorship.

**Rule:** do not delay Article 1/2 writing to build speculative Article 2 software features.

---

# PART E — FINAL ACCEPTANCE CHECKLIST

## 41. Software acceptance

The Engine is feature-complete for the current Article 1 scope when:

- [x] single canonical execution engine exists;
- [x] immutable strategy/execution provenance exists;
- [x] PILOT vs FORMAL separation exists;
- [x] scientific gate/freeze guards exist;
- [x] corpus normalization/deduplication exists;
- [x] full-text/OCR provenance exists;
- [x] canonical ABCD 34/34 contract exists;
- [x] ABCD reviewer persistence/adjudication exists;
- [x] explicit relation ledger exists;
- [x] relation review completion and descriptive calibration exist;
- [x] Article 1 synthesis exists;
- [x] PRISMA firewall exists;
- [x] `ENGINE_TO_SHEET` payload exists;
- [x] Article 1 manifest/audit export foundation exists;
- [ ] all persistent screening ledgers/UI enforce canonical reviewer-slot/blinding semantics;
- [ ] actual authenticated Engine→Google Sheets transport exists;
- [ ] canonical Article 1 strategy import/registration workflow is demonstrated without retyping drift;
- [ ] end-to-end Article 1 non-PRISMA rehearsal passes;
- [ ] one-command/workspace manuscript bundle is finalized.

---

## 42. Scientific execution acceptance

The Article 1 review is ready to generate final manuscript results only when:

- [ ] real PILOT executed and audited;
- [ ] PRESS completed;
- [ ] Scopus/WoS route evidence completed as required;
- [ ] GF-01/GF-02/GF-03 closed;
- [ ] real R2/adjudicator established;
- [ ] GF-07 closed;
- [ ] screening calibration released;
- [ ] ABCD calibration released;
- [ ] GF-10 freeze authorized;
- [ ] formal searches executed from zero;
- [ ] formal corpus deduplicated/frozen;
- [ ] title/abstract screening resolved;
- [ ] full-text screening resolved;
- [ ] ABCD 34/34 resolved for every included document;
- [ ] explicit-relation review closed for every included document;
- [ ] divergences/adjudications resolved;
- [ ] synthesis snapshot created;
- [ ] PRISMA generated only from formal lineage;
- [ ] manuscript bundle frozen with SHA/config/codebook/corpus/reviewer provenance.

---

## 43. Final responsibility map

| Function | Engine | Human/external |
|---|---:|---:|
| Generate/version strategy | Yes | methodological approval |
| Execute supported PILOT/FORMAL provider calls | Yes | authorization/gate approval |
| Record manual/licensed route evidence | Yes | actual licensed execution |
| PRESS | records/enforces | external reviewer |
| Freeze guard | enforces | authorization |
| Deduplicate/normalize | Yes | ambiguous identity review |
| Full-text retrieval/OCR | Yes | access rights and content judgment |
| Screening workflow | Yes | R1/R2 decisions |
| Screening calibration metrics | Yes | interpretation/revision decision |
| ABCD structure/validation | Yes | component coding |
| ABCD calibration metrics | Yes | conceptual adjudication |
| Relations structure/metrics | Yes | relation identification/adjudication |
| Synthesis | Yes | scientific interpretation |
| PRISMA | Yes | only after scientific authorization |
| Google Sheet audit mirror | Yes, after transport completion | credential/access ownership |
| Manuscript tables/manifest | Yes | narrative interpretation/authorship |
| Clinical NutEV protocol | No automatic authority | Article 2 scientific synthesis |

---

## 44. Governing principle

The Engine is complete when it can **execute, block, preserve and export the protocol faithfully**. It is not complete because it can make more decisions than the protocol allows.

The desired endpoint is therefore:

```text
stable Engine
    +
real scientific execution
    +
human review
    ↓
auditable Article 1 results
    ↓
Article 1 manuscript
    ↓
evidence-informed Article 2 synthesis
```

Once the minimal software closure list is complete, the project should move its center of gravity from software construction to **Article 1 and Article 2 writing**.
