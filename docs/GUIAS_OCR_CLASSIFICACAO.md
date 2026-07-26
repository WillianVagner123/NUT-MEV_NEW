# Guias → OCR → classificação A/B/C/D → frases-chave

Fluxo único que **pega todos os guias** do manifesto (~140 países), **lê o texto**
(OCR quando o PDF é escaneado), **classifica** nos domínios A/B/C/D e **extrai as
frases-chave** (as sentenças que sustentam cada domínio) + os termos mais
frequentes de cada documento.

Tudo é **assistivo** e entra em revisão humana — o sistema sugere e mede, não
decide. Não fura paywall nem fabrica texto.

## Rodar (na sua máquina, com internet + tesseract instalado)

```bash
# 1) instalar com o extra de documentos (traz PyMuPDF + pytesseract p/ OCR)
pip install -e ".[documents]"

# 2) rodar o fluxo completo (baixa, OCR, classifica, frases-chave)
nutev guides --project-root SAIDA

# opções úteis:
#   --discover-fao -> descobre TODOS os países AO VIVO no site da FAO
#                     (nome oficial + ano + os PDFs reais de cada guia),
#                     em vez do manifesto fixo. É o "pegar todos" de verdade.
#   --workers 8    -> 8 guias em paralelo (mais rápido; padrão 4)
#   --limit 20     -> processa só os 20 primeiros (teste rápido)
#   --offline      -> não baixa; só processa PDFs já em 03_corpus/03C_official_docs
#   --rate 1.0     -> 1s entre downloads por worker (mais educado com os servidores)
#   --report       -> gera o relatório de corpus (dedup fuzzy + clusters + heatmap)
#   --fresh        -> ignora o checkpoint e refaz tudo do zero
```

### Backend de OCR: Tesseract (padrão) ou olmOCR (opt-in)

Por padrão o OCR usa **Tesseract** — **determinístico e offline**, com cache
content-addressed (mesmo PDF + mesmas settings ⇒ mesmo texto, sem reprocessar).
É a escolha certa para reprodutibilidade.

Opcionalmente é possível usar o **olmOCR** (allenai/olmocr), um backend por
VLM (Qwen2.5-VL) que gera Markdown limpo de PDFs com **tabelas, equações e
layout multi-coluna**. Ative com `NUTEV_OCR_BACKEND=olmocr`. Observações
importantes:

- **Opt-in e com fallback seguro:** se o `olmocr` não estiver instalado, sem GPU,
  ou falhar, o fluxo **volta automaticamente para o Tesseract** — nunca quebra.
- **O NutEV não empacota pesos de modelo.** Você instala o `olmocr` por conta
  própria (precisa de GPU ≥12 GB) e é responsável por **revisar a licença dos
  pesos** do modelo. O nosso repositório só invoca o binário que você instalou.
- **Não é determinístico** (VLM). Trate a saída como **extração assistiva** (a
  revisão humana continua valendo) e registre isso no relato de reprodutibilidade.
  Trocar de backend invalida o cache de OCR automaticamente.
- Variáveis: `NUTEV_OCR_BACKEND=tesseract|olmocr`, `NUTEV_SKIP_OLMOCR=1` (força
  desligar), `NUTEV_OLMOCR_TIMEOUT` (segundos, padrão 600).

### Relatório de corpus (`--report`)

Precisa das dependências opcionais: `pip install -e ".[report]"` (scikit-learn +
matplotlib). Com `--report`, além das tabelas normais, o comando gera:

- **`NUTEV_GUIDES_REPORT.xlsx`** — abas: `DOCUMENTS` (com `cluster_id`,
  `dedup_group`, `dedup_is_duplicate_of`), `DUPLICATES` (pares parecidos com o
  score de similaridade) e `THEME_BY_CLUSTER` (média A/B/C/D por cluster).
- **`NUTEV_GUIDES_THEME_HEATMAP.png`** — mapa de calor dos domínios por cluster.

O que ele faz: **dedup por conteúdo** (TF-IDF + cosseno — pega traduções e
reedições que o dedup por identificador não pega) e **clusterização temática**
(KMeans). Sem as dependências instaladas, ele é **pulado com um aviso** (não
quebra o resto). Tudo assistivo, sob revisão humana.

### Descoberta FAO ao vivo (`--discover-fao`)

Sem essa flag, o comando usa o **manifesto fixo** de países. Com
`--discover-fao`, ele **rastreia o registro FBDG da FAO na hora**: acha *todos*
os países, lê **nome oficial** e **ano de publicação**, e pega os **arquivos de
download reais** de cada guia (um "source" por PDF). Depois cada arquivo passa
pelo mesmo fluxo: OCR → A/B/C/D → frases-chave → referência → checkpoint.

```bash
nutev guides --project-root SAIDA --discover-fao --workers 8
```

### Salvar & continuar (checkpoint)

