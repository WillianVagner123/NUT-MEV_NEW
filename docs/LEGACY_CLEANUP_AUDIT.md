# Legacy Cleanup Audit — final state

Status: **completed for the current working tree**.

This file is kept as a concise provenance/cleanup record. It no longer describes pending removal work.

## Current canonical tree

The supported NutEV runtime is:

- `src/nutev/**`;
- `config/**`;
- `nutev_tests/**`;
- current governance/methodology documentation;
- the `nutev` CLI, dashboard and API components.

## Removed inherited runtime

The inherited Local Deep Research (LDR) runtime and its old application stack are no longer present in the current working tree:

- `src/local_deep_research/**` — removed;
- legacy `tests/**` — removed;
- legacy LDR console entry points — removed;
- legacy frontend/Docker/tooling — removed;
- historical runtime compatibility shims — removed.

The old code remains recoverable from Git history. Do not restore it into the canonical NutEV runtime merely to preserve history.

## Provenance

The repository evolved from the open-source Local Deep Research project by LearningCircuit. Historical MIT attribution is preserved in `LICENSE`, `NOTICE.md` and Git history. The current `src/nutev/**` tree is the NutEV Evidence Engine implementation.

See `NOTICE.md` for the authoritative provenance boundary. Do not infer that every current line originated upstream.

## Remaining compatibility surface

Some NutEV modules still use historical names such as `busca1`, `busca2a`, `busca2b`, `a3` or the legacy `master_pipeline` orchestration. These are compatibility/downstream analysis surfaces, not authorization to execute multiple independent scientific searches for Article 1.

Removal of those names requires dependency/test analysis and should happen only when the canonical global-search + `nutev play` path fully replaces their remaining runtime use.

## Cleanup rule going forward

Delete or archive a file only after confirming that:

1. canonical runtime does not import it;
2. canonical tests do not require it;
3. current documentation does not rely on it as normative truth;
4. any useful scientific/provenance content has a canonical replacement;
5. the deletion is covered by tests/CI.

Historical audit reports may remain in Git history instead of the active documentation set when they contradict current code.
