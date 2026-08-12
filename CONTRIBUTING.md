# Contributing to NutEV/NutMEV

Thank you for your interest in contributing to **NutEV/NutMEV — Evidence Engine for Lifestyle Nutrition**.

NutEV/NutMEV is a scientific and methodological platform for identifying, normalizing, auditing, retrieving and reviewing evidence for the NutEV research program. The canonical runtime is `src/nutev/`.

The repository evolved from a historical Local Deep Research base. That inherited runtime is no longer part of the active source tree; required provenance is preserved in `LICENSE`, `NOTICE.md`, Git history and `docs/PROVENANCE_AND_LICENSE.md`.

## Project principles

1. **Scientific traceability first.** Every scientific claim about execution must be backed by recorded execution evidence.
2. **Generated is not executed.** Rendered queries are not execution evidence until a real attempt exists.
3. **Human review is required.** PRESS, FREEZE, screening/adjudication and final scientific decisions remain explicit human states where required.
4. **LLM is assistive only.** LLM output cannot approve protocol items or fabricate documentary support.
5. **One canonical search runtime.** Do not reintroduce independent `busca1/busca2a/busca2b/a3` search pipelines; use the registered global-search/PLAY architecture.
6. **Small PRs are safer.** Keep one intent per PR when practical.

## Canonical Article 1 workflow

```text
registered global strategy
        ↓
provider rendering + execution ledger
        ↓
master corpus + deduplication
        ↓
full text / OCR
        ↓
human screening / eligibility
        ↓
extraction / codebook / quality / synthesis
```

`nutev play` is the one-command computational orchestrator for the currently authorized PILOT path.

## Before you start

- Open/reference an issue for larger changes.
- Do not create a second search/corpus pipeline when an existing canonical layer can be extended.
- Preserve immutable scientific versions and execution provenance.
- Do not commit generated real outputs, secrets, local databases or protected full texts.
- Update tests and documentation when behavior changes.

## Development setup

```bash
python -m pip install -e ".[dashboard,platform,documents]"
```

Demo:

```bash
nutev demo-data --project-root ./project_output_demo
nutev dashboard --project-root ./project_output_demo --port 8501
```

PILOT PLAY on a project with a registered strategy:

```bash
nutev play --project-root ./project_output_scientific --metadata-only
```

Tests:

```bash
PYTHONPATH=src python -m pytest -q nutev_tests
```

## Pull request expectations

A good PR includes:

- clear title and rationale;
- one coherent concern;
- tests or a documented reason they were not run;
- documentation updates for user/scientific behavior;
- explicit notes about scientific/provenance impact.

Recommended scopes include `fix(cli)`, `feat(search)`, `feat(play)`, `feat(audit)`, `feat(ui)`, `docs`, `test`, `refactor` and `chore`.

## Safety rules

Do not commit:

- API keys, tokens, credentials or `.env` files;
- personal/patient/participant data;
- protected PDFs/full texts without redistribution rights;
- local research outputs/databases intended to stay private;
- fabricated execution evidence or generated queries labeled as executed.

## Scientific rules

When contributing to scientific/search/review modules:

- preserve strategy/run/provider identities;
- keep failure/truncation states visible;
- do not silently map technical failure to zero evidence;
- do not let machine output create `INCLUDE`, `EXCLUDE`, PRESS approval, FREEZE authorization or final clinical recommendations;
- preserve source/document/claim links where those layers are used;
- keep conflicts and uncertainty visible.

## Repository structure

See [`docs/REPOSITORY_STRUCTURE.md`](docs/REPOSITORY_STRUCTURE.md). Main active areas include:

```text
src/nutev/search/
src/nutev/pipelines/
src/nutev/acquire/
src/nutev/download/
src/nutev/extract/
src/nutev/review/
src/nutev/analysis/
src/nutev/export/
src/nutev/ui/
src/nutev/global_watch/
config/
docs/
nutev_tests/
```

## Documentation

Start with:

- `README.md`
- `AGENTS.md`
- `SECURITY.md`
- `docs/PLAY.md`
- `docs/REPOSITORY_STRUCTURE.md`
- `docs/SCIENTIFIC_GOVERNANCE.md`
- `docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md`
- `docs/REPRODUCIBILITY.md`
- `docs/CODE_HYGIENE_CURRENT.md`
- `docs/PROVENANCE_AND_LICENSE.md`

## Code of conduct

Be respectful and constructive. Make methodological assumptions explicit, prefer transparent limitations over overclaiming, and protect the scientific integrity of the project.
