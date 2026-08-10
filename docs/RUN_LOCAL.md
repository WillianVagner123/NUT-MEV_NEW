# Rodar o NutEV Evidence Engine no PC

Este guia separa claramente três usos diferentes:

1. **demo sintética** — para testar instalação/interface sem chave e sem evidência real;
2. **piloto/compatibilidade** — pipeline genérico antigo, útil para testes especializados;
3. **execução científica canônica** — uma estratégia global versionada, executada em múltiplas fontes, formando um corpus mestre antes da triagem por artigo.

## 1. Pré-requisitos

- Git;
- Python **3.12 ou 3.13**;
- navegador atualizado.

O pacote exige Python `>=3.12,<3.14`.

## 2. Windows — instalação assistida

```powershell
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git
cd NutEV-Evidence-Engine
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_windows.ps1
```

Dashboard:

```powershell
.\scripts\run_dashboard_windows.ps1
```

API local em outro terminal:

```powershell
.\scripts\run_api_windows.ps1
```

## 3. Instalação manual

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dashboard,platform,documents]"
```

### macOS/Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dashboard,platform,documents]"
```

## 4. Demo sintética sem chave

```bash
nutev demo-data --project-root ./project_output_demo
nutev dashboard --project-root ./project_output_demo --port 8501
```

Abra `http://127.0.0.1:8501`.

API opcional:

```bash
nutev serve --project-root ./project_output_demo --host 127.0.0.1 --port 8000
```

A demo é sintética e **não é evidência científica**.

## 5. Verificar instalação

```bash
python scripts/check_local.py
```

No Windows, sem ativar o ambiente:

```powershell
.\.venv\Scripts\python.exe scripts\check_local.py
```

## 6. Execução científica canônica — uma busca global

A pesquisa formal **não deve ser representada como quatro buscas independentes por `workstream`**.

Fluxo canônico:

```text
UMA estratégia global
        ↓
versão FORMAL congelada
        ↓
renderização por base/provider
        ↓
execução real + ledger
        ↓
UM run / corpus mestre
        ↓
deduplicação
        ↓
triagem/classificação por artigo
        ↓
full text / extração / qualidade / revisão humana
```

### 6.1 Abra um projeto científico exclusivo

```bash
nutev dashboard --project-root ./project_output_scientific --port 8501
```

### 6.2 Abra **Search Strategy**

Preencha o **campo global único** com a estratégia científica aprovada. O sistema pode renderizar sintaxes diferentes para PubMed, Europe PMC, Crossref e OpenAlex, mas isso continua sendo uma única estratégia científica.

### 6.3 Salve uma versão no registro

Antes da execução formal:

- revise a estratégia;
- salve a versão imutável;
- use `FORMAL` somente após aprovação metodológica;
- preserve responsável, versão e timestamp;
- não trate a versão mostrada na tela como executada até existir tentativa real.

### 6.4 Execute a versão registrada

Use a área **Executar uma versão registrada**. O executor deve ler a versão congelada e registrar `run_id`, provider, expressão submetida, tentativa, timestamp, status, contagem, limites/paginação/truncamento e snapshots/hashes conforme o contrato.

### 6.5 Corpus mestre e deduplicação

Após a recuperação, normalize e deduplique o `run_id` executado. A deduplicação ocorre uma vez no corpus mestre. Depois disso, cada documento pode receber decisões diferentes por artigo sem ser pesquisado/armazenado novamente.

### 6.6 Continuação downstream

Depois do corpus mestre:

- screening por artigo;
- full-text assessment;
- extração;
- OCR quando necessário/disponível;
- evidence matrix;
- quality assessment;
- revisão/adjudicação humana.

Metadata-only não deve ser promovido silenciosamente a full text.

## 7. Construtor CLI de estratégia

Para gerar/auditar uma estratégia a partir de um spec:

```bash
nutev strategy --spec examples/picos.json --out project_output_scientific/07_logs/search_strategy.json
```