Cada guia é gravado no **checkpoint** (`07_logs/guides_checkpoint.jsonl`) assim
que termina. Se a execução parar no meio (queda de rede, você fechou o terminal),
**é só rodar o mesmo comando de novo** — ele retoma de onde parou, sem
re-baixar nem re-OCR o que já foi feito. Para recomeçar do zero, use `--fresh`.

### Mais rápido

- **Paralelo**: `--workers N` baixa e faz OCR de N guias ao mesmo tempo (o
  tesseract roda como subprocesso, então as threads realmente paralelizam).
- **Não repete trabalho**: o checkpoint faz a re-execução pular o que já está
  pronto; PDFs com texto nativo nem passam pelo OCR.

> Windows: o `tesseract` precisa estar instalado (você já tem o 5.5.0). O
> renderizador de PDF é o **PyMuPDF** (vem no `pip install`, não precisa do
> poppler). Se ativar o venv der erro de permissão, use
> `.\.venv\Scripts\python.exe -m nutev guides --project-root SAIDA`.

### OCR (agora bem melhor)

O OCR antes rodava **só em inglês, sem preparo de imagem** — péssimo para guias em
português/espanhol. Agora:

- **multilíngue** por padrão (`por+eng+spa`); troque com a variável de ambiente
  `NUTEV_OCR_LANG` (ex.: `por+eng+spa+fra+ita`). Os pacotes de idioma precisam
  estar instalados no tesseract (ex.: `tesseract-ocr-por`); se faltar, cai para
  inglês em vez de falhar;
- **prepara a imagem** (tons de cinza + autocontraste + amplia páginas de baixa
  resolução) e renderiza a **300 DPI** (repetindo a 450 se sair fraco);
- usa engine LSTM (`--oem 1 --psm 3`), configurável por `NUTEV_OCR_CONFIG`.

