# Rodar o NutEV Evidence Engine no PC

Este guia cobre apenas o runtime canônico atual. O antigo modo genérico `--workstreams` foi aposentado; a pesquisa científica usa estratégia global versionada e o orquestrador `nutev play`.

## 1. Pré-requisitos

- Git;
- Python **3.12 ou 3.13** (`>=3.12,<3.14`);
- navegador atualizado;
- Tesseract opcional, mas necessário para OCR de PDFs escaneados.

## 2. Instalação

### Windows PowerShell

```powershell
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git
cd NutEV-Evidence-Engine
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dashboard,platform,documents]"
```

### macOS/Linux

```bash
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git
cd NutEV-Evidence-Engine
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dashboard,platform,documents]"
```

Verificação local:

```bash
python scripts/check_local.py
```

## 3. Demo sintética

```bash
nutev demo-data --project-root ./project_output_demo
nutev dashboard --project-root ./project_output_demo --port 8501
```

A demo é sintética e **não é evidência científica**.

## 4. Projeto científico

```bash
nutev dashboard --project-root ./project_output_scientific --port 8501
```

No dashboard, abra **Search Strategy**, registre uma versão imutável e execute somente o estado científico autorizado.

Fluxo canônico:

```text
estratégia global versionada
        ↓
renderização por provider
        ↓
execução + ledger + snapshots
        ↓
corpus mestre
        ↓
normalização/deduplicação
        ↓
full text / OCR
        ↓
revisão humana
        ↓
extração / qualidade / síntese
```

## 5. PLAY — um comando

PILOT completo:

```bash
nutev play --project-root ./project_output_scientific
```

Teste apenas de busca + corpus:

```bash
nutev play --project-root ./project_output_scientific --metadata-only
```

Versão específica:

```bash
nutev play \
  --project-root ./project_output_scientific \
  --version-id STRATEGY_VERSION_ID \
  --breadth specific \
  --limit 10000 \
  --providers pubmed europepmc crossref openalex
```

O PLAY atual é deliberadamente **PILOT-only** para o caminho automático completo. Ele não cria decisões humanas de `INCLUDE`/`EXCLUDE`, não aprova PRESS, não autoriza FREEZE e não transforma um piloto em contagens formais do PRISMA.

Saída principal:

```text
project_output_scientific/
└── 12_play/
    ├── latest_summary.json
    └── play_<id>/
        ├── play_state.json
        ├── play_summary.json
        ├── play_summary.sha256
        ├── play_summary.md
        ├── search_providers.csv
        ├── fulltext_ledger.jsonl
        ├── download_manifest.jsonl
        ├── download_failures.jsonl
        └── extraction_manifest.jsonl
```

## 6. OCR

Teste no Windows:

```powershell
tesseract --version
```

O NutEV extrai texto nativo quando disponível e usa OCR quando necessário. Falha ou ausência de OCR deve permanecer registrada; não deve virar documento vazio ou evidência ausente.

## 7. Construtor de estratégia

```bash
nutev strategy --spec examples/picos.json --out project_output_scientific/07_logs/search_strategy.json
```

Esse comando **gera** expressões. Uma expressão gerada só pode ser descrita como executada quando existir tentativa correspondente no execution ledger.

## 8. Guias e fontes oficiais

```bash
nutev guides --project-root ./project_output_scientific --workers 4 --rate 1.0
```

Descoberta ao vivo não substitui o marco amostral/manifesto congelado de uma execução definitiva. Preserve data, fonte, URL, status, artefato e hash conforme o protocolo.

## 9. Variáveis locais

### Windows PowerShell

```powershell
$env:NCBI_EMAIL="seu-email@exemplo.com"
$env:NCBI_API_KEY="sua-chave-ncbi"
$env:CROSSREF_MAILTO="seu-email@exemplo.com"
$env:OPENALEX_MAILTO="seu-email@exemplo.com"
```

Nunca comite secrets. Falha de credencial, timeout ou rate limit não deve ser convertida em “zero resultados”.

## 10. Testes

```bash
PYTHONPATH=src python -m pytest -q nutev_tests
```

A CI canônica valida Python 3.12/3.13, Windows smoke, compileall/Ruff, mypy crítico, segurança, dependency review e artefatos de release.

## 11. Contrato científico

- `generated` ≠ `executed`;
- `execution_status` ≠ `scientific_readiness`;
- PILOT ≠ busca formal/PRISMA;
- software não inventa revisão PRESS, FREEZE ou decisão humana;
- texto integral só é recuperado por rotas legalmente acessíveis;
- `RecommendationCandidate` não é recomendação clínica final.

Ver [`ARTICLE1_SEARCH_EXECUTION_CONTRACT.md`](ARTICLE1_SEARCH_EXECUTION_CONTRACT.md), [`SCIENTIFIC_GOVERNANCE.md`](SCIENTIFIC_GOVERNANCE.md) e [`PLAY.md`](PLAY.md).
