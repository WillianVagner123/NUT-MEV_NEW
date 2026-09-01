# Quality Observatory + Scientific Workspace Death Test

The Quality Observatory is the system-quality layer of the NutEV Scientific Workspace v2. It makes operational failures, provenance problems and technical incompleteness visible without turning software signals into scientific judgments.

## Scope

`/quality.html` reports **system quality, not evidence quality**.

It may report:

- web engine and Article Workbench availability;
- Agent Context availability and age;
- scientific snapshot identity and source hashes;
- build commit identity;
- full-text retrieval status;
- extraction methods used during deepening;
- missing DOI, PMID or year;
- `unclassified` document form;
- documents without an operational domain;
- `unrouted` documents;
- provider operational states;
- canonical PRESS, GF-10, formal-search and PRISMA-event states.

It does **not** assess methodological quality, risk of bias, certainty, eligibility, inclusion/exclusion, evidence strength or clinical relevance.

## Runtime sources

The page is read-only and uses only existing safe surfaces:

- `/api/health`;
- `/api/articles/status`;
- `/api/radar`;
- `/agent-context/article1/SEARCH_STATE.json`;
- `/agent-context/article1/CONTEXT_MANIFEST.json`;
- `/agent-context/article1/ARTICLE_SUMMARIES.jsonl`;
- `/build-info.json`;
- the browser-side Scientific Snapshot builder.

No protected full text is loaded into the observatory and no scientific POST action is introduced.

## Interpretation guardrails

The observatory deliberately keeps the following distinctions visible:

- missing DOI or PMID != invalid document;
- missing operational domain != evidence gap;
- `unrouted` != excluded;
- provider failure/unavailability != absence of literature;
- retrieval/full-text status != eligibility;
- document count != evidence strength or certainty;
- machine profile != risk-of-bias assessment;
- snapshot != PRISMA;
- discovery/deepening != formal search.

The page reflects canonical states. It cannot approve PRESS, authorize GF-10, freeze a query, execute formal provider searches or emit PRISMA events.

## PRESS regression fixed in Phase 9

The dashboard previously interpreted PRESS with substring matching. The canonical state `NOT_YET_RECORDED_AS_PASS` contains the token `PASS`, so a substring test could display the gate as approved even though the Search Master kept it closed.

PRESS now passes only when the normalized canonical value is exactly `PASS`.

This behavior is protected both by UI regression tests and by the adversarial workspace audit.

## Executable death test

Run:

```bash
python tools/audit_scientific_workspace_v2.py
```

For compact machine-readable output:

```bash
python tools/audit_scientific_workspace_v2.py --compact
```

The audit fails closed if it detects regressions such as:

- PRESS being parsed by substring instead of exact equality;
- the canonical formal gate being promoted while PRESS/GF-10/freeze remain closed;
- C4 Social Context being promoted before PRESS approval;
- POST actions appearing on analytical read-only surfaces;
- hidden direct OpenAI/Anthropic endpoints in Ask NutEV;
- Bank rank/score or machine relevance leaking into the scientific snapshot;
- snapshot semantics being promoted to PRISMA;
- production corpus totals being hardcoded in analytical JavaScript;
- frontend functions attempting to authorize GF-10, approve PRESS, freeze a query or emit PRISMA.

The audit checks software/UI scientific semantics and system contracts. A passing death test is **not** evidence validation, PRESS review, risk-of-bias assessment, certainty assessment or PRISMA validation.

## CI enforcement

The GitHub Actions job `audit guardrail contract` runs the death test explicitly in addition to the existing fail-closed ranking contract. The full Python matrix also executes `nutev_tests/test_quality_observatory_ui.py` as part of the complete `nutev_tests` suite.
