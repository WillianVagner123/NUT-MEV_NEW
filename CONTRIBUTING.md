# Contributing to NutEV Reference Engine

NutEV Reference Engine is intentionally focused on multi-source reference discovery, normalization, deduplication, ranking and export for Lifestyle Nutrition.

## Product principles

- Never fabricate provider data or hide provider failures.
- Preserve source/provider identity.
- Keep ranking deterministic for identical inputs and configuration.
- Treat ranking as reading priority, not as a clinical or scientific decision.
- Do not simulate licensed databases when access is unavailable.
- Keep public outputs limited to supported reference metadata and ranking fields.
- Keep changes small and testable.

## Development setup

```bash
python -m pip install -e ".[dev]"
```

Run the test suite:

```bash
PYTHONPATH=src python -m pytest -q nutev_tests
```

Compile and lint:

```bash
python -m compileall -q src tools nutev_tests
ruff check src tools nutev_tests --select F,E9
```

## Canonical product path

```text
RODAR_TUDO.cmd
  -> tools/run_everything_now.py
  -> tools/run_latin_sources.py
  -> tools/rank_references.py
```

## Pull requests

A PR should include:

- a clear rationale;
- the affected providers/configuration/output contract;
- tests or a clear explanation of any test that could not be run;
- documentation updates for user-visible changes;
- explicit reporting of provider/network limitations.

Do not commit secrets, private research data, protected full texts without redistribution rights, or generated local output directories.

See `README.md`, `AGENTS.md`, `docs/README.md`, `SECURITY.md` and `NOTICE.md`.
