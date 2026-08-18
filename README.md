# NutEV Reference Engine

**Descoberta, normalização, deduplicação e priorização de referências para Nutrição do Estilo de Vida.**

> Stable software release: **v1.0.0**  
> DOI da versão: **10.5281/zenodo.21998607**  
> Python: **3.12–3.13**  
> Licença: **MIT**

O **NutEV Reference Engine** é um software de recuperação de informação que coleta referências em múltiplas fontes, normaliza os metadados, aplica uma regra explícita de identidade/deduplicação, cruza os registros com a taxonomia NutEV e gera uma fila priorizada de leitura.

Ele foi desenhado para ajudar a **encontrar e ordenar referências candidatas**. O score não representa qualidade metodológica, elegibilidade científica, força de evidência nem recomendação clínica.

A `main` atual opera com guardrails de rastreabilidade e integridade: masters de coleta são verificados por SHA-256, registros sem origem rastreável são colocados em quarentena e cada execução de ranking gera um manifesto auditável. O engine não usa IA generativa para inventar ou completar referências.

## Fluxo oficial

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT
```

No Windows, o caminho operacional suportado é:

```text
Iniciar-NutEV-Windows.bat
  -> RODAR_TUDO.cmd
     -> run_everything_now.cmd
        -> tools/run_everything_now.py
     -> tools/run_latin_sources.py
     -> tools/rank_references.py
```

## Comece aqui

### 1. Primeira instalação no Windows

Requer Git e Python 3.12 ou 3.13.

```bat
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git
cd NutEV-Evidence-Engine
Iniciar-NutEV-Windows.bat
```

Na primeira execução, o launcher cria `.venv`, atualiza `pip`, instala o projeto em modo editável e inicia a coleta e o ranking.

### 2. Se o repositório já está instalado

```bat
cd %USERPROFILE%\NutEV-Evidence-Engine
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
Iniciar-NutEV-Windows.bat
```

Se o clone estiver em outra pasta, entre nela em vez de usar `%USERPROFILE%\NutEV-Evidence-Engine`.

Para uma execução auditável, guarde o SHA mostrado por:

```bat
git rev-parse HEAD
```

### 3. Como saber se funcionou

Uma execução completa passa pelas três etapas:

```text
[1/3] COLETA MULTI-FONTE
[2/3] LILACS/BVS + SCIELO NATIVO
[3/3] RANKING DE REFERENCIAS
```

O final esperado é:

```text
Coleta geral: codigo 0
LILACS/BVS + SciELO: codigo 0
Ranking: codigo 0
SUCESSO: ranking de referencias gerado.
```

Em 18/08/2026 foi registrada uma execução real no Windows com:

```text
status: COMPLETE
records_input: 8702
records_unique: 8702
taxonomy_groups_loaded: 115
top_n: 100
```

Esse registro está preservado em [`docs/VALIDATED_WINDOWS_RUN_2026-08-18.md`](docs/VALIDATED_WINDOWS_RUN_2026-08-18.md). Esses números descrevem aquela execução específica e não são uma promessa de volume para execuções futuras.

## Saídas principais

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/reference_quarantine.jsonl
project_output_reference/reference_ranking/AUDIT_MANIFEST.json
project_output_reference/reference_ranking/latest.json
```

| Arquivo | Uso |
|---|---|
| `TOP_REFERENCIAS.md` | TOP N em formato humano para priorização de leitura, com rastreabilidade e score breakdown. |
| `reference_ranking.csv` | Tabela completa para planilha, inspeção e curadoria. |
| `reference_ranking.jsonl` | Saída estruturada, um registro JSON por linha. |
| `reference_quarantine.jsonl` | Registros bloqueados por falta de origem rastreável. |
| `AUDIT_MANIFEST.json` | Hashes, política, fontes de entrada, assertions e contagens da execução. |
| `latest.json` | Resumo da execução, fontes de entrada, contagens, hashes e caminhos gerados. |

O launcher do Windows tenta abrir `TOP_REFERENCIAS.md` automaticamente ao final.

## Guardrails e política anti-fabricação

O comportamento padrão é **fail-closed**.

O ranker:

