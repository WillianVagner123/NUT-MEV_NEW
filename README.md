# NutEV Reference Engine

**Stable software identity: 1.0.0**  
**Zenodo DOI:** `10.5281/zenodo.21998607`

NutEV Reference Engine is a multi-source discovery, normalization, deduplication and ranking tool for Lifestyle Nutrition references. It combines bibliographic providers, configured official sources, the NutEV keyword taxonomy, focus terms, document-type signals, provider weights and a light recency bonus to produce a prioritized reading queue.

The score is an information-retrieval priority. It does **not** determine scientific eligibility, methodological quality or clinical recommendations. Licensed databases such as Scopus and Web of Science are not simulated when access is unavailable.

## Canonical flow

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT
```

On Windows the supported one-command path is:

```text
Iniciar-NutEV-Windows.bat
  -> RODAR_TUDO.cmd
     -> run_everything_now.cmd
        -> tools/run_everything_now.py
     -> tools/run_latin_sources.py
     -> tools/rank_references.py
```

For the complete Portuguese operating procedure, see [`docs/POP_USO_NUTEV_REFERENCE_ENGINE.md`](docs/POP_USO_NUTEV_REFERENCE_ENGINE.md).

## Quick start — Windows

Requires Python `>=3.12,<3.14`.

```bat
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git
cd NutEV-Evidence-Engine
Iniciar-NutEV-Windows.bat
```

The first run creates `.venv`, upgrades `pip`, installs the project in editable mode and starts collection/ranking automatically.

If the repository is already cloned, update it first:

```bat
cd %USERPROFILE%\NutEV-Evidence-Engine
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
Iniciar-NutEV-Windows.bat
```

If the repository was cloned elsewhere, `cd` to that directory instead. `git rev-parse HEAD` is optional for normal use but recommended when an execution must be auditable or cited.

## What a successful run looks like

The launcher executes three stages:

```text
[1/3] COLETA MULTI-FONTE
[2/3] LILACS/BVS + SCIELO NATIVO
[3/3] RANKING DE REFERENCIAS
```

A complete run ends with:

```text
Coleta geral: codigo 0
LILACS/BVS + SciELO: codigo 0
Ranking: codigo 0
SUCESSO: ranking de referencias gerado.
```

The operator's validated Windows run on 2026-08-18 completed with `8,702` ranking inputs, `8,702` unique records under the current identity rule, `115` taxonomy groups loaded and `top_n = 100`. Full observed details are recorded in [`docs/VALIDATED_WINDOWS_RUN_2026-08-18.md`](docs/VALIDATED_WINDOWS_RUN_2026-08-18.md).

## Collection profiles

The default profile is `operational`:

| Provider | Operational limit |
|---|---:|
| PubMed | 2,000 |
| Europe PMC | 3,000 |
| OpenAlex | 3,000 |
| Crossref | 1,000 |
| DOAJ | 1,000 |
| Semantic Scholar | 1,000 |

The configured deep limits are preserved for explicit opt-in. On Windows CMD:

```bat
set NUTEV_DEEP_COLLECTION=1
Iniciar-NutEV-Windows.bat
```

To return to the normal profile in the same CMD session:

```bat
set NUTEV_DEEP_COLLECTION=
```

The active profile and provider limits are printed before network collection begins.

## Sources

The canonical collector supports:

- PubMed;
- Europe PMC;
- OpenAlex;
- Crossref;
- DOAJ;
- Semantic Scholar;
- configured official/institutional web sources;
- native LILACS/BVS;
- native SciELO;
- Google Programmable Search, Brave and SerpAPI when credentials are configured.

Provider failures and missing credentials are explicit. A missing or blocked provider never becomes fabricated output.

LILACS/BVS and SciELO use public native interfaces. If those interfaces reject automated access with HTTP `401`/`403`, the provider is recorded as `unavailable` and the pipeline can continue with available sources.

Scopus and Web of Science are reported as unavailable when licensed access is not configured; they are never simulated.

## Optional credentials and contact metadata

`.env.example` documents supported variable names, but the current runtime does **not** automatically load a `.env` file. Set variables in the shell before running.

CMD examples:

```bat
set NCBI_EMAIL=you@example.com
set NCBI_API_KEY=...
set CROSSREF_MAILTO=you@example.com
set OPENALEX_MAILTO=you@example.com
set S2_API_KEY=...
```

Optional web-search providers:

```bat
set GOOGLE_API_KEY=...
set GOOGLE_CSE_ID=...
set BRAVE_API_KEY=...
set SERPAPI_API_KEY=...
```

The absence of `NCBI_EMAIL`/`ENTREZ_EMAIL` does not stop PubMed collection; the client uses a conservative rate limit when no email/API key is configured.

Never commit real secrets.

## Resume behavior

PubMed checkpoints are saved under the output/log tree and collection is configured to resume when possible. If a run is interrupted, rerun:

```bat
Iniciar-NutEV-Windows.bat
```

Do not delete `project_output_reference` or checkpoints by default. Exit code `130` normally indicates a user interruption such as `Ctrl+C`.

## Configuration

Search configuration:

```text
config/reference_search.json
```

It contains canonical queries plus `provider_limits` and `deep_provider_limits`.

Ranking configuration:

```text
config/reference_mode.json
config/keyword_taxonomy.json
config/keyword_taxonomy_supplement*.json
```

Every `keyword_taxonomy*.json` file is loaded by the ranker.

The current focus keywords are:

```text
lifestyle medicine
lifestyle nutrition
nutrition care
dietary pattern
food-based dietary guideline
behavior change
food literacy
culinary
shared decision making
social determinants of health
```

## Ranking model

Ranking uses:

- taxonomy terms, with stronger title matches than abstract/snippet matches;
- configurable focus keywords;
- document-type signals;
- provider/source weights;
- DOI/PMID/PMCID presence;
- a light recency bonus that does not dominate topical relevance.

Provider weights are configured in `config/reference_mode.json`.

### Priority tiers

- `A_TOP_REFERENCE` — highest reading priority;
- `B_STRONG_REFERENCE` — strong complementary references;
- `C_DISCOVERY` — discovery set with lower relative priority.

These tiers are reading-priority labels only.

### Deduplication boundary

The current deduplication/identity logic is identifier- and metadata-driven. Parallel publications, closely related versions or semantically equivalent records with different persistent identifiers can remain as separate ranked items. Human inspection remains required before final scientific use.

`records_unique == records_input` means no duplicate was removed by the active identity rule in that run; it does not prove that every record is semantically distinct.

## Outputs

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/latest.json
```

