# NutEV **Evidence** Engine — Lifestyle Nutrition

Infraestrutura computacional reprodutível que **identifica, organiza, deduplica,
classifica e audita** documentos científicos e oficiais de Nutrição do Estilo de
Vida, produzindo matrizes de extração e filas de revisão humana para apoiar uma
**revisão de escopo** (Artigo 1). É a camada de **evidência** do projeto
NutEV/NutMEV — **não** é o motor de decisão clínica (ver
[Escopo e o que este software NÃO é](#escopo-e-o-que-este-software-não-é)).

![status](https://img.shields.io/badge/status-alpha-orange)
![python](https://img.shields.io/badge/python-3.12%E2%80%933.13-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![tests](https://img.shields.io/badge/tests-nutev__tests-informational)
![science](https://img.shields.io/badge/output-RecommendationCandidate%20(n%C3%A3o%20final)-red)
<!-- TODO: após o depósito no Zenodo (docs/ZENODO_SETUP.md), troque o badge abaixo
     pelo badge de DOI real fornecido pelo Zenodo. -->
[![DOI](https://img.shields.io/badge/DOI-pendente%20(Zenodo)-lightgrey)](docs/ZENODO_SETUP.md)

> ⚠️ **Status científico:** software de apoio à pesquisa, em estágio **alpha**.
> A release citável reconciliada está sendo preparada como **versão `0.2.0` / tag
> `v0.2.0`**. As tags históricas `v0.1.0`–`v0.1.8` são preservadas e não serão
> reutilizadas. `alpha` descreve a maturidade científica e não uma segunda versão
> concorrente. Distingue claramente **software**, **pesquisa**, **evidência** e
> **recomendação clínica**. Uma saída computacional (`RecommendationCandidate`)
> **não** é recomendação clínica final. Toda candidata exige revisão humana,
> adjudicação metodológica e vínculo documental verificável. Nenhuma saída
> automática é apresentada como recomendação final. Ver
> [`docs/SCIENTIFIC_GOVERNANCE.md`](docs/SCIENTIFIC_GOVERNANCE.md).

## O que o sistema faz / não faz

**Faz:** documenta estratégias de busca; localiza metadados e documentos oficiais
públicos; organiza, deduplica e classifica registros; extrai claims com localizador
verificável; produz matrizes de evidência e filas de revisão humana; gera
recomendações **candidatas** rastreáveis.

**Não faz:** diagnóstico, prescrição individual, decisão clínica automática ou
recomendação final; não redistribui PDFs/textos protegidos; não usa LLM para
aprovar recomendações; não armazena dados pessoais/clínicos.

## Escopo e o que este software NÃO é

O projeto NutEV/NutMEV tem **dois softwares distintos**, com nomes parecidos. É
importante não confundi-los:

| | **NutEV Evidence Engine** (ESTE repositório) | **Decision Engine** (NÃO está aqui) |
|---|---|---|
| Apoia | a **revisão de escopo** (Artigo 1) | o **instrumento clínico** |
| Faz | busca, deduplicação, classificação de documentos, matrizes de extração | z-score intraindividual, AR(1), regra de acionamento |
| Usuário | o **pesquisador** | o **nutricionista** |
| Saída | documentos organizados e `RecommendationCandidate` (candidatas) | apoio à decisão clínica |

**Este repositório NÃO contém, NÃO executa e NÃO distribui o motor de decisão
clínica (*Decision Engine*).** Ele não produz recomendação clínica: as saídas do
tipo `RecommendationCandidate` são **candidatas** sujeitas a adjudicação humana e
**não** constituem recomendação final. Todas as decisões de inclusão, exclusão,
codificação e interpretação são **humanas**. Ver
[`docs/SCIENTIFIC_GOVERNANCE.md`](docs/SCIENTIFIC_GOVERNANCE.md) e
[`docs/CODE_AVAILABILITY.md`](docs/CODE_AVAILABILITY.md).

## Uso público para pesquisa

Este repositório é público e pode ser utilizado por estudantes, pesquisadores, nutricionistas e equipes acadêmicas para apoiar pesquisas relacionadas à Nutrição do Estilo de Vida, qualidade da dieta, guias alimentares, diretrizes clínicas, padrões alimentares, competências alimentares, adesão e implementação.

Usos previstos:

- construir e documentar estratégias de busca;
- localizar metadados e documentos oficiais de acesso público;
- organizar resultados de diferentes fontes;
- deduplicar e classificar registros;
- extrair trechos e claims para conferência humana;
- produzir matrizes de evidências e filas de revisão;
- apoiar revisões de escopo, análises documentais e projetos metodológicos.

O sistema não fornece diagnóstico, prescrição individual, decisão clínica automática ou recomendação final. Resultados devem ser conferidos nas fontes originais e avaliados por revisores humanos.

### Uso responsável

- respeite licenças, direitos autorais e termos de uso das fontes;
- não publique PDFs protegidos ou textos integrais sem autorização;
- prefira compartilhar metadados, URLs oficiais, DOI e trechos estritamente necessários à auditoria;
- não envie dados pessoais, prontuários ou informações identificáveis;
- nunca inclua chaves de API, tokens ou credenciais em commits;
- informe a versão do código, a data da execução, as fontes consultadas e os critérios de seleção;
- descreva qualquer uso de modelos de linguagem e mantenha revisão humana documentada.

### Como contribuir

Contribuições podem ser propostas por issue ou pull request. São especialmente úteis:

- correções de termos e traduções da taxonomia;
- inclusão de fontes oficiais verificáveis;
- testes reprodutíveis;
- melhorias de documentação;
- correções de bugs;
- novos exportadores que preservem rastreabilidade;
- exemplos públicos sem material protegido e sem dados pessoais.

Toda contribuição científica deve indicar a justificativa metodológica, a fonte e o impacto esperado. Alterações não devem transformar recomendações candidatas em recomendações finais automáticas.

## Visão geral

O projeto organiza uma arquitetura científica local para apoiar a qualificação de doutorado e o desenvolvimento do Protocolo Dietético NutEV/NutMEV. Ele inclui:

- CLI principal `nutev`;
- dashboard local;
- API local;
- demo data;
- pipeline de busca, classificação, download e extração;
- Global Watch;
- Audit Engine;
- Scientific Rigor Layer;
- Human Review and Adjudication.

## Runtime canônico

Toda a arquitetura do NutEV/NutMEV está em:

```text
src/nutev
```

O repositório evoluiu a partir de uma base histórica `local-deep-research`
(Local Deep Research, MIT © LearningCircuit). Esse motor herdado **foi removido**
da árvore do projeto; sua proveniência e atribuição são preservadas em
[`NOTICE.md`](NOTICE.md) e no histórico Git. O núcleo `src/nutev` não depende do
runtime herdado removido.

## Instalação rápida

### Windows PowerShell

```powershell
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git
cd NutEV-Evidence-Engine
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dashboard,platform]"
```

### macOS/Linux

```bash
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git
cd NutEV-Evidence-Engine
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dashboard,platform]"
```

O projeto requer Python `>=3.12,<3.14` (Python 3.12 e 3.13 são as versões declaradas/testadas pela CI canônica).

## Demonstração sem chave (nem API paga, nem dados reais)

O primeiro exemplo funciona **sem** OpenAI, Google, SerpAPI, Brave, dados reais ou
PDFs protegidos:

```bash
python -m venv .venv
python -m pip install -e ".[dashboard]"
nutev demo-data --project-root ./project_output_demo
nutev dashboard --project-root ./project_output_demo
```

Os dados gerados são **sintéticos** (demonstração, **não** evidência). Detalhes em
[`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md).

Para ler **PDFs escaneados** (imagem, sem camada de texto) basta o extra
`documents` (que já inclui o **PyMuPDF**, via pip, sem instalar nada no sistema)
e o programa `tesseract`. O `poppler` é opcional. Sem OCR configurado o NutEV
não trava: avisa o que instalar e marca esses documentos como
`pdf_needs_ocr_setup` no `run_summary.json`. Passo a passo (inclusive Windows)
em [`docs/OCR_SETUP.md`](docs/OCR_SETUP.md).

## Demo

```bash
nutev demo-data --project-root ./project_output_demo
nutev dashboard --project-root ./project_output_demo --port 8501
```

Depois acesse:

```text
http://127.0.0.1:8501
```

API local:

```bash
nutev serve --project-root ./project_output_demo --host 127.0.0.1 --port 8000
```

URLs:

- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/docs`

## Primeiro piloto real

```bash
nutev --project-root ./project_output_pilot --workstreams busca1 busca2a busca2b a3 --web-enabled
nutev pilot-report --project-root ./project_output_pilot
nutev dashboard --project-root ./project_output_pilot --port 8501
```

Variáveis úteis para integrações bibliográficas:

```bash
export NCBI_EMAIL="seu-email@exemplo.com"
export NCBI_API_KEY="sua-chave-ncbi"
export CROSSREF_MAILTO="seu-email@exemplo.com"
export OPENALEX_MAILTO="seu-email@exemplo.com"
```

Nunca coloque chaves de API no GitHub, em logs ou em outputs científicos.

## Outputs esperados

Camadas principais em `project_output_*`:

- `02_metadata`: metadados e artefatos canônicos de claims/auditoria usados por dashboard/API/exportadores;
- `06_tables`: matrizes derivadas, PRISMA, convergência, gaps e outras tabelas analíticas;
- `07_logs`: eventos, snapshots, resumo da execução e rastreabilidade;
- `10_curated`: metadados curados, documentos únicos e documentos operacionais priorizados.

Artefatos canônicos de auditoria esperados em `02_metadata`:

- `NUTEV_EVIDENCE_CLAIMS.csv`
- `NUTEV_CLAIM_EVALUATIONS.csv`
- `NUTEV_CONFLICTS.csv`
- `NUTEV_RECOMMENDATION_CANDIDATES.csv`

Matrizes derivadas e relatórios analíticos permanecem em `06_tables`.

Resumo final esperado em `07_logs/run_summary.json`:

- `records`
- `downloads_ok`
- `downloads_failed`
- `ocr_docs`
- `curated_unique_documents`
- `evidence_claims_total`
- `evidence_claims_supported`
- `evidence_claims_needs_review`
- `recommendation_candidates_total`
- `recommendation_candidates_ready_review`
- `recommendation_candidates_insufficient_evidence`
- `conflicting_evidence_total`

## Testes NutEV

Caminho padronizado:

```bash
PYTHONPATH=src python -m pytest -q nutev_tests
```

No Windows PowerShell:

```powershell
$env:PYTHONPATH="src"
python -m pytest -q nutev_tests
```

Para uma release citável, não reutilize contagens históricas: execute a suite no SHA candidato final e registre o resultado em [`docs/VALIDATION_REPORT.md`](docs/VALIDATION_REPORT.md).

## Limitações metodológicas

O sistema apoia identificação, classificação, auditoria e tradução preliminar de evidências. Ele **não substitui** revisão sistemática humana, avaliação de risco de viés, dupla checagem, adjudicação de conflitos, interpretação clínica ou decisão final do protocolo.

Recomendações candidatas podem receber estados como:

- `ready_for_human_review`
- `conflicting_evidence`
- `draft_needs_evidence`
- `insufficient_evidence`

Nenhum desses estados equivale a recomendação final.

## Documentação

- [`docs/AUDITORIA_CRUZADA_DRIVE_GITHUB_ARTIGO1.md`](docs/AUDITORIA_CRUZADA_DRIVE_GITHUB_ARTIGO1.md)
- [`docs/RUN_LOCAL.md`](docs/RUN_LOCAL.md)
- [`docs/VALIDATION_REPORT.md`](docs/VALIDATION_REPORT.md)
- [`docs/NUTEV_AUDIT_ENGINE.md`](docs/NUTEV_AUDIT_ENGINE.md)
- [`docs/NUTEV_CONTROL_CENTER.md`](docs/NUTEV_CONTROL_CENTER.md)
- [`docs/NUTEV_EVIDENCE_TO_PROTOCOL_FLOW.md`](docs/NUTEV_EVIDENCE_TO_PROTOCOL_FLOW.md)
- [`docs/NUTEV_PLATFORM_API.md`](docs/NUTEV_PLATFORM_API.md)
- [`docs/NUTEV_PROVIDER_SETTINGS.md`](docs/NUTEV_PROVIDER_SETTINGS.md)
- [`docs/REPOSITORY_STRUCTURE.md`](docs/REPOSITORY_STRUCTURE.md)
- [`docs/LEGACY_CLEANUP_AUDIT.md`](docs/LEGACY_CLEANUP_AUDIT.md)
- [`docs/LEGACY_DEPENDENCY_MAP.md`](docs/LEGACY_DEPENDENCY_MAP.md)

## Revisão humana

As decisões humanas são persistidas em `project_output/07_logs/human_review_decisions.csv` quando o fluxo de revisão está habilitado. Nenhuma recomendação deve ser considerada final sem revisão humana explícita, lastro documental e adjudicação metodológica.

## Estrutura dos artigos (numeração canônica) e mapa dos workstreams

A arquitetura da tese/pós-doutorado tem **cinco artigos**. Este repositório
(**Evidence Engine**) apoia os corpora documentais de **A1 e A2**; A3–A5 usam
outros métodos/projetos.

| | Artigo | Workstream no engine |
|---|---|---|
| **A1** | Revisão de escopo (guias + diretrizes) | `busca1` + `busca2a` |
| **A2** | Revisão integrativa (implementação/adesão) | `busca2b` |
| **A3** | Protocolo NutEV + pirâmide (Delphi) | — (fora do engine) |
| **A4** | Framework comportamental | `a4_framework` (alias do antigo `a3`) |
| **A5** | Instrumento CFD-8 + **Decision Engine** | — (outro projeto, não está aqui) |

O **Artigo 1** é: *“Domínios da Nutrição do Estilo de Vida em guias alimentares e
diretrizes clínicas: revisão de escopo e análise documental para subsidiar o
Protocolo NutEV.”* Seu corpus tem **três trilhas** metodologicamente distintas
(guias por marco amostral; diretrizes por bases indexadas + sites de sociedades;
materiais de implementação vinculados) — ver `docs/GREY_LITERATURE_POLICY.md` e
`docs/ARTICLE1_DOMAIN_CODING.md`.

> Nota de renumeração: o workstream histórico `a3` passou a ser **`a4_framework`**
> (aceito como alias; ambos funcionam). `busca2b` **deixou de ser "fora do
> corpus"** e agora é o corpus do **Artigo 2**.

Exemplo reproduzível (sem PDFs de terceiros):
[`examples/article1_pilot/`](examples/article1_pilot/).

## Ciência aberta, governança e copyright

- [`docs/SCIENTIFIC_GOVERNANCE.md`](docs/SCIENTIFIC_GOVERNANCE.md) — política científica.
- [`docs/AI_USE_AND_HUMAN_OVERSIGHT.md`](docs/AI_USE_AND_HUMAN_OVERSIGHT.md) — uso de IA e supervisão humana.
- [`docs/DATA_GOVERNANCE.md`](docs/DATA_GOVERNANCE.md) — governança de dados.
- [`docs/COPYRIGHT_AND_FULL_TEXT_POLICY.md`](docs/COPYRIGHT_AND_FULL_TEXT_POLICY.md) — copyright e texto integral.
- [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) — reprodutibilidade.
- [`docs/DEPENDENCY_ARCHITECTURE.md`](docs/DEPENDENCY_ARCHITECTURE.md) — arquitetura de dependências.
- [`docs/PUBLIC_RELEASE_AUDIT.md`](docs/PUBLIC_RELEASE_AUDIT.md) · [`docs/LEGACY_MIGRATION_PLAN.md`](docs/LEGACY_MIGRATION_PLAN.md)

Prefira compartilhar DOI, URL oficial, metadados e trechos mínimos permitidos.
Não redistribua PDFs protegidos. Não envie dados pessoais ou clínicos.

## Como citar

Use o arquivo [`CITATION.cff`](CITATION.cff). A versão preparada para a release citável reconciliada é `0.2.0`. ORCID e afiliação institucional permanecem **HUMAN INPUT REQUIRED** até confirmação humana; o DOI só deve ser inserido depois que o Zenodo arquivar a release exata.

Veja também [`docs/ZENODO_SETUP.md`](docs/ZENODO_SETUP.md) e [`docs/CODE_AVAILABILITY.md`](docs/CODE_AVAILABILITY.md).

## Como contribuir

Veja [`CONTRIBUTING.md`](CONTRIBUTING.md), [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)
e os templates em `.github/ISSUE_TEMPLATE/`. Toda contribuição científica deve
indicar justificativa metodológica, fonte e impacto esperado.

## Roadmap

Ver [`docs/ROADMAP.md`](docs/ROADMAP.md). Release citável reconciliada planejada:
**`v0.2.0`**, mantendo **alpha** como status de maturidade científica.

## Licença e proveniência

- Licença: **MIT** (ver [`LICENSE`](LICENSE)).
- O motor herdado `local_deep_research` foi **removido** da árvore, mas seu
  copyright original **© 2025 LearningCircuit** permanece atribuído em
  [`LICENSE`](LICENSE) — essa atribuição é preservada.
- Proveniência e fronteira entre código herdado e código NutEV:
  [`NOTICE.md`](NOTICE.md).

## NutEV/NutMEV robust search runtime

The canonical (and only) runtime is `src/nutev`. The inherited
`local_deep_research` package has been removed from the tree.

Scientific search does not depend on Google. PubMed, Europe PMC, OpenAlex, Crossref and official sources run through safe provider handling; provider failures are logged and the pipeline exports partial results instead of crashing. PubMed uses NCBI E-utilities with `usehistory=y`, `WebEnv`, `query_key`, paginated batches, retry/backoff and checkpoints under `07_logs/checkpoints/pubmed/`.

Configure local environment variables from `.env.example`. The most important PubMed settings are `NCBI_EMAIL`, optional `NCBI_API_KEY`, and `NCBI_TOOL=nutev_pipeline`. Google/SerpAPI keys are optional and are used only for gray-literature discovery.

More details: `docs/SEARCH_PROVIDERS.md` and `docs/PUBMED_TROUBLESHOOTING.md`.