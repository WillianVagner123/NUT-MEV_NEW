# Current code hygiene inventory

Status: **active cleanup record for the pre-release development tree**.

The goal is to make the canonical NutEV runtime smaller and clearer **without deleting live compatibility behavior or provenance evidence blindly**.

## Already removed from the active tree

Historical Local Deep Research application/runtime surfaces are no longer present in the current working tree:

- `src/local_deep_research/**`;
- inherited legacy `tests/**`;
- LDR-specific console entry points;
- old frontend/Docker/cookiecutter tooling;
- historical runtime compatibility shims.

Git history remains intact.

## Removed in the PLAY hygiene cycle

- `docs/AUDIT_COMPLETE_PIPELINE_2026.md` — unreferenced, superseded point-in-time audit whose assertions no longer represented the canonical current state.

The content remains available through Git history.

## Do NOT delete yet

The following surfaces look historical but still have current runtime/test references:

- `src/nutev/pipelines/master_pipeline.py`;
- historical workstream concepts `busca1`, `busca2a`, `busca2b`, `a3`;
- querypack/domain modules consumed by the compatibility pipeline;
- tests that protect compatibility/offline behavior.

They are tracked for controlled retirement in #1015. Blind deletion now would trade repository neatness for broken runtime/tests and lost behavior.

## Canonical replacement direction

The target runtime is:

```text
registered/versioned global strategy
        ↓
provider execution + attempt ledger
        ↓
master corpus
        ↓
full-text resolution/download/OCR
        ↓
human-review queues
        ↓
extraction/codebook/quality/synthesis
```

`nutev play` is the one-command computational orchestrator for this path. Once PLAY integrates the remaining protocol tracks and downstream exports, compatibility modules can be retired incrementally.

## Candidate cleanup classes

Before the next release, inspect candidates in these classes:

1. **stale point-in-time audits** — delete from active docs only when no release record/normative doc depends on them;
2. **duplicate migration plans** — replace with current-state records or Git history references;
3. **compatibility CLI paths** — deprecate explicitly, migrate tests, then remove;
4. **orphan Python modules** — require zero import/reference hits plus passing canonical tests after deletion;
5. **unused configuration** — verify no runtime/fixture/document generator consumes it;
6. **generated/local outputs** — keep ignored and outside releases;
7. **third-party/inherited assets** — removal requires provenance/license review, not just import analysis.

## Deletion acceptance rule

A source/config file is safe to delete only when all are true:

- no supported runtime imports it;
- no canonical test relies on it except a test being deliberately migrated;
- no normative scientific path requires the behavior;
- a replacement exists or the behavior is explicitly retired;
- deletion does not erase required attribution/provenance;
- Python 3.12/3.13, Windows smoke, blocking lint/compile, build and release-artifact checks remain green.

## Release boundary

Repository size in Git history is not reduced by deleting current-tree files. Do **not** rewrite history merely to make the repository look smaller before Zenodo. The release artifact should instead contain a clean current snapshot and exclude protected/local/generated outputs.