- `TOP_REFERENCIAS.md` — human-readable TOP N queue with score, priority tier, source, year, identifiers, taxonomy matches and focus terms.
- `reference_ranking.csv` — tabular export for spreadsheet/statistical inspection.
- `reference_ranking.jsonl` — structured one-record-per-line export for automation.
- `latest.json` — run summary with status, source files, counts, loaded taxonomy groups, focus keywords, TOP N and output paths.

## Common troubleshooting

### `Nenhum master de coleta encontrado`

The collection stage did not finalize a usable master. Rerun the launcher and allow stage `[1/3]` to finish. A previous `Ctrl+C` commonly produces exit code `130`.

### BVS/SciELO HTTP 401 or 403

The public native interface refused automated access. Current `main` records that provider as unavailable instead of treating the access denial as a fatal pipeline failure.

### VS Code prints `StorageMainService`, `Unknown channel` or Node `DeprecationWarning`

Those messages can appear after Windows opens `TOP_REFERENCIAS.md` in VS Code. They are VS Code messages, not NutEV Reference Engine runtime failures. Check the NutEV exit-code summary printed before the file opens.

### `Deseja finalizar o arquivo em lotes (S/N)?`

This is a Windows CMD prompt normally triggered by `Ctrl+C` during a batch file. If `SUCESSO: ranking de referencias gerado.` was already printed, the ranking output has already been produced.

## CLI

The packaged CLI is intentionally small:

```bash
nutev --version
nutev providers
```

Collection and ranking remain explicit repository tools so configuration and output locations are visible.

## Development and validation

```bash
python -m pip install -e ".[dev]"
PYTHONPATH=src python -m pytest -q nutev_tests
python -m compileall -q src tools nutev_tests
ruff check src tools nutev_tests --select F,E9
```

CI validates Python 3.12, Python 3.13, Windows smoke, type checking, security checks, dependency review, CodeQL and clean wheel/sdist installation.

## Limitations

- provider availability, rate limits and credentials affect coverage;
- public web interfaces can change or block automated access;
- provider coverage differs by language, geography and document type;
- ranking is metadata- and text-signal-driven and requires human judgment;
- identifier-based deduplication does not guarantee semantic uniqueness;
- optional credentials increase provider availability but do not convert ranking into scientific screening;
- licensed providers are reported as unavailable rather than replaced or simulated.

## Documentation

- [`docs/POP_USO_NUTEV_REFERENCE_ENGINE.md`](docs/POP_USO_NUTEV_REFERENCE_ENGINE.md) — Portuguese Standard Operating Procedure for day-to-day use.
- [`docs/VALIDATED_WINDOWS_RUN_2026-08-18.md`](docs/VALIDATED_WINDOWS_RUN_2026-08-18.md) — real successful Windows run evidence.
- [`docs/SEARCH_PROVIDERS.md`](docs/SEARCH_PROVIDERS.md) — provider access, limits and failure behavior.
- [`docs/PROVENANCE_AND_LICENSE.md`](docs/PROVENANCE_AND_LICENSE.md) — provenance and licensing boundary.
- [`docs/RELEASE_V1_0_0.md`](docs/RELEASE_V1_0_0.md) — v1.0.0 stable release notes.
- [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md) — release validation gates.
- [`docs/ZENODO_SETUP.md`](docs/ZENODO_SETUP.md) — archive/DOI publication record.
- [`docs/REFERENCE_ENGINE_CLEANUP_AUDIT.md`](docs/REFERENCE_ENGINE_CLEANUP_AUDIT.md) — cleanup scope and evidence.

## Citation and release metadata

Citation metadata: `CITATION.cff`  
Archive metadata: `.zenodo.json`

Version `1.0.0` is archived on Zenodo as record `21998607`.

**DOI:** [10.5281/zenodo.21998607](https://doi.org/10.5281/zenodo.21998607)  
**Zenodo record:** [zenodo.org/records/21998607](https://zenodo.org/records/21998607)

The published Git tag `v1.0.0` remains immutable. Current `main` may contain post-release fixes and documentation; those changes do not rewrite the archived `v1.0.0` snapshot.

## License and provenance

MIT. See `LICENSE`, `NOTICE.md` and `docs/PROVENANCE_AND_LICENSE.md`.