Esse comando **gera** expressões. Ele não comprova execução.

## 8. Tracks do Artigo 1

- **Track A:** bases indexadas/congeladas — expressões exatas, tentativas, contagens, paginação, snapshots e hashes;
- **Track B:** fontes oficiais/institucionais/guidelines — manifesto, regra de navegação, URLs finais, status de captura e hashes quando aplicável;
- **Track C:** descoberta suplementar somente se o protocolo a declarar.

O conector SciELO atual usa Crossref com prefixo DOI `10.1590`; não é uma busca nativa/completa do SciELO.

Contrato normativo: [`ARTICLE1_SEARCH_EXECUTION_CONTRACT.md`](ARTICLE1_SEARCH_EXECUTION_CONTRACT.md).

## 9. Guias/fontes oficiais

Quando o protocolo exigir o pipeline de guias:

```bash
nutev guides --project-root ./project_output_scientific --workers 4 --rate 1.0
```

Para execução definitiva, prefira um marco amostral/manifesto congelado. Descoberta ao vivo deve ser preservada como snapshot e explicitamente descrita no método quando utilizada.

## 10. Pipeline legado / compatibilidade

O comando abaixo continua disponível para testes, compatibilidade e pilotos especializados:

```bash
nutev --project-root ./project_output_legacy --workstreams busca1 busca2a busca2b a3 --web-enabled
```

Ele **não é o caminho recomendado para representar a execução científica canônica de uma busca global**.

## 11. Variáveis locais

Nunca coloque chaves no GitHub ou em outputs científicos.

### Windows PowerShell

```powershell
$env:NCBI_EMAIL="seu-email@exemplo.com"
$env:NCBI_API_KEY="sua-chave-ncbi"
$env:CROSSREF_MAILTO="seu-email@exemplo.com"
$env:OPENALEX_MAILTO="seu-email@exemplo.com"
```

### macOS/Linux

```bash
export NCBI_EMAIL="seu-email@exemplo.com"
export NCBI_API_KEY="sua-chave-ncbi"
export CROSSREF_MAILTO="seu-email@exemplo.com"
export OPENALEX_MAILTO="seu-email@exemplo.com"
```

Credenciais opcionais não devem transformar falha de provider em “zero resultados”.

## 12. Artefatos esperados

### `02_metadata`

Artefatos canônicos de claims/auditoria, incluindo:

- `NUTEV_EVIDENCE_CLAIMS.csv`;
- `NUTEV_CLAIM_EVALUATIONS.csv`;
- `NUTEV_CONFLICTS.csv`;
- `NUTEV_RECOMMENDATION_CANDIDATES.csv`.

### `06_tables`

Matrizes e relatórios analíticos derivados.

### `07_logs`

Entre outros:

- `run_events.jsonl`;
- `run_summary.json`;
- `search_job_snapshot.json`;
- `querypack_generated.json/.csv`;
- `provider_querypack_generated.json/.csv`;
- `query_execution_ledger.json/.csv`;
- `provider_performance.csv`;
- checkpoints.

### `10_curated`

Outputs curados e priorização operacional. `is_prioritized` não equivale a inclusão científica.

## 13. Testes

```bash
PYTHONPATH=src python -m pytest -q nutev_tests
```

A CI canônica também valida Python 3.12/3.13, cobertura, Windows smoke, mypy crítico, compileall, Ruff, CodeQL, security scan, dependency review e build/clean-install do wheel.

## 14. Estados de execução

`execution_status` descreve a execução computacional.

`scientific_readiness` é um gate separado. Um pipeline concluído pode estar apenas `computationally_ready_for_human_review`.

`manuscript_ready` não deve ser inferido sem os gates humanos/manuscrito explícitos.

## 15. Regra metodológica final

O sistema apoia busca, classificação, proveniência, curadoria e revisão. Ele não substitui revisão humana, avaliação metodológica ou decisão final do protocolo.

`RecommendationCandidate` é candidata computacional; não é recomendação clínica final.