> Windows — instalar o idioma português no tesseract: baixe `por.traineddata`
> de `github.com/tesseract-ocr/tessdata` e coloque em
> `C:\Program Files\Tesseract-OCR\tessdata\`.

## O que sai

| Arquivo | Conteúdo |
|---|---|
| `06_tables/NUTEV_GUIDES_CODED.csv` | **Uma linha por guia**: país, emissor, `sha256`, `fulltext_status`, OCR, `profile` A/B/C/D, **tipo de documento + peso de evidência**, **padrões nomeados** (mediterrânea/DASH/…), **nº de temas + temas detectados**, **valores nutricionais** (macros %, fibra, sódio, micronutrientes), termos frequentes e frases-chave. |
| `06_tables/NUTEV_GUIDES_EVIDENCE.csv` | **Tabela de evidências (tidy)**: uma linha por tema detectado, com o **trecho verbatim** (evidência), a família/subtema, o tipo/peso de documento e a **referência** — ouro para o scoping. |
| `06_tables/NUTEV_GUIDES_DOMAIN_STATES.csv` | **Estados A/B/C/D (protocolo §7.2/§7.3)**: uma linha por documento × domínio com o **estado** (`NOT_ASSESSED`/`MENTIONED`/`RECOMMENDED`/`OPERATIONALIZED`), a **intensidade 0–3** sugerida, o **trecho + página** que justifica e a referência. Marcado `machine_suggestion` — é a fila que os dois revisores humanos validam. |
| `10_curated/guides_coded.json` | Detalhe completo por guia: frases-chave (`{domain, actionable, sentence, page, reference}`) **e** os temas com seus trechos (`themes[família][subtema].snippets`). |
| `07_logs/guides_summary.json` | Contagem: guias, com texto, OCR, frases-chave, **temas detectados**, **trechos de evidência**, distribuição por `profile`. |
| `07_logs/{file_asset,document_version,document_family,denominator}_registry.csv` | **Registros de entidade (§7.1)**: separam **arquivo × documento × versão**. `file_asset` = arquivo físico (sha256); `document_version` = mesmo documento+edição/ano/idioma (PDF e HTML da mesma edição colapsam em 1); `document_family` = documento através das edições (a mais nova é `current`, as antigas `superseded`); `denominator_registry` = as contagens nomeadas para **nunca somar denominadores incompatíveis**. Agregadores/derivados não são contados como documento. |
| `06_tables/NUTEV_GUIDES_EVIDENCE_GEMS.csv` + `10_curated/best_gems.md` | **Banco de riquezas (§14)**: ranqueia os documentos de maior **valor descritivo** (score 0–18: autoridade, vigência, amplitude A/B/C/D, especificidade operacional, rastreabilidade, novidade, material de implementação), cada um com **trecho + página + referência** e o **destino sugerido no manuscrito**. Marcado `candidate` / revisão humana. **É valor descritivo, NÃO avaliação de qualidade ou risco de viés.** |
| `06_tables/NUTEV_GUIDES_SCREENING_QUEUE.csv` | **Fila de triagem por dois revisores (§13)**: uma linha por documento para os **dois revisores** decidirem (include/exclude/uncertain) com motivo padronizado. Documentos sem texto útil / OCR ruim recebem `screen_flag` (`no_full_text`/`poor_ocr`) e vão para fila separada. **Nada fica `export_ready` até dois revisores validarem** — o gate de exportação bloqueia registros não validados (a lógica de conflito/adjudicação/kappa está em `nutev.review.screening`). |
| `06_tables/NUTEV_GUIDES_ABCD_MATRIX.csv` + `07_logs/prisma_counts.json` + `10_curated/prisma_diagram.md` + `08_docs/DATA_DICTIONARY.md` | **Exportações reprodutíveis (§17)**: a **matriz larga documento × A/B/C/D** (estado + intensidade — o resultado central), as **contagens PRISMA-ScR** (identificação/prontidão; `included = pending`, pois a validação é humana), o **diagrama PRISMA** (Mermaid) e o **dicionário de dados**. O pipeline **nunca declara corpus final**. |

### Detecção temática rica (multilíngue, config-driven)

Além do A/B/C/D, cada guia passa por um **detector temático granular** — definido em
`config/thematic_taxonomy.json` (EN/PT/ES), fácil de editar:

- **Padrões nomeados**: mediterrânea, DASH, MIND, nórdica, portfolio, plant-based, EAT-Lancet, FBDG
- **Pilares de Lifestyle Medicine**: sono, estresse, atividade física, conexão social, ambiente alimentar
- **Neuro / saúde mental**: depressão, ansiedade, cognição, demência, eixo intestino-cérebro, neuroinflamação, estresse oxidativo, neuroplasticidade
- **Competências alimentares**: culinária, planejamento, compras, rótulos, comensalidade, estrutura das refeições
- **Processamento (NOVA)**: minimamente processado, ultraprocessado
- **Implementação**: aderência, custo, acesso, tempo, cultura, viabilidade, ambiente
- **Tipo de documento → peso de evidência** (guideline=5, consenso/revisão=4, ensaio=3, observacional=2)
- **Valores nutricionais** por regex: faixas de macro (`45-65%`), fibra (`25g`), sódio (`2000 mg`), micronutrientes

Para **cada tema detectado**, o sistema guarda o **trecho verbatim** (janela de ~240
caracteres) — a evidência que você lê e cita. Tudo assistivo, sob revisão humana.
As mesmas colunas resumidas também saem no `article_data.csv` do pipeline principal.

O texto integral extraído/OCR fica em `04_ocr_text/` e `05_extraction/`.

## As frases-chave — com a referência e a página

Para cada domínio, o extrator pega as **sentenças verbatim** que contêm um termo
do domínio, priorizando as que também têm um **verbo de recomendação**
(`recommends`, `should`, `deve`, `recomenda`…) — a mesma regra de
"substantividade" da codificação.

Cada frase carrega **a referência em si** (não só o texto): a **citação** do
documento-fonte + a **página** onde a frase aparece + o `source_url` + o
`sha256` do arquivo arquivado. Assim toda frase é citável e rastreável:

```
[A] (p.12) O guia recomenda aumentar o consumo de frutas e hortaliças…
    ↳ referência: Ministério da Saúde. Guia Alimentar para a População Brasileira.
      Brazil. 2014. Disponível em: https://… . Acesso em: 2026-07-16. SHA-256: ab12…
```

A citação completa sai na coluna `reference` da tabela e em cada item de
`key_phrases` no `guides_coded.json` (`{domain, actionable, sentence, page,
reference, source_url, sha256}`).

## Também no pipeline principal

O `nutev --project-root SAIDA` (busca1/2a/2b) agora também grava, por documento,
as colunas `track`, `profile`, `domain_A..D`, `n_key_phrases`, `top_terms` e
`key_phrases_text` no `02_metadata/article_data.csv` — a classificação e as
frases-chave aparecem na tabela principal, não só na camada curada.

## Dashboard web do Artigo 1 (§15)

Depois de rodar `nutev guides`, você pode ver os resultados no navegador (sem
build de frontend):

```bash
pip install -e ".[api]"
nutev serve --project-root SAIDA        # sobe a API em http://127.0.0.1:8000
# abra:  http://127.0.0.1:8000/api/article1/dashboard
```

O dashboard mostra os **denominadores**, o **PRISMA-ScR** (com `incluídos =
PENDENTE`, pois a validação é humana), a **matriz A/B/C/D** (estado colorido) e as
**riquezas** ranqueadas — com os avisos de que tudo é assistivo e não é corpus
final. Endpoints JSON em `/api/article1/*` (denominators, prisma, abcd-matrix,
domain-states, gems, screening-queue, families, versions) alimentam a futura app
Next.js completa.

## Limite honesto

Guias públicos: dá para pegar quase todos. O que estiver atrás de acesso
institucional continua marcado para você baixar pela biblioteca/VPN da UnB — o
sistema não fura paywall. A codificação A/B/C/D e as frases são **sugestões**
para o seu olho humano confirmar.
