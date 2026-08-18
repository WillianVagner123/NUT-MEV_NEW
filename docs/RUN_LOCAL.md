# Run NutEV Reference Engine locally

This guide covers the supported NutEV Reference Engine v1.0.0 path.

## Requirements

- Git;
- Python **3.12 or 3.13** (`>=3.12,<3.14`);
- network access for live providers;
- Tesseract only when OCR of scanned documents is needed by optional document utilities.

## Windows PowerShell — general reference mode

```powershell
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git
cd NutEV-Evidence-Engine
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[documents,search]"
.\RODAR_TUDO.cmd
```

The supported general one-command flow is:

```text
multi-source collection
      ↓
native LILACS/BVS + SciELO
      ↓
technical deduplication
      ↓
NutEV taxonomy + focus-keyword ranking
      ↓
reference exports
```

## Windows PowerShell — thesis article mode

For A1–A4 thesis work, use the governed launcher and declare the target article explicitly:

```powershell
.\RODAR_ARTIGO.cmd A1
.\RODAR_ARTIGO.cmd A2
.\RODAR_ARTIGO.cmd A3
.\RODAR_ARTIGO.cmd A4
```

The launcher validates the canonical governance contract before ranking. It does not turn the Reference Engine into a scientific inclusion/exclusion or clinical decision engine.

Canonical boundaries:

- A1: recommendations and dietary direction in normative/structuring documents;
- A2: current dietary prescriptions/interventions + operational package + executability difficulties;
- A3: development of the NutEV Dietary Protocol, not an independent review engine;
- A4: conceptual clinical-decision framework, not CFD-I, CFD-8, score, flag engine or algorithm.

## Outputs

General convenience outputs:

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/latest.json
```

Governed article outputs are durable and separated by article:

```text
project_output_reference/reference_ranking/by_article/<ARTICLE>/latest.json
project_output_reference/reference_ranking/by_article/<ARTICLE>/runs/<RUN_ID>/
```

Each `runs/<RUN_ID>/` directory contains the Markdown/CSV/JSONL ranking, a snapshot of `nutev_governance_manifest.json`, the effective article-specific reference profile and `run_manifest.json`. Ranking artifacts are recorded with SHA-256 hashes.

The root `reference_ranking/latest.json` is only the most recent convenience pointer. Use `by_article/<ARTICLE>/latest.json` and the referenced immutable run directory for thesis provenance.

## Run only the ranker

If collection output already exists, general ranking can be run with:

```bash
python tools/rank_references.py \
  --project-root ./project_output_reference \
  --config-dir ./config \
  --top-n 100
```

For an article-specific thesis run:

```bash
python tools/run_governed_rank_references.py \
  --article A2 \
  --project-root ./project_output_reference \
  --config-dir ./config \
  --top-n 100
```

`--article` only accepts `A1`, `A2`, `A3` or `A4`; unscoped thesis runs fail closed.

## Provider credentials

Optional provider variables may include:

```powershell
$env:NCBI_EMAIL="seu-email@exemplo.com"
$env:NCBI_API_KEY="sua-chave-ncbi"
$env:CROSSREF_MAILTO="seu-email@exemplo.com"
$env:OPENALEX_MAILTO="seu-email@exemplo.com"
```

Never commit secrets. Provider failures, missing credentials, rate limits or interface changes must remain explicit and must not be converted into fabricated zero-result claims.

## Tests

```bash
PYTHONPATH=src python -m pytest -q nutev_tests
```

The canonical CI covers Python 3.12/3.13, Windows smoke, compile/Ruff, type checking, security, dependency review, CodeQL and release artifact validation.

## Product boundary

Ranking is a reading/reference-priority signal. It is not scientific inclusion/exclusion and is not a clinical recommendation. A1–A4 governance supplies scope and provenance to thesis discovery/ranking runs; final scientific interpretation remains human-only.

Historical systematic/scoping-review, screening and scientific-gate commands or documents may remain for compatibility/provenance. They are not the supported v1 path. See `README.md`, `RELEASE_V1_AUDIT.md` and `legacy/README.md`.
