# Arquitetura do NutEV Reference Engine

Este documento descreve o comportamento implementado atualmente no repositório. Ele é deliberadamente técnico e deve ser atualizado quando o contrato de coleta, deduplicação, scoring ou exportação mudar.

## 1. Fluxo

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT
```

No Windows:

```text
Iniciar-NutEV-Windows.bat
  -> RODAR_TUDO.cmd
     -> run_everything_now.cmd
        -> tools/run_everything_now.py
     -> tools/run_latin_sources.py
     -> tools/rank_references.py
```

## 2. Componentes principais

### Coleta geral

`tools/run_everything_now.py`

Responsabilidades:

- carregar `config/reference_search.json`;
- selecionar perfil `operational` ou `deep`;
- executar PubMed e demais providers suportados;
- preservar identidade do provider;
- registrar falhas/indisponibilidades explicitamente;
- normalizar e deduplicar registros da coleta geral;
- salvar outputs por provider e um `master_records.jsonl`;
- atualizar o estado de execução usado pelo ranker.

### Fontes latino-americanas nativas

`tools/run_latin_sources.py`

Responsabilidades:

- tentar LILACS/BVS e SciELO pelas interfaces públicas nativas configuradas;
- preservar `source_provider`;
- registrar `401`/`403` como indisponibilidade de acesso automatizado;
- nunca substituir a fonte por outra silenciosamente;
- gerar `latin_native_records.jsonl` e resumo da tentativa.

### Ranking

`tools/rank_references.py`

Responsabilidades:

- localizar os masters mais recentes registrados nos estados de coleta;
- carregar todas as taxonomias `config/keyword_taxonomy*.json`;
- carregar `config/reference_mode.json`;
- aplicar deduplicação de entrada do ranking;
- calcular score;
- ordenar registros;
- atribuir faixa A/B/C;
- exportar JSONL, CSV, Markdown e resumo `latest.json`.

## 3. Configuração de busca

Arquivo:

```text
config/reference_search.json
```

Contém:

- query específica para PubMed;
- query genérica para APIs bibliográficas;
- query web;
- `provider_limits` para o perfil operacional;
- `deep_provider_limits` para o perfil profundo.

O perfil profundo só é ativado quando:

```text
NUTEV_DEEP_COLLECTION=1
```

## 4. Configuração do ranking

Arquivo:

```text
config/reference_mode.json
```

Valores atuais:

- `top_n = 100`;
- focus keywords configuradas;
- pesos por provider.

Pesos atuais por provider:

| Token de provider | Peso |
|---|---:|
| `official` | 8 |
| `pubmed` | 6 |
| `lilacs` | 5 |
| `bvs` | 5 |
| `scielo` | 4 |
| `europepmc` | 4 |
| `openalex` | 3 |
| `crossref` | 2 |
| `doaj` | 2 |
| `semantic` | 2 |

O ranker normaliza o nome do provider e usa o maior peso cujo token apareça no nome normalizado.

## 5. Carregamento da taxonomia

O ranker carrega, em ordem de nome de arquivo:

```text
config/keyword_taxonomy*.json
```

A taxonomia é achatada em grupos nomeados pelo caminho das chaves JSON.

Termos são:

- convertidos para minúsculas;
- normalizados sem acentos;
- reduzidos a caracteres alfanuméricos e espaços;
- ignorados quando têm menos de três caracteres.

Os grupos e termos correspondentes são preservados nos outputs para auditoria.

## 6. Regra de identidade e deduplicação

A identidade de cada registro é determinada na seguinte ordem:

```text
DOI -> PMID -> URL -> título normalizado
```

Se dois registros têm a mesma identidade, permanece a versão com maior quantidade de texto descritivo entre `abstract`, `summary` e `snippet`.

Consequências:

- registros com o mesmo DOI tendem a ser unidos;
- registros com o mesmo PMID tendem a ser unidos quando não há DOI;
- registros com a mesma URL tendem a ser unidos quando não há DOI/PMID;
- título só é usado como fallback quando os identificadores anteriores não estão presentes;
- publicações semanticamente equivalentes com identificadores diferentes podem permanecer separadas.

Esta regra não deve ser descrita como deduplicação semântica completa.

## 7. Scoring atual

O score é aditivo.

### 7.1 Termos da taxonomia

Para cada termo correspondente:

| Campo | Pontos |
|---|---:|
| título | +6 |
| keywords/subjects | +4 |
| abstract/summary/snippet | +2 |

A soma de um mesmo termo é limitada a `8` pontos.

O ranker considera no máximo quatro termos correspondentes por grupo de taxonomia. Quando um grupo tem pelo menos um hit, o grupo recebe ainda `+3` pontos.

### 7.2 Focus keywords

Para cada palavra-chave foco:

| Campo | Pontos |
|---|---:|
| título | +10 |
| keywords/subjects | +6 |
| abstract/summary/snippet | +4 |

### 7.3 Tipo documental no título

Pesos implementados:

| Expressão normalizada | Pontos |
|---|---:|
| `clinical practice guideline` | +12 |
| `practice guideline` | +11 |
| `guideline` | +10 |
| `consensus statement` | +9 |
| `consensus` | +7 |
| `position statement` | +8 |
| `scientific statement` | +8 |
| `standards of care` | +8 |
| `systematic review` | +7 |
| `meta analysis` | +7 |
| `framework` | +5 |
| `recommendation` | +4 |

Como as expressões são testadas separadamente, um título pode receber mais de um desses sinais quando contém expressões sobrepostas.

### 7.4 Provider

É adicionado o bônus definido em `provider_weights`.

### 7.5 Identificadores

Se o registro tiver pelo menos um entre DOI, PMID ou PMCID:

```text
+2 pontos
```

### 7.6 Recência

Usando o ano encontrado nos campos de data/ano:

- idade de até 5 anos: `+4`;
- idade de 6 a 10 anos: `+2`;
- mais de 10 anos: sem bônus de recência.

O ano válido é limitado ao intervalo de 1900 até o ano atual + 1.

### 7.7 Penalidades

- sem título: `-25`;
- sem abstract/summary/snippet: `-1`.

## 8. Ordenação

Após o scoring, os registros são ordenados por:

1. score decrescente;
2. ano decrescente;
3. título em ordem lexical.

## 9. Faixas de prioridade

A faixa é definida pela posição, e não por um ponto de corte absoluto do score:

- posições 1–20: `A_TOP_REFERENCE`;
- posições 21–100: `B_STRONG_REFERENCE`;
- demais posições: `C_DISCOVERY`.

Logo, uma faixa A ou B não é uma classificação metodológica da evidência.

## 10. Campos públicos do ranking

Antes de exportar, o ranker aplica uma allowlist aos campos de entrada. Entre os campos preservados estão:

- source/provider;
- title;
- abstract/summary/snippet;
- DOI/PMID/PMCID;
- URL;
- journal;
- ano/data;
- article type;
- authors;
- keywords/subjects;
- queries e metadados de coleta suportados.

O ranker acrescenta:

- `reference_score`;
- `taxonomy_groups`;
- `matched_terms`;
- `focus_keyword_hits`;
- `document_type_hits`;
- `reference_year`;
- `reference_provider`;
- `reference_rank`;
- `reference_tier`.

## 11. Exports

### JSONL

```text
project_output_reference/reference_ranking/reference_ranking.jsonl
```

Contém todo o conjunto ranqueado, um objeto JSON por linha.

### CSV

```text
project_output_reference/reference_ranking/reference_ranking.csv
```

Usa UTF-8 com BOM e achata listas com separador ` | `.

### Markdown

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
```

Contém apenas o TOP N configurado e apresenta título, score, faixa, provider, ano, identificadores, URL, grupos de taxonomia e focus keywords quando disponíveis.

### Resumo da execução

```text
project_output_reference/reference_ranking/latest.json
```

Registra:

- `mode`;
- `status`;
- `created_at`;
- arquivos-fonte usados;
- `records_input`;
- `records_unique`;
- `taxonomy_groups_loaded`;
- `focus_keywords`;
- `top_n`;
- caminhos dos outputs.

## 12. Estado e checkpoints

O PubMed salva checkpoints para permitir retomada. O ranker lê os masters registrados nos arquivos `latest.json` das coletas geral e latino-americana.

Por isso, apagar a árvore de output pode remover estado útil de retomada e rastreabilidade.

## 13. Fronteira científica

O engine não executa, por si só:

- critérios de inclusão/exclusão;
- screening de título/resumo;
- avaliação de risco de viés;
- GRADE;
- PRISMA;
- síntese qualitativa ou quantitativa;
- recomendação clínica.

O output deve ser entendido como uma **fila priorizada de candidatos para leitura humana**.
