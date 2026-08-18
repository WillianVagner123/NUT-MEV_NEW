# Arquitetura do NutEV Reference Engine

Este documento descreve o comportamento implementado atualmente no repositório. Ele deve ser atualizado sempre que o contrato de coleta, integridade, deduplicação, scoring, quarentena ou exportação mudar.

## 1. Fluxo

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> TRACEABILITY GATE -> RANK -> EXPORT -> AUDIT
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
- salvar outputs por provider e `master_records.jsonl`;
- calcular SHA-256 do master e registrá-lo no manifesto;
- atualizar o estado de execução usado pelo ranker.

### Fontes latino-americanas nativas

`tools/run_latin_sources.py`

Responsabilidades:

- tentar LILACS/BVS e SciELO pelas interfaces públicas nativas configuradas;
- preservar `source_provider`;
- registrar `401`/`403` como indisponibilidade de acesso automatizado;
- nunca substituir a fonte por outra silenciosamente;
- reter evidência HTML quando a interface permite coleta;
- gerar `latin_native_records.jsonl` e SHA-256 do master.

### Guardrails

`src/nutev/audit_guardrails.py`

Responsabilidades:

- calcular hashes de arquivos e payloads canônicos;
- verificar `master_records_sha256` antes de o ranker consumir um master;
- classificar rastreabilidade de cada registro;
- marcar registros que devem ser colocados em quarentena;
- gerar `audit_origin_sha256` determinístico;
- falhar quando a integridade declarada não pode ser comprovada.

### Ranking

`tools/rank_references.py`

Responsabilidades:

- localizar os masters mais recentes registrados nos estados de coleta;
- verificar SHA-256 dos masters antes da leitura;
- carregar todas as taxonomias `config/keyword_taxonomy*.json`;
- carregar `config/reference_mode.json` e a política de guardrails;
- aplicar gate de rastreabilidade;
- exportar registros bloqueados para quarentena;
- aplicar deduplicação somente aos registros elegíveis;
- calcular score explicável e com caps;
- ordenar registros e atribuir faixa A/B/C;
- exportar JSONL, CSV, Markdown, quarentena e manifesto de auditoria.

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

## 4. Configuração do ranking e guardrails

Arquivo:

```text
config/reference_mode.json
```

Valores atuais:

- `top_n = 100`;
- focus keywords configuradas;
- pesos por provider;
- política de rastreabilidade e integridade;
- caps de score para taxonomia e focus keywords;
- modo de scoring de tipo documental.

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

Política canônica:

```json
{
  "guardrails": {
    "require_traceable_origin": true,
    "fail_on_input_hash_mismatch": true,
    "taxonomy_score_cap": 60,
    "focus_score_cap": 40,
    "document_type_scoring": "highest_weight_only"
  }
}
```

## 5. Integridade de entrada

Para cada `latest.json` de coleta, o ranker lê:

```text
master_records_path
master_records_sha256
```

Quando um master é declarado:

1. o arquivo deve existir;
2. o SHA-256 declarado deve existir;
3. o SHA-256 real deve ser idêntico ao declarado;
4. cada linha JSONL deve ser um objeto JSON válido.

Falha em qualquer uma dessas verificações interrompe o ranking. Não há reparo silencioso nem fallback para um arquivo não verificado.

## 6. Gate de rastreabilidade

Antes do scoring, cada registro recebe uma classe:

| Classe | Regra |
|---|---|
| `A_IDENTIFIER` | possui DOI, PMID ou PMCID |
| `B_TRACEABLE_URL` | possui URL HTTP/HTTPS válida |
| `Q_INCOMPLETE_ORIGIN` | falta provider ou título |
| `Q_UNTRACEABLE` | provider/título presentes, mas sem identificador nem URL |

Por padrão, classes `Q_*` não entram no ranking e são exportadas em:

```text
reference_quarantine.jsonl
```

O engine não cria identificadores, URLs, autores, anos ou abstracts para fazer um registro passar pelo gate.

Cada registro recebe ainda:

- `audit_policy_version`;
- `audit_traceability`;
- `audit_quarantined`;
- `audit_reasons`;
- `audit_origin_sha256`;
- `audit_source_manifest_path`;
- `audit_source_master_sha256`;
- `audit_source_run_id`.

## 7. Carregamento da taxonomia

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

## 8. Regra de identidade e deduplicação

A identidade de cada registro elegível é determinada na seguinte ordem:

```text
DOI -> PMID -> URL -> título normalizado
```

Se dois registros têm a mesma identidade, permanece a versão com maior quantidade de texto descritivo entre `abstract`, `summary` e `snippet`.

Consequências:

- registros com o mesmo DOI tendem a ser unidos;
- registros com o mesmo PMID tendem a ser unidos quando não há DOI;
- registros com a mesma URL tendem a ser unidos quando não há DOI/PMID;
- título é fallback de identidade;
- publicações semanticamente equivalentes com identificadores diferentes podem permanecer separadas.

Esta regra não é deduplicação semântica completa.

## 9. Scoring atual

O score final é a soma de componentes explicitamente registrados em `score_breakdown`.

### 9.1 Termos da taxonomia

Para cada termo correspondente:

| Campo | Pontos |
|---|---:|
| título | +6 |
| keywords/subjects | +4 |
| abstract/summary/snippet | +2 |

