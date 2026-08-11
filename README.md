# NutEV Evidence Engine — Lifestyle Nutrition

Infraestrutura computacional reprodutível para **identificação, proveniência, normalização, deduplicação, classificação, curadoria assistida e revisão humana** de evidências em Nutrição do Estilo de Vida.

O repositório apoia a camada de evidências do projeto NutEV/NutMEV e a execução metodológica do Artigo 1. Ele **não é um motor de decisão clínica**, não prescreve e não transforma `RecommendationCandidate` em recomendação clínica final.

![status](https://img.shields.io/badge/status-alpha-orange)
![python](https://img.shields.io/badge/python-3.12%E2%80%933.13-blue)
![license](https://img.shields.io/badge/license-MIT-green)
[![DOI](https://img.shields.io/badge/DOI-pendente%20de%20verifica%C3%A7%C3%A3o%20Zenodo-lightgrey)](docs/ZENODO_SETUP.md)

## Identidade da versão

| Estado | Identidade |
|---|---|
| Última release pública/citável | `0.2.0` / tag `v0.2.0` |
| Árvore de desenvolvimento atual | `0.3.0.dev1` |
| Maturidade científica | `alpha` |
| DOI Zenodo | não configurado/verificado para nova release |

A release `v0.2.0` e as tags históricas são objetos imutáveis. A árvore `main` permanece em desenvolvimento e **não existe uma `v0.3.0` publicada**.

A arquitetura atualmente validada inclui **uma busca global**, proveniência `generated`/`executed`, corpus mestre, curadoria/revisão humana e validação reprodutível do artefato de software. Isso não implica que triagem humana, manuscrito ou recomendações clínicas estejam concluídos.

Quando houver decisão futura de publicar uma nova release, versão do pacote, tag proposta, `CITATION.cff`, `.zenodo.json`, CHANGELOG, README e release notes deverão ser reconciliados novamente no mesmo SHA candidato e todos os gates deverão executar nesse SHA. Ver [`AGENTS.md`](AGENTS.md) e [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md).

## Princípios científicos obrigatórios

- query gerada **não é** query executada;
- `execution_status` **não é** `scientific_readiness`;
- `manuscript_ready` requer gates humanos explícitos;
- capacidade técnica de provider não implica inclusão no protocolo;
- erros, timeout, rate limit ou credencial ausente permanecem visíveis;
- `RecommendationCandidate` não é recomendação final;
- Evidence Engine não é Clinical Decision Engine;
- decisões de inclusão, exclusão, codificação e interpretação científica permanecem humanas.

A política normativa está em [`AGENTS.md`](AGENTS.md), [`docs/SCIENTIFIC_GOVERNANCE.md`](docs/SCIENTIFIC_GOVERNANCE.md) e [`docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md`](docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md).

# Arquitetura canônica da pesquisa

## Uma busca global, não uma busca por artigo

O fluxo científico canônico é:

```text
UMA estratégia global de pesquisa
            ↓
versão FORMAL e imutável da estratégia
            ↓
renderização específica por base/provider
            ↓
execução real + attempt-level ledger
            ↓
UM run científico
            ↓
UM corpus mestre
            ↓
normalização + deduplicação uma vez
            ↓
classificação / triagem por artigo
            ↓
full text / extração / qualidade / síntese
            ↓
revisão humana
```

Os identificadores históricos como `busca1`, `busca2a`, `busca2b`, `a3` ou `a4_framework` ainda podem existir em módulos de compatibilidade, scoring ou análises downstream. **Eles não significam que a pesquisa científica principal deva ser executada como várias buscas temáticas independentes.**

A mesma estratégia global pode ser traduzida para sintaxes diferentes em PubMed, Europe PMC, Crossref e OpenAlex. Isso continua sendo **uma estratégia científica**, executada em múltiplas fontes e registrada sob uma identidade de execução.

## Tracks metodológicos

O Artigo 1 mantém métodos de identificação diferentes quando a natureza da fonte exige:

- **Track A — bases indexadas/congeladas:** expressão exata por base, timestamps, paginação/limites, contagens, snapshots/hashes e ledger de tentativas;
- **Track B — fontes oficiais/institucionais/guidelines:** manifesto de organizações/fontes, regras de navegação, URLs finais, captura/download legalmente permitido, hashes e revisão humana;
- **Track C — descoberta suplementar:** somente quando explicitamente prevista pelo protocolo.

Esses tracks podem convergir para o corpus documental governado, mas não devem ser descritos como se tivessem o mesmo método amostral.

O conector chamado SciELO no runtime atual usa recuperação via Crossref escopada pelo prefixo DOI `10.1590`; não deve ser descrito como busca nativa e completa no SciELO.

# Instalação

O pacote requer Python **`>=3.12,<3.14`**. As versões canônicas de CI são Python 3.12 e 3.13.

## Windows PowerShell

```powershell
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git
cd NutEV-Evidence-Engine
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dashboard,platform,documents]"
```

Também existe o instalador assistido:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_windows.ps1
```

## macOS/Linux

```bash
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git
cd NutEV-Evidence-Engine
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dashboard,platform,documents]"
```

# Demo sem chave

A demonstração usa dados sintéticos e **não é evidência científica**:

```bash
nutev demo-data --project-root ./project_output_demo
nutev dashboard --project-root ./project_output_demo --port 8501
```

Abra:

```text
http://127.0.0.1:8501
```

API local opcional:

```bash
nutev serve --project-root ./project_output_demo --host 127.0.0.1 --port 8000
```

O workflow `release-artifact-validation` também constrói wheel/sdist, executa `twine check`, instala o wheel em ambiente virtual limpo, executa `pip check`, verifica a CLI e roda a demo zero-key a partir do artefato instalado.

# Como rodar a pesquisa canônica

## 1. Abra um projeto exclusivo

```bash
nutev dashboard --project-root ./project_output_scientific --port 8501
```

## 2. Abra **Search Strategy**

Use o **campo global único de pesquisa**. A pergunta/estratégia deve representar o protocolo científico global, não um artigo isolado.

O construtor permite revisar a renderização por provider e amplitude. Uma expressão mostrada na interface é apenas **gerada** até existir uma tentativa real registrada.

## 3. Salve uma versão FORMAL

Antes da execução científica:

- revise a estratégia;
- salve a versão no registro;
- marque o tipo como `FORMAL` quando metodologicamente aprovado;
- preserve versão, timestamp e identidade do responsável conforme o protocolo;
- não edite retrospectivamente a versão congelada.

## 4. Execute a versão registrada

Na área de execução, selecione a **versão congelada**. O executor deve usar a versão registrada, não o texto eventualmente deixado no formulário da interface.

A execução deve registrar, no mínimo:

- `run_id`;
- provider;
- expressão submetida;
- tentativa/status;
- timestamp;
- contagem;
- limite/paginação/truncamento;
- erro real, quando houver;
- snapshot/hash conforme o contrato.

## 5. Construa o corpus mestre

Após a execução:

```text
snapshots dos providers
        ↓
normalização
        ↓
deduplicação
        ↓
corpus mestre
```

Possíveis duplicatas não resolvidas de forma determinística devem permanecer visíveis para revisão humana.

## 6. Classifique por artigo depois da recuperação

A classificação/triagem por artigo acontece **sobre o corpus mestre**. Um mesmo documento pode ser relevante para mais de um artigo sem ser pesquisado ou armazenado novamente.

## 7. Continue para full text, extração e qualidade

Quando aplicável e legalmente permitido:

- recuperação/captura;
- full-text assessment;
- extração;
- OCR quando necessário e disponível;
- evidence matrix;
- quality assessment;
- filas de revisão humana.

Metadata-only não deve ser promovido silenciosamente a full text.

## Construtor CLI de estratégia

É possível gerar/auditar expressões a partir de um spec:

```bash
nutev strategy --spec examples/picos.json --out project_output_scientific/07_logs/search_strategy.json
```

Esse comando **gera** estratégia. Ele não é prova de que a expressão foi executada.

# Pipeline legado / compatibilidade

O comando genérico abaixo continua existindo para compatibilidade, testes e pilotos especializados:

```bash
nutev --project-root ./project_output_legacy --workstreams busca1 busca2a busca2b a3 --web-enabled
```

**Não use esse comando como representação da execução científica canônica de “uma busca global” do Artigo 1.** Para execução formal, use a estratégia global versionada + executor registrado + corpus mestre descritos acima e no contrato do Artigo 1.

# Guias e fontes oficiais

Documentos oficiais possuem trilha de aquisição própria. Para o pipeline de guias, quando metodologicamente apropriado:

```bash
nutev guides --project-root ./project_output_scientific --workers 4 --rate 1.0
```

Descoberta ao vivo não substitui um marco amostral/manifesto congelado. Para execução definitiva, preserve manifesto/configuração, data, tentativa, URL e hash dos artefatos quando aplicável.

# Proveniência de busca

Artefatos canônicos em `07_logs` incluem equivalentes atuais de:

- `querypack_generated.json/.csv` — espaço gerado;
- `provider_querypack_generated.json/.csv` — renderização gerada;
- `provider_performance.csv` — tentativas terminais;
- `query_execution_ledger.json/.csv` — evidência canônica do que foi tentado;
- `querypack_executed.json/.csv` — compatibilidade construída a partir de tentativas reais;
- `provider_querypack_executed.json/.csv` — visão executada por provider;
- `run_summary.json` — resumo computacional e readiness separado.

**Nunca use um querypack gerado para afirmar que uma busca foi executada.**

# Outputs

Camadas principais:

- `02_metadata` — metadados e artefatos canônicos de claims/auditoria;
- `06_tables` — matrizes e relatórios analíticos derivados;
- `07_logs` — ledgers, eventos, snapshots, resumos e proveniência;
- `10_curated` — outputs curados e priorização operacional.

Artefatos de claims/auditoria canônicos ficam em `02_metadata`, incluindo:

- `NUTEV_EVIDENCE_CLAIMS.csv`;
- `NUTEV_CLAIM_EVALUATIONS.csv`;
- `NUTEV_CONFLICTS.csv`;
- `NUTEV_RECOMMENDATION_CANDIDATES.csv`.

`is_prioritized`, relevance score e `RecommendationCandidate` são estados computacionais/operacionais e não decisões científicas finais.

# Testes e gates

Suite canônica:

```bash
PYTHONPATH=src python -m pytest -q nutev_tests
```

Os gates de PR/release incluem, conforme os workflows atuais:

- Python 3.12 e 3.13;
- cobertura com threshold bloqueante;
- Windows smoke/zero-key;
- `compileall`;
- Ruff bloqueante;
- mypy do núcleo crítico de proveniência;
- CodeQL;
- security scan / Gitleaks / hygiene;
- dependency review realmente executado;
- build wheel/sdist + `twine check` + clean install + zero-key do wheel.

Um workflow verde só é evidência de PASS para o SHA/ref que realmente executou aquele check.

# Segurança, copyright e revisão humana

- não comite secrets, tokens, `.env`, private keys ou URLs autenticadas;
- não armazene dados clínicos/pessoais identificáveis;
- não redistribua PDFs/textos protegidos sem direito explícito;
- prefira DOI, metadados, URLs oficiais e trechos mínimos permitidos;
- falha de OCR/captura deve permanecer registrada, não virar documento vazio;
- IA/LLM auxilia, mas não substitui inclusão/exclusão/coding/adjudicação humana.

Ver [`docs/COPYRIGHT_AND_FULL_TEXT_POLICY.md`](docs/COPYRIGHT_AND_FULL_TEXT_POLICY.md), [`docs/DATA_GOVERNANCE.md`](docs/DATA_GOVERNANCE.md) e [`docs/AI_USE_AND_HUMAN_OVERSIGHT.md`](docs/AI_USE_AND_HUMAN_OVERSIGHT.md).

# Documentação principal

- [`AGENTS.md`](AGENTS.md)
- [`docs/SCIENTIFIC_GOVERNANCE.md`](docs/SCIENTIFIC_GOVERNANCE.md)
- [`docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md`](docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md)
- [`docs/RUN_LOCAL.md`](docs/RUN_LOCAL.md)
- [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md)
- [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md)
- [`docs/SEARCH_PROVIDERS.md`](docs/SEARCH_PROVIDERS.md)
- [`docs/ZENODO_SETUP.md`](docs/ZENODO_SETUP.md)
- [`NOTICE.md`](NOTICE.md)

# Citação

A última release publicada/citável continua sendo **`v0.2.0`**. `CITATION.cff` e `.zenodo.json` descrevem essa release pública enquanto a `main` permanece em desenvolvimento (`0.3.0.dev1`).

ORCID, afiliação, data de release e DOI devem ser incluídos somente após confirmação/verificação real.

# Licença e proveniência

Licença: MIT. O projeto evoluiu a partir de uma base histórica Local Deep Research / LearningCircuit; o runtime herdado foi removido, mas a atribuição e proveniência permanecem documentadas em [`NOTICE.md`](NOTICE.md) e no histórico Git.
