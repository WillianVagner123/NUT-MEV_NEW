# NutEV Reference Engine

**Stable software identity: 1.0.0**

NutEV Reference Engine is a multi-source discovery, normalization, deduplication and ranking tool for Lifestyle Nutrition references. It combines bibliographic providers, configured official sources, the NutEV keyword taxonomy, focus terms, document-type signals, provider weights and a light recency bonus to produce a prioritized reading queue.

The score is an information-retrieval priority. It does not determine scientific eligibility, methodological quality or clinical recommendations. Licensed databases such as Scopus and Web of Science are not simulated when access is unavailable.

## Canonical flow

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT
```

On Windows the supported one-command path is:

```text
RODAR_TUDO.cmd
  -> run_everything_now.cmd
     -> tools/run_everything_now.py
  -> tools/run_latin_sources.py
  -> tools/rank_references.py
```

## Quick Start - Windows

Requires Python `>=3.12,<3.14`.

```powershell
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git
cd NutEV-Evidence-Engine
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
.\RODAR_TUDO.cmd
```

Alternatively, double-click `Iniciar-NutEV-Windows.bat` for first-run environment setup and execution.

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

Provider failures and missing credentials are explicit. A missing provider never becomes fabricated output.

## Configuration

Search configuration:

```text
config/reference_search.json
```

Ranking configuration:

```text
config/reference_mode.json
config/keyword_taxonomy.json
config/keyword_taxonomy_supplement*.json
```

Every `keyword_taxonomy*.json` file is loaded by the ranker.

## Ranking model

Ranking uses:

- taxonomy terms, with stronger title matches than abstract/snippet matches;
- configurable focus keywords;
- document-type signals;
- provider/source weights;
- DOI/PMID/PMCID presence;
- a light recency bonus that does not dominate topical relevance.

### Priority tiers

- `A_TOP_REFERENCE` - highest reading priority;
- `B_STRONG_REFERENCE` - strong complementary references;
- `C_DISCOVERY` - discovery set with lower relative priority.

These tiers are reading-priority labels only.

## Outputs

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/latest.json
```

## CLI

The packaged CLI is intentionally small:

```bash
nutev --version
nutev providers
```

Collection and ranking remain explicit repository tools so their configuration and output locations are visible.

## Development

```bash
python -m pip install -e ".[dev]"
PYTHONPATH=src python -m pytest -q nutev_tests
python -m compileall -q src tools nutev_tests
ruff check src tools nutev_tests --select F,E9
```

CI validates Python 3.12, Python 3.13, Windows smoke, type checking, security checks, dependency review, CodeQL and clean wheel/sdist installation.

## Limitations

- provider availability, rate limits and credentials affect coverage;
- public web interfaces can change without notice;
- provider coverage differs by language, geography and document type;
- ranking is metadata- and text-signal-driven and requires human judgment for actual use of a reference;
- licensed providers are reported as unavailable when they are not configured, rather than replaced or simulated.

## Documentation

Current documentation is indexed in `docs/README.md`. Software cleanup evidence is recorded in `docs/REFERENCE_ENGINE_CLEANUP_AUDIT.md`.

## Citation and release metadata

Citation metadata: `CITATION.cff`  
Archive metadata: `.zenodo.json`

Version `1.0.0` is archived on Zenodo as record `21998607`.

**DOI:** [10.5281/zenodo.21998607](https://doi.org/10.5281/zenodo.21998607)  
**Zenodo record:** [zenodo.org/records/21998607](https://zenodo.org/records/21998607)

The published Git tag `v1.0.0` remains immutable. Future software releases must receive their own archive record and version-specific DOI.

## License and provenance

MIT. See `LICENSE`, `NOTICE.md` and `docs/PROVENANCE_AND_LICENSE.md`.
