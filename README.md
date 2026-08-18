# NutEV Reference Engine — Lifestyle Nutrition

Motor de busca e priorização de referências para Nutrição do Estilo de Vida.

O objetivo operacional é simples: **buscar em múltiplas fontes, normalizar/deduplicar os registros e apontar quais arquivos/artigos/documentos merecem ser lidos primeiro** com base na taxonomia NutEV e em palavras-chave de foco.

O caminho padrão **não executa revisão sistemática ou de escopo**, não produz PRISMA, não faz PRESS, não usa FREEZE, não cria decisão automática de INCLUDE/EXCLUDE e não transforma ranking em recomendação clínica.

## Fluxo fechado

```text
coleta multi-fonte
      ↓
LILACS/BVS + SciELO nativo
      ↓
deduplicação técnica do ranking
      ↓
match com keyword_taxonomy*.json
      ↓
score por palavras-chave + taxonomia + tipo documental + fonte + recência
      ↓
TOP_REFERENCIAS.md + CSV + JSONL
```

O produto final é uma **fila priorizada de leitura/referência**, não um conjunto de estudos incluídos.

## Rodar no Windows

Depois de criar/ativar o ambiente virtual e instalar o projeto:

```powershell
.\RODAR_TUDO.cmd
```

O comando usa `project_output_reference` e gera principalmente:

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/latest.json
```

### Faixas do ranking

- `A_TOP_REFERENCE`: primeiras referências a revisar.
- `B_STRONG_REFERENCE`: referências fortes e prováveis complementos.
- `C_DISCOVERY`: descoberta de menor prioridade relativa.

Essas faixas são **prioridade de leitura**, não elegibilidade científica.

## Como o score funciona

O ranker usa os arquivos existentes `config/keyword_taxonomy*.json` e adiciona peso para:

- correspondência no título;
- correspondência em palavras-chave/assuntos;
- correspondência em resumo/snippet;
- número de grupos da taxonomia atingidos;
- palavras-chave de foco configuradas;
- termos documentais como `guideline`, `consensus`, `statement`, `framework`, `systematic review` e `meta-analysis`;
- fonte/provedor;
- identificadores fortes (DOI/PMID/PMCID);
- recência como bônus leve.

Os pesos de fonte e as palavras-chave de foco ficam em:

```text
config/reference_mode.json
```

## Taxonomia

A taxonomia principal e seus suplementos continuam sendo a base semântica do Engine:

```text
config/keyword_taxonomy.json
config/keyword_taxonomy_supplement*.json
```

Adicionar ou ajustar termos nesses arquivos altera a priorização sem exigir uma nova estrutura de revisão científica.

## Fontes

O coletor existente consulta as rotas automatizáveis disponíveis no projeto, incluindo PubMed, Europe PMC, OpenAlex, Crossref, DOAJ, Semantic Scholar e fontes oficiais configuradas. O fluxo padrão também executa LILACS/BVS e SciELO nativamente.

Scopus e Web of Science não são simulados.

## Instalação

Requer Python `>=3.12,<3.14`.

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

## Uso separado do ranker

Se a coleta já existir:

```bash
python tools/rank_references.py \
  --project-root ./project_output_reference \
  --config-dir ./config \
  --top-n 100
```

## Escopo do software

O NutEV Reference Engine é uma ferramenta de **descoberta, organização e priorização bibliográfica**. A decisão de usar uma referência em tese, artigo, aula, protocolo ou texto continua sendo humana.

![status](https://img.shields.io/badge/status-reference--mode-blue)
![python](https://img.shields.io/badge/python-3.12%E2%80%933.13-blue)
![license](https://img.shields.io/badge/license-MIT-green)