A soma de um mesmo termo é limitada a `8` pontos.

O ranker considera no máximo quatro termos correspondentes por grupo. Quando um grupo tem pelo menos um hit, o grupo recebe ainda `+3` pontos.

Para reduzir inflação decorrente de fragmentação histórica em muitos grupos, o total da taxonomia é limitado por:

```text
taxonomy_score_cap = 60
```

O valor anterior ao cap permanece disponível em `score_breakdown.taxonomy_raw_before_cap`.

### 9.2 Focus keywords

Para cada palavra-chave foco:

| Campo | Pontos |
|---|---:|
| título | +10 |
| keywords/subjects | +6 |
| abstract/summary/snippet | +4 |

O total deste componente é limitado por:

```text
focus_score_cap = 40
```

O valor bruto permanece em `score_breakdown.focus_raw_before_cap`.

### 9.3 Tipo documental no título

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

Todas as expressões encontradas aparecem em `document_type_hits`, mas somente a de maior peso entra no score. O termo efetivamente aplicado fica em `document_type_applied`.

Isso evita o antigo empilhamento de `clinical practice guideline` + `practice guideline` + `guideline`.

### 9.4 Provider

É adicionado o bônus definido em `provider_weights`.

### 9.5 Identificadores

Se o registro tiver pelo menos um entre DOI, PMID ou PMCID:

```text
+2 pontos
```

### 9.6 Recência

Usando o ano encontrado nos campos de data/ano:

- idade de até 5 anos: `+4`;
- idade de 6 a 10 anos: `+2`;
- mais de 10 anos: sem bônus de recência.

O ano válido é limitado ao intervalo de 1900 até o ano atual + 1.

### 9.7 Penalidades

- sem título: `-25`;
- sem abstract/summary/snippet: `-1`.

Na execução estrita, um registro sem título já terá sido colocado em quarentena antes do scoring.

### 9.8 Score breakdown

Cada linha ranqueada contém:

```json
{
  "score_breakdown": {
    "taxonomy": 0,
    "taxonomy_raw_before_cap": 0,
    "focus_keywords": 0,
    "focus_raw_before_cap": 0,
    "document_type": 0,
    "provider": 0,
    "identifier": 0,
    "recency": 0,
    "penalties": 0
  }
}
```

A soma dos componentes aplicados corresponde ao `reference_score`.

## 10. Ordenação

Após o scoring, os registros são ordenados por:

1. score decrescente;
2. ano decrescente;
3. título em ordem lexical.

## 11. Faixas de prioridade

A faixa é definida pela posição, e não por um ponto de corte absoluto do score:

- posições 1–20: `A_TOP_REFERENCE`;
- posições 21–100: `B_STRONG_REFERENCE`;
- demais posições: `C_DISCOVERY`.

Uma faixa A ou B não é uma classificação metodológica da evidência.

## 12. Campos públicos do ranking

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
- queries e metadados de coleta suportados;
- campos de rastreabilidade `audit_*` explicitamente permitidos.

O ranker acrescenta:

- `reference_score`;
- `score_breakdown`;
- `taxonomy_groups`;
- `matched_terms`;
- `focus_keyword_hits`;
- `document_type_hits`;
- `document_type_applied`;
- `reference_year`;
- `reference_provider`;
- `reference_rank`;
- `reference_tier`.

## 13. Exports

### JSONL ranqueado

```text
project_output_reference/reference_ranking/reference_ranking.jsonl
```

Contém todo o conjunto elegível ranqueado, um objeto JSON por linha.

### CSV

```text
project_output_reference/reference_ranking/reference_ranking.csv
```

Usa UTF-8 com BOM e achata listas com separador ` | `.

### Markdown

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
```

Contém o TOP N configurado e apresenta rastreabilidade, origem SHA-256, score breakdown e sinais de ranking.

### Quarentena

```text
project_output_reference/reference_ranking/reference_quarantine.jsonl
```

Contém registros que não passam o gate de rastreabilidade. Esses itens não entram no ranking padrão.

### Manifesto de auditoria

```text
project_output_reference/reference_ranking/AUDIT_MANIFEST.json
```

Registra:

- versão da política;
- política ativa;
- integridade dos masters de entrada;
- SHA-256 das configurações;
- contagens de entrada/rastreabilidade/quarentena;
- SHA-256 dos outputs;
- assertions de guardrail.

### Resumo da execução

```text
project_output_reference/reference_ranking/latest.json
```

Registra status, hashes, fontes, contagens, política e caminhos dos outputs.

## 14. Estado e checkpoints

O PubMed salva checkpoints para permitir retomada. O ranker lê os masters registrados nos arquivos `latest.json` das coletas geral e latino-americana e verifica seus hashes.

Apagar a árvore de output pode remover estado útil de retomada e rastreabilidade.

## 15. Fronteira científica

O engine não executa, por si só:

- critérios de inclusão/exclusão;
- screening de título/resumo;
- avaliação de risco de viés;
- GRADE;
- PRISMA;
- síntese qualitativa ou quantitativa;
- recomendação clínica;
- geração de referências por modelo de linguagem.

O output é uma **fila priorizada de candidatos rastreáveis para leitura humana**.

Para o contrato completo de auditoria, consulte [`AUDITABILITY_AND_GUARDRAILS.md`](AUDITABILITY_AND_GUARDRAILS.md).
