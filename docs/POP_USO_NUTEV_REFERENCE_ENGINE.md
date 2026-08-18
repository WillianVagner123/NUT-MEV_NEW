# POP — Uso do NutEV Reference Engine

**Documento:** Procedimento Operacional Padrão (POP)  
**Produto:** NutEV Reference Engine  
**Versão de software:** 1.0.0  
**Plataforma operacional principal:** Windows  
**Python suportado:** 3.12 ou 3.13  
**Fluxo oficial:** `SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT`

## 1. Objetivo

Este POP descreve como instalar, atualizar, executar, monitorar e interpretar o NutEV Reference Engine de forma reproduzível. O software coleta referências em múltiplas fontes, normaliza metadados, aplica deduplicação por identificadores/metadados, classifica registros segundo a taxonomia NutEV e exporta uma fila priorizada de leitura.

O ranking é uma prioridade de recuperação de informação. Ele **não** representa elegibilidade científica, avaliação metodológica, recomendação clínica ou decisão automática sobre uso de uma referência.

## 2. Escopo

Este procedimento cobre o uso corrente do repositório `WillianVagner123/NutEV-Evidence-Engine` no Windows.

O modo operacional padrão consulta PubMed, Europe PMC, OpenAlex, Crossref, DOAJ, Semantic Scholar, fontes oficiais configuradas e tenta as rotas nativas LILACS/BVS e SciELO. Google Programmable Search, Brave e SerpAPI só são usados quando as respectivas credenciais estão configuradas.

Scopus e Web of Science não são simulados. Quando acesso licenciado não está configurado, o sistema os registra como indisponíveis.

## 3. Pré-requisitos

Antes da primeira execução, confirmar:

- Windows com acesso à internet;
- Git instalado;
- Python 3.12 ou 3.13 instalado;
- acesso ao repositório GitHub;
- espaço em disco para `project_output_reference`.

Verificações rápidas no Prompt de Comando:

```bat
python --version
py -3.12 --version
git --version
```

Basta uma instalação Python compatível; o launcher procura primeiro `py -3.12` e depois `python`.

## 4. Primeira instalação

No Prompt de Comando:

```bat
cd C:\Users\Victor
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git
cd NutEV-Evidence-Engine
Iniciar-NutEV-Windows.bat
```

Na primeira execução, `Iniciar-NutEV-Windows.bat` cria `.venv`, atualiza `pip`, instala o projeto em modo editável e chama `RODAR_TUDO.cmd`.

Se o repositório já estiver clonado, não é necessário clonar novamente.

## 5. Atualizar antes de executar

Para trabalhar com a versão mais recente de `main`:

```bat
cd C:\Users\Victor\NutEV-Evidence-Engine
git checkout main
git pull --ff-only origin main
```

Opcionalmente, registrar o commit exato usado:

```bat
git rev-parse HEAD
```

Esse SHA deve ser guardado quando a execução precisar ser citável ou auditável.

## 6. Execução padrão recomendada

No diretório do projeto:

```bat
Iniciar-NutEV-Windows.bat
```

Depois que o ambiente virtual já existe, também é possível executar diretamente:

```bat
RODAR_TUDO.cmd
```

O launcher oficial executa três etapas:

```text
[1/3] COLETA MULTI-FONTE
[2/3] LILACS/BVS + SCIELO NATIVO
[3/3] RANKING DE REFERENCIAS
```

Uma execução válida termina com:

```text
Coleta geral: codigo 0
LILACS/BVS + SciELO: codigo 0
Ranking: codigo 0
SUCESSO: ranking de referencias gerado.
```

## 7. Perfil operacional e perfil profundo

O perfil padrão é `operational`. Ele usa os seguintes limites máximos configurados:

| Provider | Limite operacional |
|---|---:|
| PubMed | 2.000 |
| Europe PMC | 3.000 |
| OpenAlex | 3.000 |
| Crossref | 1.000 |
| DOAJ | 1.000 |
| Semantic Scholar | 1.000 |

O terminal mostra o perfil e os limites no início da coleta.

Para uma coleta mais extensa, habilitar explicitamente o perfil profundo na mesma sessão do CMD:

```bat
set NUTEV_DEEP_COLLECTION=1
Iniciar-NutEV-Windows.bat
```

O perfil profundo pode levar substancialmente mais tempo. Para voltar ao padrão na mesma sessão:

```bat
set NUTEV_DEEP_COLLECTION=
```

## 8. Variáveis opcionais e credenciais

O arquivo `.env.example` é apenas uma referência de nomes de variáveis. O projeto atual **não carrega automaticamente um arquivo `.env`**.

No CMD, configurar variáveis antes da execução, por exemplo:

```bat
set NCBI_EMAIL=seu-email@exemplo.com
set NCBI_API_KEY=sua-chave-se-tiver
set CROSSREF_MAILTO=seu-email@exemplo.com
set OPENALEX_MAILTO=seu-email@exemplo.com
set S2_API_KEY=sua-chave-se-tiver
```

Para provedores web opcionais:

```bat
set GOOGLE_API_KEY=...
set GOOGLE_CSE_ID=...
set BRAVE_API_KEY=...
set SERPAPI_API_KEY=...
```

Não versionar chaves, tokens ou e-mails privados em arquivos do repositório.

A ausência de `NCBI_EMAIL`/`ENTREZ_EMAIL` não impede a execução; o cliente PubMed usa um ritmo conservador quando não há e-mail/API key configurados.

## 9. Retomada após interrupção

O PubMed mantém checkpoints e o coletor foi configurado para retomar o trabalho quando possível.

