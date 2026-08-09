# Scientific Governance — NutEV Evidence Engine

Status: **normative repository governance**.

This policy governs how NutEV/NutMEV produces, audits, represents, versions and preserves evidence-related software outputs. It is binding for the software and for anyone using its outputs.

It separates permanent rules from temporary repository state. Historical audit documents describe past states; they do not automatically override current code, configuration, tests or execution records.

## 1. Scientific objective

A scientifically relevant frozen version of NutEV Evidence Engine should be defensible as a reproducible research-software object: identifiable by exact code/version/SHA, connected to a declared scientific function, supported by configuration and execution provenance, explicit about human decisions and limitations, reproducible to the extent permitted by external services/data rights, and citable without ambiguity.

The objective is not to create releases or DOIs for their own sake.

## 2. Non-negotiable principles

1. **A `RecommendationCandidate` is not a final recommendation.** Computational outputs remain candidates pending human review.
2. **Generated is not executed.** No query, provider, count, source or navigation rule may be described as executed without attempt-level evidence for the exact run.
3. **Computational completion is not scientific readiness.** `execution_status` and `scientific_readiness` are distinct.
4. **Every scientific claim must be traceable.** Claims require source provenance and verifiable location/identifier appropriate to the source type.
5. **Conflicts cannot be hidden.** Conflicting evidence, source disagreements and reviewer disagreements must remain visible.
6. **AI/LLM does not decide approval.** Language models may assist with organization, extraction, coding support and drafting, but they are not independent evidence and do not replace scientific adjudication.
7. **Final scientific decisions require human review.** See `docs/AI_USE_AND_HUMAN_OVERSIGHT.md`.
8. **Demo data is not scientific evidence.** Synthetic/demo outputs exist only to exercise the pipeline.
9. **Protected documents are not redistributed without rights.** See `docs/COPYRIGHT_AND_FULL_TEXT_POLICY.md`.
10. **No personal or identifiable clinical data in the repository.** See `docs/DATA_GOVERNANCE.md`.
11. **Published releases/tags are immutable.** Never move, overwrite or reuse a published tag.
12. **Methodological changes are versioned.** Changes to methodology, scoring, ontology, rules or provenance semantics require explicit records in the relevant changelog/documentation.
13. **PASS means the analysis actually executed.** A green workflow created by bypassing or suppressing a failed analysis is not scientific/security evidence.
14. **Never fabricate identity or citation metadata.** DOI, ORCID, affiliation, authorship, funding, dates and study results require real evidence or human confirmation.

## 3. Source hierarchy

When determining software truth, use this order:

1. code at the exact SHA/ref being evaluated;
2. tests/workflows at the same SHA/ref;
3. configuration;
4. ledgers/manifests/artifacts from the run;
5. current normative documentation;
6. Git history;
7. historical audits.

For external publication/citation platforms, use current official documentation/schema and the actual public record. Internal project policy must not be presented as a universal platform rule.

## 4. Roles

- **Maintainers** — steward code, CI, release integrity and repository governance.
- **Human reviewers/adjudicators** — own screening, scientific inclusion/exclusion, RecommendationCandidate approval/rejection and adjudication.
- **Contributors** — propose code, source, methodology or documentation changes via PR/issue.
- **Research software agents/assistants** — may inspect, implement, test and document changes but must obey this governance and may not invent missing scientific facts or human approvals.

## 5. Operating modes

### Mode A — read-only audit

Use before a new release cycle, before a definitive scientific execution, or whenever repository state is uncertain.

Do not create/move release tags, fabricate metadata, erase history, bypass gates or merge a change with unresolved blockers.

Expected outputs include current-state inventory, blocker list, version matrix, software↔manuscript matrix, security/privacy status, copyright/provenance status, reproducibility status, metadata status and preliminary GO/NO-GO.

### Mode B — remediation

Perform fixes on a dedicated branch. Preserve previous releases. Prefer the smallest defensible change and regression tests for scientific invariants. Record methodological consequences. Do not turn red checks green by suppressing the underlying analysis.

### Mode C — release candidate

Freeze exact version, SHA, configuration, search strategies, dependency state, demonstrative outputs, documentation and metadata. Validate the **exact candidate SHA**.

### Mode D — publication

