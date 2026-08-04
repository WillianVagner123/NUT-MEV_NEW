# Recuperação de texto completo e elegibilidade por artigo

Esta camada completa as fases de **elegibilidade** e **inclusão** do PRISMA a partir de uma sessão de triagem já vinculada a um corpus mestre auditável.

## Princípio central

O relatório em texto completo pertence ao documento, não a um artigo específico. Por isso, sua recuperação é registrada uma única vez. A avaliação de elegibilidade permanece independente para cada Artigo 1–5.

```text
Documento único no corpus
        ↓
Recuperação do texto completo uma vez
        ↓
Avaliação de elegibilidade no Artigo 1
Avaliação de elegibilidade no Artigo 2
Avaliação de elegibilidade no Artigo 3
Avaliação de elegibilidade no Artigo 4
Avaliação de elegibilidade no Artigo 5
```

Um mesmo documento pode ser incluído em vários artigos sem ser duplicado no corpus ou baixado novamente.

## Pré-requisito

O documento só entra na fila de texto completo quando a decisão mais recente na triagem de título e resumo for:

- `INCLUDE`; ou
- `MAYBE`.

Decisões `EXCLUDE` e registros ainda pendentes não entram nessa etapa.

## Recuperação do relatório

Os estados disponíveis são:

- `AVAILABLE`: texto completo disponível por arquivo local ou URL;
- `REQUESTED`: solicitado a autor, biblioteca ou serviço de comutação;
- `NOT_FOUND`: relatório não localizado após as tentativas documentadas;
- `PAYWALLED`: acesso bloqueado e não resolvido;
- `FAILED`: falha técnica ou operacional documentada.

Estados `NOT_FOUND`, `PAYWALLED` e `FAILED` exigem notas explicativas.

Quando um arquivo local é informado, o sistema:

1. verifica se o arquivo existe;
2. calcula SHA-256;
3. registra o tipo de conteúdo;
4. verifica novamente a integridade antes de permitir a decisão ou exportação.

Caminhos relativos são resolvidos a partir da raiz do projeto.

## Elegibilidade em texto completo

A decisão é registrada por:

```text
document_id + article_id + revision
```

Valores permitidos:

- `INCLUDE`;
- `EXCLUDE`;
- `MAYBE`.

Uma decisão só pode ser salva quando a recuperação mais recente estiver como `AVAILABLE` e o arquivo local, quando existente, mantiver o SHA-256 registrado.

### Motivos de exclusão

- `WRONG_POPULATION`;
- `WRONG_CONCEPT`;
- `WRONG_CONTEXT`;
- `WRONG_DOCUMENT_TYPE`;
- `WRONG_STUDY_DESIGN`;
- `WRONG_OUTCOME`;
- `NOT_PRIMARY_SOURCE`;
- `DUPLICATE_PUBLICATION`;
- `NO_USABLE_DATA`;
- `WRONG_PUBLICATION_DATE`;
- `WRONG_LANGUAGE`;
- `OTHER`.

`OTHER` exige nota textual.

## Histórico imutável

Correções não substituem linhas anteriores. Cada mudança cria uma nova revisão append-only. A operação e os relatórios utilizam a revisão mais recente, enquanto o histórico integral permanece no SQLite.

## Tabelas adicionadas

```text
full_text_retrieval_reviews
full_text_eligibility_decisions
full_text_exports
```

As tabelas são adicionadas ao mesmo `search_registry.sqlite3`, sem migração destrutiva das etapas anteriores.

## Contagens PRISMA por artigo

Para cada Artigo 1–5, o sistema calcula:

- relatórios buscados para recuperação;
- relatórios recuperados;
- relatórios não recuperados;
- relatórios aguardando recuperação;
- relatórios avaliados para elegibilidade;
- relatórios excluídos em texto completo;
- relatórios incluídos;
- relatórios em dúvida;
- relatórios pendentes de avaliação;
- motivos de exclusão em texto completo.

Para estratégias `PILOT`, todas as decisões permanecem auditáveis, mas as colunas iniciadas por `prisma_` são exportadas como zero.

## Saídas

```text
<build_dir>/full_text/<session_id>/<export_id>/
├── full_text_retrieval_reviews.csv
├── full_text_eligibility_decisions.csv
├── full_text_queue.csv
├── included_documents_by_article.csv
├── prisma_full_text_by_article.csv
├── prisma_full_text_by_article.json
└── full_text_manifest.json
```

O manifesto inclui:

- corpus e versão de busca de origem;
- hashes das entradas;
- hashes de todas as saídas;
- resumo por artigo;
- regras de governança aplicadas.

## Governança

- recuperação registrada uma vez por documento;
- elegibilidade independente por artigo;
- decisão humana autoritativa;
- exclusão sempre justificada;
- revisões append-only;
- arquivos locais verificados por SHA-256;
- corpus mestre nunca sobrescrito.
