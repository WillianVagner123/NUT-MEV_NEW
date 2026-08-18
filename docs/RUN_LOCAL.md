# Run NutEV Reference Engine locally

This guide covers the supported NutEV Reference Engine v1.0.0 path.

## Requirements

- Git;
- Python **3.12 or 3.13** (`>=3.12,<3.14`);
- network access for live providers;
- Tesseract only when OCR of scanned documents is needed by optional document utilities.

## Windows PowerShell

```powershell
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git
cd NutEV-Evidence-Engine
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[documents,search]"
.\RODAR_TUDO.cmd
```

The supported one-command flow is:

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

## Outputs

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/latest.json
```

## Run only the ranker

If collection output already exists:

```bash
python tools/rank_references.py \
  --project-root ./project_output_reference \
  --config-dir ./config \
  --top-n 100
```

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

Ranking is a reading/reference-priority signal. It is not scientific inclusion/exclusion and is not a clinical recommendation.

Historical systematic/scoping-review, screening and scientific-gate commands or documents may remain for compatibility/provenance. They are not the supported v1 path. See `README.md`, `RELEASE_V1_AUDIT.md` and `legacy/README.md`.
