# NutEV Evidence Engine — Lifestyle Nutrition

Infraestrutura computacional reprodutível para **identificação, proveniência, normalização, deduplicação, recuperação de texto, OCR, classificação assistida e revisão humana** de evidências em Nutrição do Estilo de Vida.

O repositório apoia o projeto NutEV/NutMEV e a execução metodológica do Artigo 1. Ele **não é um Clinical Decision Engine** e não transforma resultados computacionais em recomendação clínica final.

![status](https://img.shields.io/badge/status-alpha-orange)
![python](https://img.shields.io/badge/python-3.12%E2%80%933.13-blue)
![license](https://img.shields.io/badge/license-MIT-green)
[![DOI](https://img.shields.io/badge/DOI-pendente%20de%20verifica%C3%A7%C3%A3o%20Zenodo-lightgrey)](docs/ZENODO_SETUP.md)

## Estado da versão

| Estado | Identidade |
|---|---|
| Última release pública/citável | `0.2.0` / `v0.2.0` |
| Desenvolvimento atual | `0.3.0.dev1` |
| Maturidade científica | `alpha` |
| Nova release/DOI Zenodo | ainda não publicada/verificada |

Não existe uma `v0.3.0` publicada. Tags/releases históricas são imutáveis.

## Arquitetura científica canônica

O runtime antigo de buscas independentes por `busca1`, `busca2a`, `busca2b` e `a3` foi aposentado. O caminho científico atual é:

```text
UMA estratégia global
        ↓
versão imutável registrada
        ↓
renderização por provider/base
        ↓
execução real + ledger + snapshots/hashes
        ↓
UM run científico
        ↓
UM corpus mestre
        ↓
normalização + deduplicação uma vez
        ↓
classificação / triagem por artigo
        ↓
full text / OCR
        ↓
extração / qualidade / síntese
        ↓
revisão humana
```

A associação com Artigos 1–5 acontece **depois da recuperação**. Um mesmo documento pode ser relevante para mais de um artigo sem ser pesquisado ou armazenado novamente.

## Caminho científico do Artigo 1

A ordem metodológica atual é:

1. **GF-02 — PILOT das buscas**: recall de sentinelas, ruído e equivalência das strings;
2. **GF-03 — PRESS**;
3. **GF-06 — janela temporal/filtros definitivos**;
4. **GF-07 — equipe, critérios e calibração da triagem humana**;
5. **GF-10 — FREEZE**;
6. busca formal;
7. corpus mestre;
8. triagem título/resumo;
9. texto completo;
10. extração/codebook, qualidade e síntese.

`nutev play` não pula esses gates. O modo automático completo é **PILOT-only** enquanto os gates formais ainda não estiverem registrados/autorizados no software.

## Instalação

Requer Python `>=3.12,<3.14`.

### Windows PowerShell

```powershell
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git
cd NutEV-Evidence-Engine
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dashboard,platform,documents]"
```

### macOS/Linux

```bash
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git
cd NutEV-Evidence-Engine
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dashboard,platform,documents]"
```

Guia completo: [`docs/RUN_LOCAL.md`](docs/RUN_LOCAL.md).

## Demo sem evidência real

```bash
nutev demo-data --project-root ./project_output_demo
nutev dashboard --project-root ./project_output_demo --port 8501
```

A demo usa dados sintéticos e **não é evidência científica**.

## Dashboard científico

```bash
nutev dashboard --project-root ./project_output_scientific --port 8501
```

No painel **Search Strategy**:

- construa a pesquisa global;
- revise as expressões por provider;
- registre uma versão imutável;
- execute somente o estado científico autorizado;
- construa o corpus mestre;
- siga para revisão humana/downstream.

Uma expressão mostrada na interface é apenas **gerada** até existir uma tentativa real registrada.

## ▶ NutEV PLAY

Um comando executa o pipeline computacional autorizado:

```bash
nutev play --project-root ./project_output_scientific
```

Para testar apenas busca + corpus:

```bash
nutev play --project-root ./project_output_scientific --metadata-only
```

O PLAY atual encadeia:

```text
estratégia PILOT registrada
        ↓
providers + snapshots + ledger
        ↓
corpus mestre + deduplicação
        ↓
resolução legal de full text
        ↓
download
        ↓
extração nativa / OCR quando necessário
        ↓
12_play/<play_id>/
```

Saídas incluem `play_summary.json`, checksum separado, relatório Markdown, provider report, full-text ledger, manifests de download/falha e extraction/OCR manifest.

O PLAY torna truncamento explícito. Se uma base informar mais resultados do que foram recuperados, a execução não pode ser descrita como exaustiva.

## Full text e OCR

A recuperação prioriza rotas legalmente acessíveis, incluindo PMCID/PMC, localizações OA declaradas por providers, Unpaywall e PMID→PMC quando aplicável. Paywalls não são contornados.

PDFs com camada de texto são extraídos diretamente. OCR é usado quando necessário e disponível. Falha de OCR/captura permanece registrada.

## Guias e fontes oficiais

```bash
nutev guides --project-root ./project_output_scientific --workers 4 --rate 1.0
```

Fontes oficiais/institucionais seguem trilha metodológica própria. Descoberta ao vivo não substitui um manifesto/marco amostral congelado para execução definitiva.

## Providers

O executor registrado atualmente suporta o conjunto formal implementado no software, com proveniência de expressão, tentativa, timestamp, contagem, limite/paginação, snapshot e hash. Scopus e Web of Science permanecem rotas licenciadas/manuais até existir integração autorizada; não devem ser representadas silenciosamente como executadas.

O conector chamado SciELO no runtime atual usa Crossref com prefixo DOI `10.1590`; não é uma busca nativa/completa da plataforma SciELO.

## Construtor de estratégia

```bash
nutev strategy --spec examples/picos.json --out project_output_scientific/07_logs/search_strategy.json
```

Esse comando **gera** expressões; não é evidência de execução.

## Princípios obrigatórios

- query gerada **não é** query executada;
- `execution_status` **não é** `scientific_readiness`;
- PILOT **não é** busca formal/PRISMA;
- capacidade técnica de provider não implica inclusão no protocolo;
- timeout, 403, rate limit, credencial ausente e falha de OCR não viram “zero resultados”;
- decisões `INCLUDE`, `EXCLUDE`, PRESS, adjudicação e FREEZE permanecem humanas quando exigidas;
- `RecommendationCandidate` não é recomendação clínica final.

Normas: [`AGENTS.md`](AGENTS.md), [`docs/SCIENTIFIC_GOVERNANCE.md`](docs/SCIENTIFIC_GOVERNANCE.md) e [`docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md`](docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md).

## Testes e gates

```bash
PYTHONPATH=src python -m pytest -q nutev_tests
```

A CI canônica inclui Python 3.12/3.13, Windows smoke, cobertura, compileall/Ruff, mypy crítico, CodeQL, security scan, dependency review e validação de wheel/sdist.

## Segurança e copyright

- nunca comite secrets/tokens/`.env`;
- não redistribua PDFs/textos protegidos sem direito explícito;
- não armazene dados clínicos/pessoais identificáveis;
- prefira metadados, DOI, URLs oficiais e artefatos legalmente redistribuíveis;
- release/Zenodo não deve incluir outputs locais com full texts protegidos.

Ver [`docs/COPYRIGHT_AND_FULL_TEXT_POLICY.md`](docs/COPYRIGHT_AND_FULL_TEXT_POLICY.md) e [`docs/DATA_GOVERNANCE.md`](docs/DATA_GOVERNANCE.md).

## Release, Zenodo e proveniência

A última release pública/citável permanece `v0.2.0`. A próxima release só deve ser criada a partir de um SHA revisado, com metadados reconciliados e gates verdes.

O projeto evoluiu de uma base histórica Local Deep Research/LearningCircuit. O runtime herdado foi removido da árvore atual, mas atribuição/licença/proveniência não devem ser apagadas sem auditoria. O gate está documentado em `NOTICE.md`, `docs/PROVENANCE_AND_LICENSE.md` e na issue #1014.

Nenhum DOI novo deve ser inventado ou escrito no projeto antes de existir registro público real no Zenodo.

## Documentação principal

- [`docs/PLAY.md`](docs/PLAY.md)
- [`docs/RUN_LOCAL.md`](docs/RUN_LOCAL.md)
- [`docs/SCIENTIFIC_GOVERNANCE.md`](docs/SCIENTIFIC_GOVERNANCE.md)
- [`docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md`](docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md)
- [`docs/CODE_HYGIENE_CURRENT.md`](docs/CODE_HYGIENE_CURRENT.md)
- [`docs/RELEASE_PLAN_v0.3.0.md`](docs/RELEASE_PLAN_v0.3.0.md)
- [`docs/ZENODO_SETUP.md`](docs/ZENODO_SETUP.md)
- [`NOTICE.md`](NOTICE.md)

## Licença

Distribuição do repositório sob MIT, preservando a atribuição histórica aplicável e a fronteira de proveniência documentada.
