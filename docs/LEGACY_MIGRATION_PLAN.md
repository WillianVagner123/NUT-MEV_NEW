# Legacy Migration Record — Local Deep Research → NutEV

Status: **migration completed for the current working tree**.

This document replaces the former pending migration plan. The detailed historical sequence remains available in Git history; the active repository should describe the state that actually exists now.

## Result

The inherited Local Deep Research (LDR) application runtime has been removed from the current tree while preserving provenance and history.

Completed outcomes:

- NutEV version source is independent under `src/nutev/__version__.py`;
- the canonical console entry point is `nutev`;
- `src/nutev/**` does not depend on `src/local_deep_research/**`;
- the inherited `src/local_deep_research/**` tree is removed;
- the legacy `tests/**` tree is removed;
- old LDR frontend/Docker/tooling is removed;
- legacy `ldr`, `ldr-web` and `ldr-mcp` entry points are removed;
- canonical tests live under `nutev_tests/**`;
- canonical packaging contains no `legacy` optional dependency group;
- provenance is retained in `LICENSE`, `NOTICE.md` and Git history.

## What remains intentionally

Historical terminology can still occur in documentation, Git history and compatibility/downstream NutEV modules. Names such as `busca1`, `busca2a`, `busca2b`, `a3` and `master_pipeline` do not represent the canonical Article 1 search architecture.

The canonical scientific path is the versioned global strategy → actual execution → master corpus → human review workflow. `nutev play` is being introduced as the one-command computational orchestrator for that path.

## Licensing/provenance boundary

The repository was derived historically from LearningCircuit's Local Deep Research under the MIT License. Do not remove upstream copyright/license notices from inherited/substantial upstream material without a provenance review. Conversely, do not describe all current NutEV source code as authored by LearningCircuit merely because the historical base was MIT-licensed.

`NOTICE.md` is the authoritative active provenance note.

## No history rewrite

Do not use `git filter-repo`, force-push or tag rewriting merely to erase the inherited project. Git history is part of the provenance record.

## Future cleanup

Further removal should target only demonstrably unused compatibility modules, stale audit documents or redundant configuration. Each deletion must be supported by import/reference analysis and the canonical test suite.