Only after GO: merge/review per repository policy, validate final default-branch state, create a new unused tag, publish the GitHub Release, allow preservation/deposit integration to create/update the external record, and then verify the real identifiers.

### Mode E — post-release

Record version, tag, SHA, date, release URL, real DOI(s) when available, final metadata, limitations and relation to the manuscript. Start subsequent development with a distinct version identity.

## 6. Version identity

At every release candidate, reconcile:

| Source | Observed | Expected | Status |
|---|---|---|---|
| package version |  |  |  |
| `pyproject.toml` version source |  |  |  |
| `CITATION.cff` |  |  |  |
| `.zenodo.json` |  |  |  |
| `CHANGELOG.md` |  |  |  |
| README/release docs |  |  |  |
| Git tag |  |  |  |
| GitHub Release |  |  |  |
| preservation record/DOI |  |  |  |

Development metadata may intentionally differ from the latest published release metadata when that distinction is explicit. Before a new public release, all metadata for the new object must be reconciled.

## 7. Scientific object boundary

NutEV Evidence Engine may support:

- search-strategy construction/documentation;
- traceable retrieval;
- normalization and deduplication;
- assisted screening/extraction;
- quality/risk coding when explicitly implemented;
- evidence matrices;
- provenance ledgers/manifests;
- audit/reproducibility exports;
- human adjudication workflows;
- manuscript-facing methodological outputs.

It must not be described as independently prescribing, diagnosing, validating final clinical recommendations, replacing peer review, eliminating human bias, or fully automating scientific judgment.

Preferred verbs include: supports, assists, records, organizes, audits, generates candidates, facilitates human review, and improves traceability.

## 8. Query and execution provenance

For definitive scientific use, preserve both generated strategy space and actual execution attempts.

Never infer `executed` from `generated`.

Minimum attempt-level evidence should include, where applicable:

- run identifier;
- strategy/configuration version;
- provider/source;
- exact expression or navigation rule;
- timestamp;
- execution status;
- rows returned and provider-reported total when available;
- pagination/limit/truncation rules;
- error, timeout, unsupported state or missing credential;
- raw snapshot and checksum where required;
- configuration digest;
- downstream human review state.

`docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md` is the normative implementation-specific contract for definitive Article 1 executions.

## 9. Article 1 search tracks

Do not collapse sources with different sampling mechanisms into one homogeneous search.

### Track A — indexed databases

Freeze exact expressions and retrieve with provider-specific provenance, counts, dates, snapshots/hashes and formal/pilot status.

### Track B — official/institutional/guideline sources

Record organization/source manifest, URL/resolved URL, retrieval date, status, local artifact/hash when lawful, and downstream human inclusion/coding.

### Track C — supplementary discovery

Use only when declared by the protocol. Technical provider availability does not automatically authorize manuscript inclusion.

The current SciELO connector is DOI-prefix/Crossref scoped (`10.1590`) and must not be represented as a comprehensive native SciELO free-text search.

## 10. Scientific readiness

Keep two distinct concepts:

- `execution_status`: whether the computational workflow completed, partially completed or failed;
- `scientific_readiness`: whether outputs passed required scientific and human gates.

Conceptual readiness states:

- `blocked`;
- `computationally_ready_for_human_review`;
- `manuscript_ready`.

`manuscript_ready` requires explicit human-review completion and manuscript gates, not merely successful providers or a completed pipeline.

## 11. Software ↔ manuscript traceability

For a manuscript-bound execution, maintain a matrix:

| Methodological claim | Implementation | File/module | Test | Ledger/output | Status |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

Verify that the manuscript does not claim functionality absent from the frozen software and that the software does not perform an undocumented scientifically meaningful transformation.

## 12. Reproducibility

For a candidate or definitive execution, record operating system/environment, Python version, package version, exact SHA, commands, test counts where available, measured coverage when used, warnings/limitations, date, configuration, output identifiers and hashes where relevant.

A zero-key demonstration should work without private credentials or protected content and should use only synthetic/public/redistributable inputs.

> Demonstration data are not scientific evidence.

## 13. CI, quality and supply-chain integrity

Classify failures by scientific and software impact. A blocker is any defect that can materially alter scientific results, provenance, release identity, security/privacy or reproducibility.

