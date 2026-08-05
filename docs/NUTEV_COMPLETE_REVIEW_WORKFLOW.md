# Fluxo científico integrado do NutEV Evidence Engine

## Visão geral

O NutEV Evidence Engine utiliza um único fluxo auditável para busca, seleção e síntese documental:

```text
Busca → Corpus → Triagem → Texto completo → Extração → Qualidade → Síntese
```

A busca é global e independente dos artigos. Depois da deduplicação, cada documento pode receber decisões diferentes nos Artigos 1–5 sem ser duplicado fisicamente no corpus.

## Etapas operacionais

1. **Escrever a pesquisa global** — informar a pergunta, os conceitos e os filtros opcionais.
2. **Visualizar as expressões** — conferir a tradução da consulta para PubMed, Europe PMC, Crossref e OpenAlex.
3. **Salvar uma versão** — criar uma versão imutável, classificada como `PILOT`, `FORMAL` ou `SUPPLEMENTARY`.
4. **Executar a versão congelada** — preservar expressão, filtros, base, status, contagem, checkpoint e snapshot.
5. **Construir o corpus mestre** — validar SHA-256, normalizar os registros e deduplicar por identificadores fortes.
6. **Resolver possíveis duplicatas** — decidir manualmente pares semelhantes por título e ano.
7. **Fazer triagem por artigo** — decidir `INCLUDE`, `EXCLUDE` ou `MAYBE` para cada Artigo 1–5.
8. **Registrar o texto completo** — documentar disponibilidade, fonte, arquivo local e SHA-256.
9. **Avaliar elegibilidade** — decidir a inclusão final e registrar o motivo de toda exclusão.
10. **Extrair dados** — usar campos comuns e campos específicos configuráveis por artigo.
11. **Avaliar qualidade metodológica** — selecionar e aplicar um instrumento adequado ao tipo documental.
12. **Exportar a matriz final** — produzir matrizes, comparações, julgamentos e manifestos reprodutíveis.

## Princípios de governança

- A decisão humana é autoritativa.
- Versões de busca, snapshots, corpus e exports são imutáveis.
- Correções humanas criam novas revisões e não apagam o histórico.
- Um documento pode atender a vários artigos.
- O texto completo é recuperado uma vez por documento.
- A extração e a avaliação metodológica são independentes por artigo.
- Título e ano nunca causam deduplicação automática.
- Buscas piloto permanecem auditáveis, mas não alimentam as contagens oficiais do PRISMA.
- Arquivos locais são verificados por SHA-256 antes das etapas dependentes.

## Extração estruturada

### Campos bibliográficos compartilhados

A matriz final preserva, quando disponíveis:

- `document_id`;
- título;
- autores;
- ano e data de publicação;
- DOI, PMID e PMCID;
- periódico ou organização;
- país e idioma;
- tipo documental;
- URL;
- caminho do texto completo;
- SHA-256 do artefato.

### Campos metodológicos comuns

O sistema inicia com campos comuns para objetivo, desenho, população, amostra, contexto, intervenção ou exposição, comparador, duração, desfechos, instrumentos, análise estatística, resultados, limitações, conflitos de interesse e financiamento.

### Campos específicos por artigo

O pesquisador pode criar revisões de campos para cada Artigo 1–5 com:

- chave estável;
- rótulo;
- descrição;
- tipo;
- opções permitidas;
- obrigatoriedade;
- regras de validação;
- ordem de apresentação;
- estado ativo ou inativo.

Tipos aceitos:

```text
TEXT
LONG_TEXT
INTEGER
FLOAT
BOOLEAN
DATE
SINGLE_SELECT
MULTI_SELECT
JSON
```

### Dupla extração

Cada combinação `document_id + article_id` aceita uma extração do `REVIEWER_1` e outra do `REVIEWER_2`.

O sistema compara campo a campo:

- `AGREED` — os dois valores são iguais;
- `DIVERGENT` — os valores diferem;
- `MISSING_REVIEWER_1`;
- `MISSING_REVIEWER_2`;
- `MISSING_BOTH`.

Campos divergentes exigem adjudicação. A decisão final é adicionada ao ledger sem modificar as extrações originais.

## Avaliação metodológica

A seleção do instrumento é humana ou baseada em sugestão revisável. O sistema não transforma o tipo documental em decisão automática.

Versões iniciais configuráveis incluem:

- AGREE II;
- AMSTAR 2;
- RoB 2;
- ROBINS-I;
- JBI/CASP qualitativo;
- AACODS;
- credibilidade e transparência da fonte.

Essas configurações representam estruturas de registro. Elas não redistribuem formulários protegidos e não substituem o manual oficial de cada instrumento.

A avaliação registra, por domínio:

- julgamento;
- justificativa;
- revisor;
- posição na dupla;
- revisão;
- data e hora.

Divergências entre os dois revisores são adjudicadas e preservadas como uma nova revisão final.

## Saídas da matriz final

```text
<build_dir>/evidence_matrix/<session_id>/<export_id>/
├── extraction_schema.csv
├── extraction_submissions.csv
├── extraction_comparison.csv
├── final_evidence_matrix.csv
├── quality_assessments.csv
├── final_quality_matrix.csv
├── extraction_quality_summary.json
└── evidence_matrix_manifest.json
```

O manifesto inclui os caminhos, os hashes SHA-256, as contagens e as regras de governança da exportação.

## Uso no dashboard

Abra a página **Search Strategy** e siga os blocos numerados. As etapas posteriores aparecem somente quando existem dados elegíveis das etapas anteriores.

O painel informa:

- documentos incluídos;
- extrações pendentes;
- avaliações metodológicas pendentes;
- divergências;
- decisões finais;
- caminhos dos artefatos exportados.

## Execução no Windows

```powershell
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git
cd NutEV-Evidence-Engine
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dashboard,platform]"
nutev dashboard --project-root .\project_output --port 8501
```

Testes:

```powershell
$env:PYTHONPATH="src"
python -m pytest -q nutev_tests
ruff check src nutev_tests
```

## Limites científicos

- O software não decide a inclusão científica sem revisor humano.
- A sugestão de instrumento não equivale à escolha metodológica final.
- A concordância entre revisores não prova correção; ela apenas elimina a necessidade de adjudicação naquele campo.
- A matriz final é um artefato de pesquisa, não uma recomendação clínica.
- A interpretação e a síntese ainda dependem da equipe científica.
