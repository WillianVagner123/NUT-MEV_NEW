# NutEV Reference Engine

**Descoberta, normalização, rastreabilidade, deduplicação, classificação e priorização de referências para Nutrição do Estilo de Vida.**

> Stable software release: **v1.0.0**  
> DOI da versão: **10.5281/zenodo.21998607**  
> Python: **3.12–3.13**  
> Licença: **MIT**

O **NutEV Reference Engine** é um software de recuperação de informação para encontrar e organizar referências candidatas. Ele coleta registros em múltiplas fontes, normaliza metadados, aplica guardrails de rastreabilidade, deduplica por uma regra canônica de identidade, classifica pela taxonomia NutEV e gera uma fila técnica de leitura.

O score **não** representa qualidade metodológica, elegibilidade científica, certeza da evidência, força de recomendação ou recomendação clínica.

## Estado científico atual

O projeto está sob um protocolo explícito de reabilitação/validação científica. O estado atual permanece:

```text
B — DEMOTE
```

Isto significa: o software funciona como utilitário operacional/experimental, mas seu benefício científico incremental sobre baselines e ferramentas existentes **ainda não foi demonstrado**.

O protocolo, o status, o gold-standard plan e os ledgers de resultados ficam em `validation/`. Métricas não executadas permanecem marcadas como `NOT_TESTED`; o projeto não preenche resultados por inferência.

## Fluxo canônico

```text
SEARCH
  -> NORMALIZE
  -> TRACEABILITY GATE
  -> DEDUPLICATE
  -> CLASSIFY
  -> RANK
  -> EXPORT
  -> AUDIT
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

## Instalação e execução

Primeira instalação:

```bat
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git
cd NutEV-Evidence-Engine
Iniciar-NutEV-Windows.bat
```

Repositório já instalado:

```bat
cd %USERPROFILE%\NutEV-Evidence-Engine
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
Iniciar-NutEV-Windows.bat
```

Para auditoria, preserve o SHA mostrado por `git rev-parse HEAD` junto com os manifests e outputs daquela execução.

## Saídas principais

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/reference_quarantine.jsonl
project_output_reference/reference_ranking/AUDIT_MANIFEST.json
project_output_reference/reference_ranking/latest.json
```

- `TOP_REFERENCIAS.md`: TOP N para priorização de leitura.
- `reference_ranking.csv`: tabela completa para inspeção/planilha.
- `reference_ranking.jsonl`: saída estruturada.
- `reference_quarantine.jsonl`: registros bloqueados pelo gate.
- `AUDIT_MANIFEST.json`: hashes, política, fontes, contagens e assertions.
- `latest.json`: resumo da execução.

## Guardrails de rastreabilidade

O comportamento padrão é fail-closed.

Um registro precisa de provider, título e uma rota rastreável. As classes são:

- `A_IDENTIFIER`: DOI, PMID ou PMCID sintaticamente plausível;
- `B_TRACEABLE_URL`: URL HTTP/HTTPS válida quando não há identificador válido;
- `Q_INCOMPLETE_ORIGIN`: provider ou título ausente;
- `Q_INVALID_IDENTIFIER`: identificador presente, porém malformado, sem URL HTTP/HTTPS válida;
- `Q_UNTRACEABLE`: sem identificador válido e sem URL HTTP/HTTPS válida.

Registros `Q_*` ficam fora do ranking por padrão. O Engine não inventa nem repara identificadores para retirar um item da quarentena.

A validação sintática não prova que um DOI/PMID/PMCID resolve para o documento correto; isso continua sendo uma limitação explícita.

## Identidade e deduplicação

Coleta e ranking usam o mesmo contrato canônico em `src/nutev/reference_identity.py`:

```text
DOI válido
  -> PMID válido
  -> URL HTTP(S) normalizada
  -> título normalizado
```

A regra é determinística e usada nas duas etapas. Quando duas manifestações têm a mesma identidade, o Engine preserva preferencialmente o registro com texto descritivo mais rico.

Isto **não** é deduplicação semântica/work-level completa. Republicações, versões, traduções, documentos irmãos ou manifestações com identificadores diferentes ainda podem permanecer separadas.

## Taxonomia canônica

A classificação ativa é controlada por:

```text
config/taxonomy_registry.json
```

Versão canônica atual:

```text
2026-08-v2
```

As dimensões de classificação são:

```text
domain
context
condition
outcome
```

Os arquivos `config/keyword_taxonomy*.json` permanecem como fontes de vocabulário. O registry decide quais caminhos semânticos são canônicos.

`workstreams.*` e `global.document_types.*` não entram no score taxonômico. Um novo caminho semântico não registrado causa `TaxonomyError` em vez de criar silenciosamente uma categoria nova.

Cada referência pode receber:

- `taxonomy_primary`;
- `taxonomy_secondary`;
- `taxonomy_groups`;
- `taxonomy_group_scores`;
- `taxonomy_primary_rank`;
- `taxonomy_ranks`.

A taxonomia descreve **sobre o que** o documento trata. Ela não é nível de evidência nem qualidade científica.

## Ranking

O score atual combina sinais explícitos de:

- correspondência taxonômica;
- palavras-chave foco;
- tipo documental textual;
- provider;
- identificador primário válido;
- recência;
- penalidades por metadados ausentes.