Coverage thresholds must be based on measured baselines, not invented targets. Type checking may expand incrementally. Syntax/compile checks should remain explicit. Security/dependency workflows are PASS only when the underlying action actually executes.

Critical workflow references should follow the repository's supply-chain policy, and automated dependency/Action update tooling should be used to prevent silent aging of immutable pins.

## 14. Security and privacy

Block publication when secrets or identifiable clinical/patient/participant data are present.

Inspect for keys, tokens, passwords, cookies, `.env`, certificates, private keys, authenticated URLs, unnecessary local paths, private databases/dumps and real clinical tables. Never repeat a discovered secret verbatim in an audit report.

## 15. Copyright, redistribution and provenance

Distinguish project code, permissively licensed third-party code, referencable scientific content and content without clear redistribution rights.

Open-source status of the software does not authorize redistribution of full-text papers, figures, images, datasets or other processed content. Preserve legally required attribution and never invent upstream provenance.

## 16. Human identity and authorship

Scientific authorship, creator order, affiliation and ORCID require deliberate human confirmation. Do not derive authorship order from Git commits. ORCID is included only when confirmed; its absence alone is not automatically a technical release failure.

Use `HUMAN INPUT REQUIRED` when identity metadata cannot be safely resolved.

## 17. Metadata and citation

Audit `CITATION.cff` and `.zenodo.json` against current official schemas/documentation when preparing a release. Verify title, creators/authors, version, date, license, repository, description, keywords, related identifiers, DOI and confirmed human metadata.

Do not add a DOI before the public record exists. Deposit metadata and citation metadata may use different formats while describing the same frozen object.

## 18. GO / NO-GO

A release gate should cover at minimum:

- VERSIONING;
- TESTS;
- REPRODUCIBILITY;
- SECURITY;
- PRIVACY;
- COPYRIGHT;
- PROVENANCE;
- METADATA;
- CITATION;
- SCIENTIFIC CONSISTENCY;
- DOCUMENTATION.

Recommended states:

- 🔴 **NOT READY FOR RELEASE**;
- 🟡 **TECHNICALLY READY / HUMAN OR EXTERNAL GATE PENDING**;
- 🟢 **READY FOR RELEASE**.

## 19. Scientific chain

Where applicable, the project should be able to reconstruct:

QUESTION → PROTOCOL → STRATEGY VERSION → ACTUAL EXECUTION → RAW RECORDS → NORMALIZATION → DEDUPLICATION → SCREENING → FULL TEXT → EXTRACTION → EVALUATION → ADJUDICATION → FINAL MATRIX → MANUSCRIPT OUTPUT.

If a stage is outside the software, say so explicitly.

## 20. Decision flow

```text
sources → search → extract → engine (claims + candidates)
        → audit (traceability, conflicts) → human review/adjudication
        → (only then) protocol/manuscript output
```

The engine may emit candidates and flag conflicts; only human-review/adjudication can promote a candidate toward a final scientific/clinical protocol item.

## 21. Change control

- methodology/rule/scoring/ontology/provenance changes: PR + methodology documentation/changelog + appropriate versioning;
- software changes: PR + relevant CI + `CHANGELOG.md` where user/scientific behavior changes;
- governance changes: PR referencing the affected governance principle;
- release changes: release checklist + exact candidate-SHA validation.

## 22. FAIR and red-team review

Before release, assess findability, accessibility, interoperability and reusability. Review the candidate from the perspectives of a peer reviewer, research software engineer, open-science reviewer, security reviewer and copyright reviewer.

## 23. Related normative documents

- `AGENTS.md`
- `docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md`
- `docs/AI_USE_AND_HUMAN_OVERSIGHT.md`
- `docs/DATA_GOVERNANCE.md`
- `docs/COPYRIGHT_AND_FULL_TEXT_POLICY.md`
- `docs/REPRODUCIBILITY.md`
- `docs/RELEASE_CHECKLIST.md`
- `docs/CHANGELOG_METODOLOGICO.md`
- `CHANGELOG.md`

## 24. Release principle

The DOI is not the objective. The defensible chain is:

**code → version/SHA → scientific function → configuration → actual execution → automated decisions → human decisions → limitations → reproduction → citation**.

A new release should exist only when there is a scientific software object worth freezing.