- exige `master_records_sha256` para cada master declarado nos manifests de coleta;
- recalcula o SHA-256 antes de ler o arquivo e interrompe se houver divergência;
- exige provider, título e DOI/PMID/PMCID ou URL HTTP/HTTPS para um item entrar no ranking;
- coloca registros não rastreáveis em `reference_quarantine.jsonl` em vez de completar dados por inferência;
- grava `audit_traceability`, `audit_origin_sha256`, `audit_source_run_id` e `audit_source_master_sha256` nos registros ranqueados;
- grava `score_breakdown` em cada item;
- limita a contribuição total da taxonomia e das focus keywords para reduzir inflação estrutural;
- usa apenas o maior bônus de tipo documental quando expressões se sobrepõem;
- gera `AUDIT_MANIFEST.json` com hashes dos inputs, configurações e outputs.

Classificações de rastreabilidade:

- `A_IDENTIFIER`: DOI, PMID ou PMCID;
- `B_TRACEABLE_URL`: URL HTTP/HTTPS rastreável;
- `Q_INCOMPLETE_ORIGIN`: provider ou título ausente;
- `Q_UNTRACEABLE`: sem identificador e sem URL rastreável.

O guardrail protege **proveniência e integridade do software**, não valida a verdade científica do artigo. Veja [`docs/AUDITABILITY_AND_GUARDRAILS.md`](docs/AUDITABILITY_AND_GUARDRAILS.md).

## Fontes suportadas

O coletor atual integra:

| Fonte | Tipo | Perfil operacional |
|---|---|---:|
| PubMed | API pública | até 2.000 registros |
| Europe PMC | API pública | até 3.000 |
| OpenAlex | API pública | até 3.000 |
| Crossref | API pública | até 1.000 |
| DOAJ | API pública | até 1.000 |
| Semantic Scholar | API pública | até 1.000 |
| Fontes oficiais configuradas | manifesto local | conforme configuração |
| LILACS/BVS | interface pública nativa | tentativa nativa |
| SciELO | interface pública nativa | tentativa nativa |
| Google Programmable Search | opcional | somente com credenciais |
| Brave | opcional | somente com credenciais |
| SerpAPI | opcional | somente com credenciais |

**Scopus e Web of Science não são simulados.** Se o acesso licenciado não estiver configurado, o sistema não inventa resultados equivalentes.

Detalhes: [`docs/SEARCH_PROVIDERS.md`](docs/SEARCH_PROVIDERS.md).

## Perfil operacional e perfil profundo

O padrão é o perfil `operational`, com limites adequados para uma execução comum.

Para ativar o perfil de coleta profunda no CMD:

```bat
set NUTEV_DEEP_COLLECTION=1
Iniciar-NutEV-Windows.bat
```

Limites configurados para o perfil profundo:

| Fonte | Deep limit |
|---|---:|
| PubMed | 9.999 |
| Europe PMC | 50.000 |
| OpenAlex | 50.000 |
| Crossref | 10.000 |
| DOAJ | 10.000 |
| Semantic Scholar | 10.000 |

Para voltar ao perfil normal na mesma sessão:

```bat
set NUTEV_DEEP_COLLECTION=
```

Os limites são **tetos de coleta**, não garantias de cobertura exaustiva.

## Variáveis opcionais

O arquivo `.env.example` documenta os nomes suportados. O runtime atual **não carrega `.env` automaticamente**. Defina as variáveis no ambiente antes de executar.

Exemplo no CMD:

```bat
set NCBI_EMAIL=seu-email@exemplo.com
set NCBI_API_KEY=...
set CROSSREF_MAILTO=seu-email@exemplo.com
set OPENALEX_MAILTO=seu-email@exemplo.com
set S2_API_KEY=...
set GOOGLE_API_KEY=...
set GOOGLE_CSE_ID=...
set BRAVE_API_KEY=...
set SERPAPI_API_KEY=...
```

A ausência de `NCBI_EMAIL`/`ENTREZ_EMAIL` não bloqueia o PubMed; o cliente usa um rate limit mais conservador.

Nunca versione chaves, tokens ou outros segredos.

## Retomada após interrupção

