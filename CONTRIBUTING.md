# Contributing to NutEV Reference Engine

Thank you for contributing to **NutEV Reference Engine**.

The supported v1 product is a multi-source reference discovery and ranking engine for Lifestyle Nutrition research. The canonical runtime is under `src/nutev/`, while the supported user path is centered on `RODAR_TUDO.cmd`, `tools/rank_references.py`, `config/reference_mode.json` and the NutEV taxonomy files.

The repository evolved from a historical Local Deep Research base. Required provenance is preserved in `LICENSE`, `NOTICE.md` and Git history.

## Product principles

1. **Do not fabricate provider data.** Missing credentials, errors, rate limits and interface changes must remain visible.
2. **Ranking is not inclusion/exclusion.** A score is reading/reference priority only.
3. **No clinical recommendation inference.** Ranking cannot become a treatment recommendation.
4. **Preserve source identity.** Provider/source provenance must survive normalization and ranking.
5. **Determinism matters.** Identical input/configuration should produce the same ranking order.
6. **Do not simulate Scopus or Web of Science.**
7. **Keep public v1 outputs clean.** Legacy PRISMA/FORMAL/screening control fields do not belong in the supported ranking exports.
8. **Small PRs are safer.** Keep one intent per PR when practical.

## Supported v1 flow

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT
```

Primary outputs:

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/latest.json
```

## Development setup

```bash
python -m pip install -e ".[documents,search,dev]"
```

Run tests:

```bash
PYTHONPATH=src python -m pytest -q nutev_tests
```

Run the supported Windows path:

```text
RODAR_TUDO.cmd
```

## Pull request expectations

A good PR includes:

- a clear title and rationale;
- one coherent concern;
- tests or a documented reason they were not run;
- documentation updates when user-visible behavior changes;
- explicit notes when ranking, provider behavior or public output contracts change.

## Safety rules

Do not commit:

- API keys, tokens, credentials or `.env` files;
- personal/patient/participant data;
- protected PDFs/full texts without redistribution rights;
- private research outputs/databases;
- fabricated provider results, identifiers, counts or source provenance.

## Legacy compatibility

Historical systematic/scoping-review, screening, PRISMA, PRESS, FREEZE and GF-gate modules/documents may remain for provenance or compatibility. They are not the supported v1 product workflow and should not be expanded unless a future product decision explicitly reintroduces that scope.

See:

- `README.md`
- `AGENTS.md`
- `docs/README.md`
- `docs/RELEASE_V1_AUDIT.md`
- `docs/legacy/README.md`
- `SECURITY.md`
- `NOTICE.md`

## Code of conduct

Be respectful and constructive. Prefer transparent limitations over overclaiming, preserve provenance, and keep changes inside the supported product scope unless an explicit product decision says otherwise.
