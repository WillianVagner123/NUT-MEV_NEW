# Esquema SQLite consolidado

## Banco canônico

O registro científico utiliza:

```text
<project_root>/01_querypacks/search_registry.sqlite3
```

Todos os inicializadores são aditivos e idempotentes. O banco usa:

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 30000;
```

As tabelas anteriores não são apagadas ou recriadas destrutivamente.

## Estratégias de busca

### `search_strategies`
Identidade estável da estratégia global.

### `search_strategy_versions`
Versões imutáveis da consulta, dos filtros e das expressões por base. Relação N:1 com `search_strategies`.

### `search_executions`
Execuções individuais por base e amplitude.

## Execução e snapshots

### `search_runs`
Agrupa as bases executadas para uma versão congelada.

### `search_execution_artifacts`
Registra expressão exata, filtro, status, contagem, snapshot e SHA-256 por base.

## Corpus e deduplicação

### `search_corpus_builds`
Construções imutáveis do corpus por `run_id`.

### `search_dedup_decisions`
Decisões de retenção e duplicata automática por registro de origem.

### `search_duplicate_candidates`
Pares semelhantes que exigem decisão humana.

## Triagem

### `screening_article_catalog`
Catálogo estável dos Artigos 1–5.

### `screening_sessions`
Sessões científicas ligadas a um corpus e a uma versão do protocolo.

### `article_screening_decisions`
Decisões append-only de título/resumo por documento, artigo e etapa.

### `duplicate_candidate_reviews`
Revisões humanas das possíveis duplicatas.

### `screening_exports`
Manifestos e artefatos das exportações de triagem.

## Texto completo e elegibilidade

### `full_text_retrieval_reviews`
Estado de recuperação do relatório por documento. O texto completo é compartilhado pelos artigos.

### `full_text_eligibility_decisions`
Decisões append-only de texto completo por documento e artigo.

### `full_text_exports`
Exportações da etapa de elegibilidade e inclusão final.

## Extração estruturada

### `extraction_schema_fields`
Versões dos campos comuns e específicos por artigo.

Chave lógica:

```text
scope_key + article_id + field_key + revision
```

### `extraction_submissions`
Extrações dos revisores 1 e 2.

Chave lógica:

```text
session_id + document_id + article_id + reviewer_slot + revision
```

Cada submissão preserva um snapshot do schema usado e o SHA-256 do texto completo.

### `extraction_adjudications`
Decisões finais por campo divergente. Não modifica as submissões originais.

## Avaliação metodológica

### `quality_instrument_versions`
Versões configuráveis dos instrumentos.

### `quality_instrument_domains`
Domínios, opções de julgamento e obrigatoriedade de cada versão.

### `quality_instrument_assignments`
Instrumento selecionado para cada combinação documento-artigo, com justificativa e base humana ou sugestão revisada.

### `quality_assessments`
Avaliações dos revisores 1 e 2, com julgamentos por domínio, julgamento global e SHA-256 da fonte.

### `quality_adjudications`
Avaliação metodológica final após comparação da dupla.

### `evidence_matrix_exports`
Registro dos exports finais, caminhos e hash do manifesto.

## Relações principais

```text
search_strategies
  └── search_strategy_versions
        └── search_runs
              ├── search_execution_artifacts
              └── search_corpus_builds
                    └── screening_sessions
                          ├── article_screening_decisions
                          ├── duplicate_candidate_reviews
                          ├── full_text_retrieval_reviews
                          ├── full_text_eligibility_decisions
                          ├── extraction_submissions
                          ├── extraction_adjudications
                          ├── quality_instrument_assignments
                          ├── quality_assessments
                          ├── quality_adjudications
                          └── evidence_matrix_exports
```

## Política de revisão

Para obter o estado operacional atual, as consultas selecionam `MAX(revision)` dentro da chave lógica. As linhas antigas permanecem no banco para auditoria.

Não use `UPDATE` para substituir uma decisão científica. Crie uma nova revisão.

## Compatibilidade

Os inicializadores chamam a camada imediatamente anterior e utilizam `CREATE TABLE IF NOT EXISTS`. Dessa forma, um banco criado antes das tabelas de extração e qualidade é atualizado sem perder estratégias, execuções, corpus, triagem ou elegibilidade.

## Segurança

- Consultas parametrizadas para valores do usuário.
- Foreign keys habilitadas.
- Campos JSON serializados pelo programa.
- Sem armazenamento de credenciais.
- Sem armazenamento de conteúdo integral protegido no SQLite.
- Caminhos e hashes apontam para artefatos locais do projeto.
