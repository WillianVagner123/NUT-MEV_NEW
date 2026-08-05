# Auditoria da pipeline científica completa — 2026

## Escopo

A auditoria revisou a arquitetura da branch `main` após a implantação das camadas de busca versionada, execução por bases, corpus mestre, deduplicação, triagem por artigo e texto completo.

## Constatações

### Componentes já consolidados

- consulta global para todos os artigos;
- versionamento imutável;
- execução de PubMed, Europe PMC, Crossref e OpenAlex;
- snapshots por base;
- tolerância a falha parcial;
- normalização bibliográfica;
- deduplicação automática por identificadores fortes;
- revisão humana de pares por título e ano;
- triagem independente nos Artigos 1–5;
- recuperação compartilhada do texto completo;
- elegibilidade e PRISMA por artigo;
- verificação de SHA-256 nas etapas dependentes.

### Lacunas funcionais identificadas

- ausência de schema configurável de extração por artigo;
- ausência de dupla extração e comparação campo a campo;
- ausência de adjudicação da extração;
- plano de qualidade metodológica existente apenas como documentação, sem ledger operacional completo;
- ausência de dupla avaliação metodológica e adjudicação;
- ausência de matriz final única que combine extração e qualidade;
- navegação do dashboard sem indicação explícita das etapas 10–12;
- PR #966 aberto como rascunho duplicado de código já incorporado.

## Correções aplicadas

- fechamento do PR duplicado #966;
- ledger aditivo para schemas, extrações e adjudicações;
- campos comuns e campos específicos por Artigos 1–5;
- dupla extração com revisões append-only;
- seleção e versionamento de instrumentos metodológicos;
- instrumentos iniciais configuráveis por tipo documental;
- dupla avaliação por domínio;
- adjudicação metodológica;
- exportação da matriz final com SHA-256;
- painel Streamlit para extração, divergências, qualidade e exportação;
- documentação consolidada do fluxo e do SQLite;
- testes de compatibilidade com banco anterior e integridade de artefatos.

## Decisões arquiteturais

A nova camada reutiliza:

- `screening_sessions` como unidade científica;
- a inclusão final de `full_text_eligibility_decisions`;
- o SHA-256 de `full_text_retrieval_reviews`;
- o catálogo existente dos Artigos 1–5;
- o banco canônico `search_registry.sqlite3`.

Não foi criado um segundo corpus, um segundo sistema de artigos ou uma nova base paralela.

## Riscos remanescentes

- Os critérios de cada Artigo 1–5 precisam ser definidos pela equipe científica.
- A escolha final do instrumento metodológico depende do desenho e do protocolo.
- Os domínios iniciais são estruturas configuráveis e não substituem os manuais oficiais.
- Não é possível validar conteúdo científico sem dados reais e revisão humana.
- PRs antigos de expansão de taxonomia permanecem fora do escopo desta auditoria e devem ser triados separadamente antes de eventual merge.