Se a execução for interrompida, executar novamente:

```bat
Iniciar-NutEV-Windows.bat
```

Não apagar `project_output_reference` nem os checkpoints por padrão. Eles podem conter estado útil para retomada e auditoria.

Código `130` indica normalmente interrupção pelo usuário (`Ctrl+C`). Se isso ocorrer antes da finalização do master de coleta, o ranking pode ficar sem entrada suficiente.

## 10. Comportamento de providers indisponíveis

Falhas de provider são registradas explicitamente nos manifests.

LILACS/BVS e SciELO usam interfaces públicas nativas. Se essas interfaces recusarem automação com HTTP `401` ou `403`, o provider é registrado como `unavailable`; o sistema não fabrica registros e pode continuar com as demais fontes disponíveis.

Uma falha de provider isolada não deve ser interpretada como ausência de literatura naquela base.

## 11. Arquivos de saída

Os principais resultados ficam em:

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/latest.json
```

### `TOP_REFERENCIAS.md`

Arquivo de leitura humana com o TOP N configurado, score, faixa de prioridade, fonte, ano, DOI/PMID/URL quando disponíveis, grupos de taxonomia correspondentes e palavras-chave foco.

### `reference_ranking.csv`

Formato tabular para inspeção, filtragem e análise em planilhas ou ferramentas estatísticas.

### `reference_ranking.jsonl`

Formato estruturado, uma referência por linha JSON, indicado para processamento automatizado.

### `latest.json`

Resumo da execução de ranking: status, arquivos-fonte, contagens, número de grupos de taxonomia carregados, palavras-chave foco, TOP N e caminhos dos outputs.

## 12. Como interpretar o ranking

As faixas são:

- `A_TOP_REFERENCE`: maior prioridade de leitura;
- `B_STRONG_REFERENCE`: referências complementares fortes;
- `C_DISCOVERY`: conjunto de descoberta com prioridade relativa menor.

O score combina sinais de taxonomia, termos foco, tipo documental, provider/fonte, identificadores bibliográficos e recência leve.

O ranking não substitui leitura crítica. Um documento com score alto pode ser menos adequado ao objetivo final do pesquisador do que outro com score menor.

A deduplicação atual é orientada por identificadores e metadados. Publicações semanticamente equivalentes, versões paralelas ou documentos com DOIs distintos podem permanecer separadas. Por isso, o TOP deve ser inspecionado antes de uso final.

## 13. Execução real validada em Windows — 18/08/2026

Uma execução operacional real fornecida pelo operador terminou com sucesso e registrou:

```text
mode: REFERENCE_RANKING
status: COMPLETE
records_input: 8702
records_unique: 8702
taxonomy_groups_loaded: 115
top_n: 100

Coleta geral: codigo 0
LILACS/BVS + SciELO: codigo 0
Ranking: codigo 0
SUCESSO: ranking de referencias gerado.
```

Os arquivos-fonte do ranking nessa execução foram um `master_records.jsonl` da coleta geral e um `latin_native_records.jsonl` da etapa latino-americana.

`records_input == records_unique` nessa execução significa que nenhuma duplicata foi removida pela regra de identidade aplicada nessa etapa; não prova ausência de duplicatas semânticas.

O registro detalhado dessa validação está em `docs/VALIDATED_WINDOWS_RUN_2026-08-18.md`.

## 14. Resolução de problemas

### `Nenhum master de coleta encontrado`

A coleta geral não finalizou um master utilizável. Executar novamente e deixar a etapa `[1/3]` terminar. Se houve `Ctrl+C`, o código pode ser `130`.

### HTTP 401/403 em BVS ou SciELO

O provider foi bloqueado pela interface pública automatizada. A versão atual registra isso como indisponibilidade e segue com as demais fontes.

### O arquivo Markdown abriu no VS Code e apareceram mensagens `StorageMainService`, `Unknown channel` ou `DeprecationWarning`

Essas mensagens são do VS Code que abriu o `.md`, não do NutEV Reference Engine. O estado do motor deve ser lido nas linhas `Coleta geral`, `LILACS/BVS + SciELO`, `Ranking` e `SUCESSO` anteriores à abertura do arquivo.

### O CMD pergunta `Deseja finalizar o arquivo em lotes (S/N)?`

Isso costuma ocorrer quando `Ctrl+C` é pressionado durante um `.bat/.cmd`. Se a execução já exibiu `SUCESSO`, o ranking já foi gerado. Para evitar interrupção desnecessária, aguardar o `Pressione qualquer tecla para continuar` do launcher.

## 15. Checklist operacional

Antes da execução:

- atualizar `main`;
- registrar `git rev-parse HEAD` quando houver necessidade de auditoria;
- confirmar Python 3.12/3.13;
- definir variáveis opcionais na sessão, se desejado;
- usar o perfil `operational` salvo necessidade explícita de coleta profunda.

Após a execução:

- confirmar os três códigos de saída;
- confirmar `status: COMPLETE` em `latest.json`;
- registrar `records_input`, `records_unique`, `taxonomy_groups_loaded` e `top_n`;
- abrir `TOP_REFERENCIAS.md`;
- inspecionar duplicatas semânticas e pertinência antes de usar referências em produção científica.

## 16. Referência do software

NutEV Reference Engine v1.0.0  
DOI: `10.5281/zenodo.21998607`  
Zenodo record: `21998607`

A tag publicada `v1.0.0` permanece imutável. Correções e documentação posteriores ficam em `main` e não alteram o snapshot arquivado da tag.