Os caps atuais para taxonomia e focus keywords ficam em `config/reference_mode.json`. Tipos documentais sobrepostos não empilham bônus: apenas o maior peso é aplicado.

O campo `score_breakdown` mostra a contribuição de cada componente.

Faixas atuais:

- `A_TOP_REFERENCE`: posições 1–20;
- `B_STRONG_REFERENCE`: posições 21–100;
- `C_DISCOVERY`: posições seguintes.

Essas faixas significam **prioridade técnica de leitura**, não força científica.

## Fontes suportadas

O perfil operacional integra, conforme disponibilidade/configuração:

- PubMed;
- Europe PMC;
- OpenAlex;
- Crossref;
- DOAJ;
- Semantic Scholar;
- fontes oficiais configuradas;
- LILACS/BVS e SciELO por rota nativa;
- Google Programmable Search, Brave e SerpAPI quando há credenciais.

Scopus e Web of Science não são simulados. Sem acesso/licença configurada, o Engine registra a indisponibilidade e não fabrica substitutos.

Os limites de coleta são tetos operacionais, não garantia de cobertura exaustiva.

## Perfil profundo

No CMD:

```bat
set NUTEV_DEEP_COLLECTION=1
Iniciar-NutEV-Windows.bat
```

Para voltar ao perfil padrão:

```bat
set NUTEV_DEEP_COLLECTION=
```

O perfil profundo aumenta limites de coleta, mas não transforma a busca em levantamento exaustivo.

## Auditoria

Cada execução bem-sucedida de ranking registra:

- política de guardrails;
- versão/modo da taxonomia;
- hashes das configurações;
- hashes dos masters de entrada;
- contagens de rastreáveis e quarentena;
- hashes dos outputs;
- assertions do runtime.

A auditabilidade prova integridade e proveniência do pipeline em relação aos manifests. Ela **não prova verdade bibliográfica ou validade científica**.

Veja:

- `docs/AUDITABILITY_AND_GUARDRAILS.md`;
- `docs/ARCHITECTURE.md`;
- `docs/TAXONOMY.md`;
- `docs/KNOWN_LIMITATIONS.md`.

## Validação científica

O projeto não deve ser promovido acima de `B — DEMOTE` apenas porque CI, Windows smoke ou hashes passam.

A validação planejada exige, entre outros itens:

- gold standard independente;
- comparadores/baselines;
- precision/recall@k;
- MAP, MRR e nDCG;
- ablation study;
- validação humana da taxonomia;
- benchmark de deduplicação;
- contribuição marginal por provider;
- auditoria de perda de recall por quarentena;
- sensibilidade do ranking;
- conjunto externo selado;
- estudo de workload quando aplicável.

Arquivos canônicos:

```text
validation/SCIENTIFIC_VALIDATION_PROTOCOL.md
validation/SCIENTIFIC_VALIDATION_STATUS.md
validation/GOLD_STANDARD_PROTOCOL.md
validation/BENCHMARK_PLAN.md
validation/SCIENTIFIC_VALIDATION_REPORT.md
```

## NutEV Validation (MVP web)

O diretório `apps/nutev-validation/` contém um MVP web separado do runtime do Reference Engine para operacionalizar o gate humano cego da validação científica.

- modo local sem backend, com IndexedDB, retomada e exportação do packet preenchido;
- modo online preparado para login por magic link via Supabase;
- RLS separa os avaliadores e impede leitura das decisões do outro assessor durante `assessment`;
- julgamento `0/1/2` com justificativa, timestamp, progresso, atalhos e "revisar depois";
- import do `QUESTIONS.csv` e dos packets assessor-safe com verificação de SHA-256 e rejeição de score/rank/taxonomia/origem do sistema;
- adjudicação somente depois do fechamento da avaliação cega;
- exportação compatível com `tools/validate_gold_standard.py`;
- MVP restrito ao split `validation`; o conjunto `external_test` permanece fora da aplicação e selado.

O app **não** altera score, ranking, taxonomia ou runtime e não calcula métricas nem promove o estado científico automaticamente. O modo local funciona sem servidor; o modo online é deployável como frontend estático com backend Supabase. Veja `apps/nutev-validation/LOCAL_MODE.md`, `apps/nutev-validation/README.md` e `apps/nutev-validation/DEPLOYMENT.md`.

## O que este projeto não é

O NutEV Reference Engine não é:

- revisão sistemática/scoping review automática;
- mecanismo PRISMA;
- avaliador de risco de viés;
- avaliador automático de qualidade metodológica;
- sistema de recomendação clínica;
- substituto de leitura crítica humana;
- simulador de bases licenciadas indisponíveis;
- gerador de referências por IA.

## Desenvolvimento

```bash
python -m pip install -e ".[dev]"
PYTHONPATH=src python -m pytest -q nutev_tests
python -m compileall -q src tools nutev_tests
ruff check src tools nutev_tests --select F,E9
```

O CI inclui testes em Python 3.12/3.13, Windows smoke, contrato de guardrails, typecheck, lint/compile, security scan, dependency review, CodeQL e validação de artefatos de release.

## Release estável

A release `v1.0.0` é histórica e imutável. Desenvolvimento posterior ocorre na `main`; não mova nem recrie essa tag.

Release: `https://github.com/WillianVagner123/NutEV-Evidence-Engine/releases/tag/v1.0.0`  
Zenodo: `https://zenodo.org/records/21998607`
