# Arquitetura do NutEV Reference Engine

Este documento descreve o comportamento implementado na `main`. Ele deve ser atualizado sempre que mudar o contrato de coleta, integridade, taxonomia, deduplicação, scoring, ranking ou exportação.

## 1. Fluxo canônico

```text
SEARCH -> NORMALIZE -> TRACEABILITY GATE -> DEDUPLICATE -> CLASSIFY -> RANK -> EXPORT -> AUDIT
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

### Coleta geral — `tools/run_everything_now.py`

Responsabilidades:

- carregar `config/reference_search.json`;
- selecionar perfil `operational` ou `deep`;
- executar os providers suportados;
- preservar a identidade do provider;
- registrar falha ou indisponibilidade sem fabricar substitutos;
- normalizar e deduplicar a coleta geral;
- gerar `master_records.jsonl`;
- calcular e registrar SHA-256 do master.

### Fontes latino-americanas — `tools/run_latin_sources.py`

Responsabilidades:

- tentar LILACS/BVS e SciELO pelas rotas configuradas;
- preservar `source_provider`;
- registrar `401`/`403` como indisponibilidade de automação;
- não simular conteúdo de provider indisponível;
- gerar `latin_native_records.jsonl` e SHA-256 do master.

### Guardrails — `src/nutev/audit_guardrails.py`

Responsabilidades:

- calcular hashes de arquivos e payloads canônicos;
- verificar `master_records_sha256` antes do consumo;
- classificar rastreabilidade por registro;
- colocar registros insuficientemente rastreáveis em quarentena;
- gerar `audit_origin_sha256`;
- falhar quando a integridade declarada não puder ser comprovada.

### Taxonomia — `src/nutev/taxonomy.py`

Responsabilidades:

- ler o vocabulário acumulado em `config/keyword_taxonomy*.json`;
- ler `config/taxonomy_registry.json`;
- normalizar e deduplicar termos;
- mapear leaf paths históricos para IDs canônicos estáveis;
- excluir `workstreams.*` e `global.document_types.*` do score taxonômico;
- falhar com `TaxonomyError` se surgir um novo caminho semântico não registrado;
- devolver metadados de versão, cobertura e configuração para auditoria.

### Ranking — `tools/rank_references.py`

Responsabilidades:

- localizar os masters declarados pelos estados de coleta;
- verificar sua integridade;
- aplicar gate de rastreabilidade;
- exportar a quarentena;
- deduplicar os registros elegíveis;
- compilar a taxonomia canônica;
- classificar cada referência em taxonomia primária e secundárias;
- calcular score explicável;
- gerar rank global e rank dentro de cada grupo taxonômico;
- exportar JSONL, CSV, Markdown e manifesto de auditoria.

## 3. Configuração

### Busca

```text
config/reference_search.json
```

Contém queries e limites operacionais/profundos de providers.

O perfil profundo é ativado por:

```text
NUTEV_DEEP_COLLECTION=1
```

### Ranking e guardrails

```text
config/reference_mode.json
```

Contém `top_n`, focus keywords, pesos de provider e política de guardrails. A política atual inclui:

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

Pesos atuais por provider:

| Token | Peso |
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

### Taxonomia

```text
config/taxonomy_registry.json
config/keyword_taxonomy.json
config/keyword_taxonomy_supplement*.json
```

Os `keyword_taxonomy*.json` são a camada de **vocabulário/proveniência**. O `taxonomy_registry.json` é a camada **canônica de classificação**.

A versão canônica atual é:

```text
2026-08-v2
```

As dimensões são:

```text
domain -> context -> condition -> outcome
```

- `domain`: tema/intervenção;
- `context`: comportamento, implementação, cuidado e contexto social/alimentar;
- `condition`: condição clínica;
- `outcome`: desfecho ou construto.

Detalhes completos: [`TAXONOMY.md`](TAXONOMY.md).

## 4. Integridade de entrada

Para cada master declarado, o ranker exige:

1. `master_records_path` existente;
2. `master_records_sha256` presente;
3. SHA-256 real idêntico ao declarado;
4. JSONL sintaticamente válido e composto por objetos.

Qualquer divergência interrompe o ranking. Não há reparo silencioso.

## 5. Gate de rastreabilidade

Cada registro recebe classificação de rastreabilidade antes do scoring. Por padrão, um registro precisa de provider, título e identificador ou URL HTTP/HTTPS rastreável para entrar no ranking.

Registros bloqueados vão para:

```text
project_output_reference/reference_ranking/reference_quarantine.jsonl
```

O runtime não cria DOI, PMID, PMCID, URL, autor, ano ou abstract para promover um item.

Campos de auditoria incluem:

- `audit_policy_version`;
- `audit_traceability`;
- `audit_quarantined`;
- `audit_reasons`;
- `audit_origin_sha256`;
- `audit_source_manifest_path`;
- `audit_source_master_sha256`;
- `audit_source_run_id`.

## 6. Compilação da taxonomia

O compilador percorre os leaf paths dos arquivos `keyword_taxonomy*.json`.

Em modo canônico:

```text
leaf path
   ↓
root permitido? (global / clinical / outcomes)
   ├─ não -> excluído do score
   ↓ sim