O PubMed usa checkpoints e tenta retomar o trabalho quando possível.

Se uma execução for interrompida:

```bat
Iniciar-NutEV-Windows.bat
```

Não apague `project_output_reference` ou os checkpoints por padrão.

Código `130` normalmente significa interrupção pelo usuário, como `Ctrl+C`.

## Como o ranking funciona

O ranker carrega:

```text
config/reference_mode.json
config/keyword_taxonomy.json
config/keyword_taxonomy_supplement*.json
```

Todos os arquivos que correspondem a `keyword_taxonomy*.json` são carregados.

O score combina componentes explícitos:

- termos da taxonomia em título, palavras-chave e resumo/snippet, com cap total configurável;
- palavras-chave foco configuradas, com cap total configurável;
- maior sinal de tipo documental encontrado no título, sem empilhamento de expressões sobrepostas;
- peso do provider;
- presença de DOI/PMID/PMCID;
- bônus leve de recência;
- penalidade por ausência de título e, em menor grau, de resumo.

Cada registro exporta `score_breakdown`, incluindo valores brutos antes dos caps.

A descrição exata dos pesos atuais e do fluxo interno está em [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

### Faixas de prioridade

- `A_TOP_REFERENCE`: posições 1–20;
- `B_STRONG_REFERENCE`: posições 21–100;
- `C_DISCOVERY`: posições seguintes.

Essas faixas refletem **posição de leitura**, não nível de evidência.

## Deduplicação: o que ela faz e o que ela não faz

A identidade atual é definida nesta ordem:

1. DOI;
2. PMID;
3. URL;
4. título normalizado, quando não há os identificadores anteriores.

Quando dois registros têm a mesma identidade, o engine mantém preferencialmente a versão com texto descritivo mais rico.

Isso **não é deduplicação semântica completa**. O mesmo documento, versões paralelas, publicações associadas ou registros equivalentes com identificadores diferentes podem permanecer separados.

Por isso:

```text
records_unique == records_input
```

significa apenas que nenhuma duplicata foi removida pela regra ativa naquela execução. Não prova que todos os documentos sejam semanticamente distintos.

Veja [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md).

## Configuração

### Busca

```text
config/reference_search.json
```

Contém as consultas canônicas e os limites `provider_limits` e `deep_provider_limits`.

### Ranking e guardrails

```text
config/reference_mode.json
```

Contém `top_n`, palavras-chave foco, pesos dos providers e a política versionada de guardrails.

### Taxonomia

```text
config/keyword_taxonomy*.json
```

Os nomes dos grupos de taxonomia aparecem nos outputs para tornar o matching auditável. O nome de um grupo é apenas um caminho de classificação; não representa força de evidência. A contribuição total da taxonomia é limitada pelo `taxonomy_score_cap` para reduzir viés decorrente da fragmentação histórica em muitos grupos.

## CLI

O CLI empacotado é deliberadamente pequeno:

```bash
nutev --version
nutev providers
```

A coleta e o ranking permanecem expostos como ferramentas do repositório para manter configuração, entradas e outputs visíveis.

## Solução de problemas

### `Nenhum master de coleta encontrado`

A coleta geral não terminou com um master utilizável. Rode novamente e deixe `[1/3]` concluir.

### `Guardrail failure: SHA-256 mismatch`

Um master mudou depois de o manifesto ter sido criado ou o arquivo está corrompido. O engine interrompe de propósito. Não edite o master manualmente; refaça a coleta ou restaure o arquivo correspondente ao hash registrado.

### Registros em `reference_quarantine.jsonl`

O item não tinha origem suficiente para ranking estrito. Verifique provider, título e DOI/PMID/PMCID/URL no dado-fonte. Não preencha identificadores por suposição.

### HTTP `401`/`403` no LILACS/BVS ou SciELO

A interface pública recusou a automação. A `main` atual registra esse estado como `unavailable` e pode continuar com as demais fontes.

Isso não significa que a base não contenha literatura relevante.

### Mensagens do VS Code após o sucesso

Mensagens como:

```text
StorageMainService
Unknown channel
DeprecationWarning
```

podem aparecer porque o Windows abriu o Markdown no VS Code. Elas não são, por si só, erros do NutEV Reference Engine.

Leia primeiro o resumo dos três códigos de saída mostrado pelo engine.

### `Deseja finalizar o arquivo em lotes (S/N)?`

É uma mensagem do CMD normalmente provocada por `Ctrl+C` durante um `.bat/.cmd`. Se `SUCESSO: ranking de referencias gerado.` já apareceu, o ranking daquela execução já foi produzido.

## O que este projeto não é

O NutEV Reference Engine não é:

- um sistema automático de revisão sistemática, scoping review ou PRISMA;
- um avaliador de risco de viés ou qualidade metodológica;
- um mecanismo de recomendação clínica;
- um substituto para triagem, leitura crítica ou julgamento do pesquisador;
- uma simulação de bases licenciadas indisponíveis;
- um distribuidor de textos completos protegidos;
- um gerador de referências por IA.

## Desenvolvimento

```bash
python -m pip install -e ".[dev]"
PYTHONPATH=src python -m pytest -q nutev_tests
python -m compileall -q src tools nutev_tests
ruff check src tools nutev_tests --select F,E9
```

O CI atual inclui testes em Python 3.12 e 3.13, Windows smoke, contrato específico de guardrails, type checking, lint/compile, security scan, dependency review, CodeQL e validação de artefatos de release.

Veja [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Documentação

- [`docs/POP_USO_NUTEV_REFERENCE_ENGINE.md`](docs/POP_USO_NUTEV_REFERENCE_ENGINE.md) — procedimento operacional padrão completo.
- [`docs/AUDITABILITY_AND_GUARDRAILS.md`](docs/AUDITABILITY_AND_GUARDRAILS.md) — política fail-closed, quarentena, hashes e procedimento de auditoria.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitetura, fluxo de dados e pesos reais do ranking.
- [`docs/SEARCH_PROVIDERS.md`](docs/SEARCH_PROVIDERS.md) — providers, limites, credenciais e estados de falha.
- [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md) — limitações conhecidas e fronteiras de interpretação.
- [`docs/VALIDATED_WINDOWS_RUN_2026-08-18.md`](docs/VALIDATED_WINDOWS_RUN_2026-08-18.md) — evidência de uma execução real bem-sucedida.
- [`docs/PROVENANCE_AND_LICENSE.md`](docs/PROVENANCE_AND_LICENSE.md) — proveniência e fronteira de licenciamento.
- [`docs/RELEASE_V1_0_0.md`](docs/RELEASE_V1_0_0.md) — release estável v1.0.0.
- [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md) — checklist para futuras releases.
- [`docs/ZENODO_SETUP.md`](docs/ZENODO_SETUP.md) — regra GitHub/Zenodo/DOI.
- [`docs/REFERENCE_ENGINE_CLEANUP_AUDIT.md`](docs/REFERENCE_ENGINE_CLEANUP_AUDIT.md) — auditoria histórica da limpeza do repositório.

## Release, DOI e citação

A versão estável publicada é **v1.0.0**, lançada em 18/08/2026.

- Release commit: `5728d79b05e618897f01ba93886a17584c9f215f`
- Git tag: `v1.0.0`
- Zenodo record: `21998607`
- DOI: [`10.5281/zenodo.21998607`](https://doi.org/10.5281/zenodo.21998607)
- Citation metadata: `CITATION.cff`
- Archive metadata: `.zenodo.json`

A tag `v1.0.0` é imutável. A branch `main` contém correções, documentação e guardrails pós-release; isso não altera o snapshot arquivado da versão 1.0.0.

Para reproduzir especificamente o snapshot publicado:

```bash
git checkout v1.0.0
```

Para usar as correções pós-release mais recentes:

```bash
git checkout main
git pull --ff-only origin main
```

## Licença e proveniência

MIT. Consulte `LICENSE`, `NOTICE.md` e [`docs/PROVENANCE_AND_LICENSE.md`](docs/PROVENANCE_AND_LICENSE.md).

A árvore atual preserva a atribuição de proveniência do projeto upstream descrito nesses arquivos, sem afirmar um commit de derivação que não foi independentemente estabelecido.
