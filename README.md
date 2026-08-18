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

`RODAR_TUDO.cmd` remains the general one-command v1 reference-discovery path.

## PhD article runs — canonical A1–A4 governance

For thesis work, do **not** use an unscoped ranking as if it represented one article. Use the governed launcher and declare the article explicitly:

```powershell
.\RODAR_ARTIGO.cmd A1
.\RODAR_ARTIGO.cmd A2
.\RODAR_ARTIGO.cmd A3
.\RODAR_ARTIGO.cmd A4
```

Canonical article boundaries are versioned in `config/nutev_governance_manifest.json` and article-specific ranking profiles are versioned in `config/article_reference_profiles.json`.

- **A1** — recommendations and dietary direction in normative/structuring documents.
- **A2** — current dietary prescriptions/interventions + operational package + executability difficulties. Implementation, competencies/repertoires and context are explanatory dimensions, not the autonomous object.
- **A3** — sources supporting development of the NutEV Dietary Protocol; not an independent evidence-review engine.
- **A4** — sources supporting the conceptual clinical-decision framework. A4 is not CFD-I, CFD-8, a score, a flag engine or a computational clinical decision algorithm.

Every governed run receives a unique `run_id`, records the governance version/digest and preserves a governance snapshot, effective article profile and SHA-256 hashes for the exported ranking artifacts. Scientific inclusion/exclusion and clinical decisions remain human-only.

## Outputs

The primary general outputs are:

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/latest.json
```

Governed thesis runs are additionally preserved without cross-article overwrite:

```text
project_output_reference/reference_ranking/by_article/A1/latest.json
project_output_reference/reference_ranking/by_article/A2/latest.json
project_output_reference/reference_ranking/by_article/A3/latest.json
project_output_reference/reference_ranking/by_article/A4/latest.json

project_output_reference/reference_ranking/by_article/<ARTICLE>/runs/<RUN_ID>/
  TOP_REFERENCIAS.md
  reference_ranking.csv
  reference_ranking.jsonl
  nutev_governance_manifest.json
  effective_reference_mode.json
  run_manifest.json
```

The root `reference_ranking/latest.json` is a convenience pointer to the most recent ranking run. For thesis provenance, the article-specific `by_article/<ARTICLE>/latest.json` and immutable `runs/<RUN_ID>/` directory are the authoritative run outputs.

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

The ranker uses `config/keyword_taxonomy*.json` together with `config/reference_mode.json`. Governed article runs create an ephemeral effective profile from the canonical article configuration without mutating the base configuration.

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
config/nutev_governance_manifest.json
config/article_reference_profiles.json
```

Changing taxonomy or focus terms changes prioritization without creating a separate scientific-review workflow. Changes to canonical A1–A4 governance must be intentional, versioned and regression-tested.

## Run only the ranker

If collection outputs already exist, general ranking can be run with:

```bash
python tools/rank_references.py \
  --project-root ./project_output_reference \
  --config-dir ./config \
  --top-n 100
```

For a thesis article, use the governed ranker instead:

```bash
python tools/run_governed_rank_references.py \
  --article A2 \
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
- Article governance controls scope/provenance of discovery and ranking; it does not automate eligibility, synthesis conclusions or clinical decisions.

## Reproducibility and provenance

Raw provider/source identity is preserved through the ranking pipeline. Failures and unavailable sources must remain explicit rather than being converted into fabricated zero-result claims.

For governed article runs, each `runs/<RUN_ID>/run_manifest.json` records the exact article scope, governance context, effective profile and hashed artifacts used in that run.

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