é global.document_types.*?
   ├─ sim -> excluído do score
   ↓ não
está mapeado no taxonomy_registry.json?
   ├─ não -> TaxonomyError / FAIL CLOSED
   ↓ sim
merge + deduplicação de termos
   ↓
grupo canônico
```

Consequências:

- `workstreams.busca1`, `busca2a`, `busca2b`, `a3`, `artigo3_framework` e equivalentes não pontuam;
- tipo documental não é tratado como assunto;
- múltiplos supplements podem contribuir vocabulário para um único grupo canônico;
- um supplement novo não pode criar silenciosamente um grupo de score.

## 7. Classificação taxonômica

Cada grupo produz um score local baseado nos termos encontrados. O ranker registra:

- `taxonomy_primary`;
- `taxonomy_primary_rank`;
- `taxonomy_secondary`;
- `taxonomy_dimensions`;
- `taxonomy_groups`;
- `taxonomy_group_scores`;
- `taxonomy_ranks`.

A taxonomia principal é escolhida na primeira dimensão disponível segundo:

```text
domain -> context -> condition -> outcome
```

Dentro dessa dimensão, vence o grupo com maior score local; empates são resolvidos deterministicamente pelo ID canônico.

## 8. Identidade e deduplicação

A identidade atual é determinada por:

```text
DOI -> PMID -> URL -> título normalizado
```

Quando duas linhas têm a mesma identidade, o engine prefere a versão com texto descritivo mais rico em `abstract`, `summary` ou `snippet`.

Isso não é deduplicação semântica completa. Publicações relacionadas com identificadores distintos podem permanecer separadas.

## 9. Scoring global

### Taxonomia

Para cada termo correspondente:

| Campo | Pontos |
|---|---:|
| título | +6 |
| keywords/subjects | +4 |
| abstract/summary/snippet | +2 |

A contribuição de um termo é limitada a 8 pontos; são usados no máximo quatro termos por grupo; um grupo com hit recebe +3. O total taxonômico é limitado por `taxonomy_score_cap = 60`.

O valor bruto permanece em `score_breakdown.taxonomy_raw_before_cap`.

### Focus keywords

| Campo | Pontos |
|---|---:|
| título | +10 |
| keywords/subjects | +6 |
| abstract/summary/snippet | +4 |

O total é limitado por `focus_score_cap = 40`.

### Tipo documental

O tipo documental é calculado fora da taxonomia. Quando expressões se sobrepõem, todas podem aparecer em `document_type_hits`, mas somente o maior peso entra no score via `document_type_applied`.

Pesos principais:

| Sinal | Pontos |
|---|---:|
| clinical practice guideline | 12 |
| practice guideline | 11 |
| guideline | 10 |
| consensus statement | 9 |
| position/scientific statement | 8 |
| systematic review/meta analysis | 7 |
| framework | 5 |
| recommendation | 4 |

### Outros componentes

- provider: peso configurado em `reference_mode.json`;
- identificador DOI/PMID/PMCID: +2;
- recência até 5 anos: +4;
- recência de 6 a 10 anos: +2;
- ausência de título: -25;
- ausência de abstract/summary/snippet: -1.

Cada linha inclui `score_breakdown` com todos os componentes e valores brutos antes dos caps.

## 10. Ordenação e ranks

### Rank global

Ordem:

1. `reference_score` decrescente;
2. ano decrescente;
3. título lexical.

Faixas:

- 1–20: `A_TOP_REFERENCE`;
- 21–100: `B_STRONG_REFERENCE`;
- demais: `C_DISCOVERY`.

### Rank dentro da taxonomia

Para cada grupo taxonômico, os membros são ordenados por:

1. score local do grupo;
2. score global;
3. ano;
4. título.

Assim uma referência pode ser, por exemplo, 40ª globalmente e 2ª dentro de `domain.dietary_patterns.mediterranean`.

## 11. Outputs

```text
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
project_output_reference/reference_ranking/reference_quarantine.jsonl
project_output_reference/reference_ranking/AUDIT_MANIFEST.json
project_output_reference/reference_ranking/latest.json
```

O CSV inclui os campos de taxonomia/ranking e é a saída tabular para inspeção, planilha e curadoria.

`AUDIT_MANIFEST.json` registra:

- política de guardrails;
- versão/modo da taxonomia;
- integridade dos masters;
- SHA-256 das configurações, incluindo `taxonomy_registry.json`;
- contagens de entrada, rastreabilidade e quarentena;
- hashes dos outputs;
- assertions de integridade e taxonomia.

## 12. Fronteira científica

O engine organiza e prioriza referências rastreáveis. Ele não executa, por si só:

- critérios formais de inclusão/exclusão;
- screening científico;
- avaliação de risco de viés;
- GRADE;
- PRISMA;
- síntese científica;
- recomendação clínica;
- geração de referências por modelo de linguagem.

**Taxonomia descreve sobre o que o documento parece tratar. Ranking descreve prioridade técnica de leitura. Nenhum dos dois é sinônimo de qualidade científica.**

Para auditoria, consulte [`AUDITABILITY_AND_GUARDRAILS.md`](AUDITABILITY_AND_GUARDRAILS.md). Para a taxonomia completa, consulte [`TAXONOMY.md`](TAXONOMY.md).
