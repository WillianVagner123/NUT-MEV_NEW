# Triagem humana por artigo e PRISMA

Esta camada inicia **depois** da construção do corpus mestre auditável. Ela não
altera os snapshots brutos, o corpus normalizado nem o arquivo mestre da
execução. Todas as decisões humanas são registradas em tabelas aditivas e cada
nova decisão cria uma revisão.

## Objetivos

1. revisar possíveis duplicatas identificadas apenas por título e ano;
2. triar títulos e resumos separadamente para os Artigos 1–5;
3. permitir que um mesmo documento seja incluído em vários artigos;
4. exigir motivo padronizado para toda exclusão;
5. gerar contagens operacionais e PRISMA independentes por artigo;
6. preservar snapshots reproduzíveis da triagem.

## Ordem metodológica

```text
Corpus mestre imutável
        ↓
Revisão das possíveis duplicatas
        ↓
Corpus efetivo para triagem
        ↓
Triagem por título e resumo para cada artigo
        ↓
Inclusão, exclusão ou dúvida
        ↓
Snapshot PRISMA por artigo
```

A resolução de duplicatas deve ocorrer antes da triagem do documento que seria
removido. O sistema bloqueia a confirmação de uma duplicata quando o documento
selecionado para remoção já possui decisão de triagem.

## Artigos

O catálogo inicial contém:

- `article_1` — Artigo 1;
- `article_2` — Artigo 2;
- `article_3` — Artigo 3;
- `article_4` — Artigo 4;
- `article_5` — Artigo 5.

Os nomes e descrições podem ser ajustados no painel. A descrição deve registrar
o critério de pertinência usado pela equipe. A alteração do nome não muda o ID
estável do artigo.

## Decisões de triagem

Para cada combinação `document_id + article_id + stage`, o revisor pode registrar:

- `INCLUDE`;
- `EXCLUDE`;
- `MAYBE`.

As decisões são append-only. Uma mudança de decisão cria uma nova `revision` e
a consulta operacional usa a revisão mais recente. O histórico anterior é
preservado.

### Motivos de exclusão

Toda decisão `EXCLUDE` exige um motivo:

- `NOT_RELEVANT_TO_ARTICLE`;
- `WRONG_POPULATION`;
- `WRONG_CONCEPT`;
- `WRONG_CONTEXT`;
- `WRONG_DOCUMENT_TYPE`;
- `WRONG_OUTCOME`;
- `WRONG_PUBLICATION_DATE`;
- `WRONG_LANGUAGE`;
- `INSUFFICIENT_METADATA`;
- `OTHER`.

Quando `OTHER` é usado, uma nota explicativa é obrigatória.

## Duplicatas humanas

Coincidências somente por título e ano continuam sendo candidatas, nunca
exclusões automáticas. O revisor pode registrar:

- `CONFIRMED_DUPLICATE`, escolhendo o documento mantido;
- `REJECTED`, declarando que os documentos são distintos.

O corpus mestre permanece imutável. A decisão humana cria um **corpus efetivo**
para a triagem, no qual o documento removido deixa de aparecer nas filas e nas
contagens posteriores.

## PRISMA por artigo

Para cada artigo são calculados:

- registros disponíveis após a deduplicação automática e humana;
- registros triados;
- incluídos;
- excluídos;
- dúvidas;
- pendentes;
- motivos de exclusão;
- registros PRISMA triados;
- registros PRISMA excluídos;
- relatórios buscados para recuperação de texto completo.

Se a estratégia de origem for `PILOT` ou estiver marcada como não elegível para
PRISMA, as decisões continuam preservadas, mas as colunas PRISMA permanecem
zeradas.

## Banco de dados

As tabelas adicionadas são:

```text
screening_article_catalog
screening_sessions
article_screening_decisions
duplicate_candidate_reviews
screening_exports
```

Nenhuma tabela histórica é removida ou reescrita.

## Snapshots

Cada exportação cria uma pasta imutável:

```text
<build_dir>/screening/<session_id>/<export_id>/
├── article_screening_decisions.csv
├── duplicate_review_decisions.csv
├── screening_queue.csv
├── prisma_by_article.csv
├── prisma_by_article.json
└── screening_manifest.json
```

O manifesto registra os hashes SHA-256 das entradas e saídas, a política de
governança e o resumo das contagens.

## Governança

- decisões humanas são autoritativas;
- um documento pode servir a vários artigos;
- exclusões sempre exigem justificativa;
- candidatos por título e ano nunca são removidos automaticamente;
- o corpus mestre não é sobrescrito;
- cada correção gera nova revisão;
- o snapshot representa o estado da triagem no momento da exportação.
