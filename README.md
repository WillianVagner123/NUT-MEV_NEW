# NutEV Reference Engine

**Stable release: 1.0.0**

NutEV Reference Engine is a multi-source reference discovery and prioritization engine for Lifestyle Nutrition research. It searches configured bibliographic and institutional sources, normalizes and deduplicates records, matches them against the NutEV taxonomy and configurable focus keywords, then exports a ranked reading/reference queue.

The ranking is an information-retrieval aid. It is not a systematic/scoping-review workflow, does not produce scientific INCLUDE/EXCLUDE decisions, does not create clinical recommendations, and does not simulate Scopus or Web of Science.

## Supported v1 flow

```text
SEARCH
  ↓
NORMALIZE
  ↓
DEDUPLICATE
  ↓
RANK
  ↓
EXPORT
```

The default Windows launcher expands that flow into the implemented providers:

```text
multi-source collection
      ↓
native LILACS/BVS + SciELO
      ↓
technical deduplication
      ↓
NutEV taxonomy + focus keyword matching
      ↓
document/source/recency weighting
      ↓
TOP_REFERENCIAS.md + CSV + JSONL + latest.json
```

## Quick Start — Windows

Requires Python `>=3.12,<3.14`.

```powershell
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git
cd NutEV-Evidence-Engine
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[documents,search]"
.\RODAR_TUDO.cmd
```

`RODAR_TUDO.cmd` is the supported one-command v1 path.

## Outputs

The primary public outputs are:

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/latest.json
```

### Ranking tiers

- `A_TOP_REFERENCE` — highest-priority references to review first.
- `B_STRONG_REFERENCE` — strong references likely to complement the top set.
- `C_DISCOVERY` — lower relative priority within the discovered corpus.

These tiers indicate **reading priority only**. They are not scientific eligibility decisions.

## Sources

The collector uses the providers legitimately implemented and available in the repository, including:

- PubMed;
- Europe PMC;
- OpenAlex;
- Crossref;
- DOAJ;
- Semantic Scholar;
- configured official/institutional sources;
- native LILACS/BVS;
- native SciELO;
- optional configured web-search routes when credentials are available.

Scopus and Web of Science are not simulated. Their absence is not silently replaced by another provider.

## Ranking model

The ranker uses `config/keyword_taxonomy*.json` together with `config/reference_mode.json`.

Score components include:

- taxonomy-term matches in title, keywords/subjects and abstract/snippet;
- configurable focus-keyword matches;
- document-type signals such as guideline, consensus, statement, framework, systematic review and meta-analysis;
- provider/source weighting;
- strong identifiers such as DOI/PMID/PMCID;
- a light recency bonus.

Title matches carry more weight than abstract matches. Recency is intentionally a secondary signal and should not dominate topical relevance.

## Configuration

Main semantic configuration:

```text
config/keyword_taxonomy.json
config/keyword_taxonomy_supplement*.json
config/reference_mode.json
```

Changing taxonomy or focus terms changes prioritization without creating a separate scientific-review workflow.

## Run only the ranker

If collection outputs already exist:

```bash
python tools/rank_references.py \
  --project-root ./project_output_reference \
  --config-dir ./config \
  --top-n 100
```

## Limitations

- Provider availability, rate limits and credentials can affect coverage.
- Web interfaces such as BVS/LILACS and SciELO can change and require connector maintenance.
- Coverage is heterogeneous across providers, languages, regions and document types.
- Scopus and Web of Science are not simulated when licensed access is unavailable.
- The ranking is lexical/taxonomic and metadata-driven; it does not replace human judgment about whether a reference should be cited or used.
- A high score is not a clinical recommendation and is not proof of methodological quality.

## Reproducibility and provenance

Raw provider/source identity is preserved through the ranking pipeline. Failures and unavailable sources must remain explicit rather than being converted into fabricated zero-result claims.

Historical research-review modules and documents remain only as compatibility/provenance material. They are outside the supported v1 runtime; see `docs/legacy/README.md` and `docs/RELEASE_V1_AUDIT.md`.

## Citation

Release metadata is provided in `CITATION.cff` and `.zenodo.json`.

Until a real Zenodo archive DOI is issued and verified, no DOI is claimed by this repository.

Preferred software identity:

**NutEV Reference Engine: taxonomy-guided reference discovery and ranking for Lifestyle Nutrition. Version 1.0.0.**

## License

MIT. See `LICENSE` and `NOTICE.md` for licensing and provenance details.

![status](https://img.shields.io/badge/status-stable%201.0.0-blue)
![python](https://img.shields.io/badge/python-3.12%E2%80%933.13-blue)
![license](https://img.shields.io/badge/license-MIT-green)
