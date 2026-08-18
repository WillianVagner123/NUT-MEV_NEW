# POP — Uso do NutEV Reference Engine

**Documento:** Procedimento Operacional Padrão  
**Produto:** NutEV Reference Engine  
**Versão estável publicada:** 1.0.0  
**Plataforma operacional principal:** Windows  
**Python suportado:** 3.12 ou 3.13  
**Fluxo oficial:** `SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT`  
**DOI da versão publicada:** `10.5281/zenodo.21998607`

## 1. Objetivo

Padronizar a instalação, atualização, execução, verificação, interpretação e registro das execuções do NutEV Reference Engine.

O software coleta referências em múltiplas fontes, normaliza metadados, aplica uma regra explícita de identidade/deduplicação, calcula um score de prioridade de leitura e exporta resultados estruturados.

O ranking não substitui critérios de elegibilidade, avaliação metodológica, síntese de evidências ou recomendação clínica.

## 2. Escopo

Este POP cobre o uso corrente da branch `main` do repositório:

```text
WillianVagner123/NutEV-Evidence-Engine
```

A tag `v1.0.0` representa o snapshot publicado e arquivado. A `main` contém correções e documentação pós-release.

## 3. Responsabilidade do operador

O operador deve:

- usar Python 3.12 ou 3.13;
- atualizar `main` antes de uma execução corrente;
- registrar o SHA quando a execução precisar ser auditável;
- não interromper a coleta sem necessidade;
- não apagar checkpoints por padrão;
- verificar os códigos finais de cada etapa;
- preservar os outputs e manifests relevantes;
- interpretar o ranking como prioridade de leitura, não como decisão científica automática;
- não versionar credenciais ou dados privados.

## 4. Pré-requisitos

Confirmar:

- Windows com acesso à internet;
- Git instalado;
- Python 3.12 ou 3.13 instalado;
- acesso ao GitHub;
- espaço em disco para a árvore `project_output_reference`.

No CMD:

```bat
git --version
py -3.12 --version
python --version
```

Não é necessário que todos os comandos Python funcionem; basta uma instalação compatível que seja encontrada pelo launcher.

## 5. Primeira instalação

No Prompt de Comando:

```bat
cd %USERPROFILE%
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git
cd NutEV-Evidence-Engine
Iniciar-NutEV-Windows.bat
```

Na primeira execução, `Iniciar-NutEV-Windows.bat`:

1. entra no diretório do repositório;
2. procura `py -3.12` e depois `python`;
3. cria `.venv` se ela ainda não existir;
4. atualiza `pip`;
5. instala o projeto com `pip install -e .`;
6. chama `RODAR_TUDO.cmd`;
7. tenta abrir `TOP_REFERENCIAS.md` quando o arquivo existe;
8. mostra um `pause` antes de fechar.

## 6. Atualização antes do uso

Se o repositório já está clonado:

```bat
cd %USERPROFILE%\NutEV-Evidence-Engine
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
```

Se o clone estiver em outro local, usar a pasta correspondente.

Registrar o SHA quando a execução for usada em documentação, auditoria, artigo, relatório ou comparação entre versões.

## 7. Execução padrão

No diretório do projeto:

```bat
Iniciar-NutEV-Windows.bat
```

Se o ambiente já está pronto, também é possível chamar:

```bat
RODAR_TUDO.cmd
```

O fluxo deve mostrar:

```text
[1/3] COLETA MULTI-FONTE
[2/3] LILACS/BVS + SCIELO NATIVO
[3/3] RANKING DE REFERENCIAS
```

## 8. Critério de sucesso operacional

A execução é considerada concluída sem erro de pipeline quando o terminal exibe:

```text
Coleta geral: codigo 0
LILACS/BVS + SciELO: codigo 0
Ranking: codigo 0
SUCESSO: ranking de referencias gerado.
```

Além disso, confirmar a existência de:

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/latest.json
```

Em `latest.json`, confirmar:

```text
"mode": "REFERENCE_RANKING"
"status": "COMPLETE"
```

## 9. Perfil operacional

O perfil padrão é `operational`.

Limites configurados:

| Provider | Limite |
|---|---:|
| PubMed | 2.000 |
| Europe PMC | 3.000 |
| OpenAlex | 3.000 |
| Crossref | 1.000 |
| DOAJ | 1.000 |
| Semantic Scholar | 1.000 |

O terminal mostra o perfil ativo antes de iniciar a rede.

## 10. Perfil profundo

Somente quando houver necessidade explícita de coleta maior:

```bat
set NUTEV_DEEP_COLLECTION=1
Iniciar-NutEV-Windows.bat
```

Limites configurados:

| Provider | Limite deep |
|---|---:|
| PubMed | 9.999 |
| Europe PMC | 50.000 |
| OpenAlex | 50.000 |
| Crossref | 10.000 |
| DOAJ | 10.000 |
| Semantic Scholar | 10.000 |

O perfil profundo pode levar muito mais tempo e não garante exaustividade.

Para retornar ao padrão na mesma sessão:

```bat
set NUTEV_DEEP_COLLECTION=
```

## 11. Variáveis opcionais

O runtime atual não carrega `.env` automaticamente.

Definir variáveis no ambiente da sessão, por exemplo:

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

A ausência de `NCBI_EMAIL`/`ENTREZ_EMAIL` não impede o PubMed; o cliente usa um ritmo conservador.

Nunca registrar chaves reais em arquivos versionados, logs públicos, issues ou pull requests.

## 12. Providers

O modo padrão tenta:

- PubMed;
- Europe PMC;
- OpenAlex;
- Crossref;
- DOAJ;
- Semantic Scholar;
- fontes oficiais configuradas;
- LILACS/BVS;
- SciELO.

Google Programmable Search, Brave e SerpAPI dependem de credenciais.

Scopus e Web of Science não são simulados.

## 13. BVS/LILACS e SciELO

Essas rotas usam interfaces públicas nativas.

Se a interface responder com HTTP `401` ou `403`, a `main` atual registra o provider como `unavailable` e permite que o pipeline continue com as fontes coletadas com sucesso.

Esse estado não deve ser interpretado como ausência de literatura na base.

## 14. Interrupção e retomada

O PubMed mantém checkpoints.

Se houver interrupção:

```bat
Iniciar-NutEV-Windows.bat
```

Não apagar `project_output_reference` ou checkpoints por padrão.

Código `130` normalmente indica interrupção por `Ctrl+C`.

Se a interrupção ocorrer antes da finalização do master da coleta geral, o ranker pode emitir:

```text
Nenhum master de coleta encontrado
```

Nesse caso, executar novamente e permitir que a etapa `[1/3]` termine.

## 15. Arquivos de saída

### `TOP_REFERENCIAS.md`

Leitura humana do TOP N configurado. Exibe score, faixa, provider, ano, DOI/PMID/URL quando disponíveis, grupos de taxonomia e palavras-chave foco.

### `reference_ranking.csv`

Tabela completa do ranking para planilha, auditoria e curadoria manual.

### `reference_ranking.jsonl`

Saída estruturada para processamento automático.

### `latest.json`

Resumo da execução com:

- status;
- timestamp;
- arquivos-fonte;
- contagens;
- número de grupos de taxonomia;
- focus keywords;
- TOP N;
- caminhos dos outputs.

## 16. Como interpretar A/B/C

As faixas são definidas pela posição:

- 1–20: `A_TOP_REFERENCE`;
- 21–100: `B_STRONG_REFERENCE`;
- demais: `C_DISCOVERY`.

A faixa não é nível de evidência.

## 17. Deduplicação

A identidade atual segue:

```text
DOI -> PMID -> URL -> título normalizado
```

Isso não elimina todas as duplicatas semânticas.

Publicações paralelas, versões ou registros com identificadores diferentes podem aparecer mais de uma vez.

Antes de uso científico final, revisar manualmente o conjunto priorizado.

## 18. Registro mínimo de uma execução auditável

Antes de executar:

```bat
git rev-parse HEAD
```

Após executar, preservar pelo menos:

```text
project_output_reference/reference_ranking/latest.json
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/reference_ranking.jsonl
```

Quando necessário, preservar também os masters e manifests usados pela execução.

Registrar:

- data/hora;
- SHA do repositório;
- perfil `operational` ou `deep`;
- providers indisponíveis/falhos;
- `records_input`;
- `records_unique`;
- `taxonomy_groups_loaded`;
- `top_n`.

## 19. Execução real validada em 18/08/2026

Foi fornecido pelo operador um resultado real com:

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

Esse registro está detalhado em `VALIDATED_WINDOWS_RUN_2026-08-18.md`.

`records_unique: 8702` não comprova que 8.702 publicações sejam semanticamente distintas; somente descreve a regra de identidade aplicada naquela execução.

## 20. Mensagens do VS Code

Após o engine abrir `TOP_REFERENCIAS.md`, o VS Code pode imprimir mensagens como:

```text
StorageMainService
Unknown channel
DeprecationWarning
```

Essas mensagens pertencem ao VS Code e não devem ser confundidas automaticamente com erros do Reference Engine.

O estado do engine está no resumo dos códigos exibido antes da abertura do arquivo.

## 21. `Deseja finalizar o arquivo em lotes (S/N)?`

Essa pergunta vem do CMD quando `Ctrl+C` é usado durante um `.bat/.cmd`.

Se o terminal já exibiu:

```text
SUCESSO: ranking de referencias gerado.
```

o output final daquela execução já foi gerado.

## 22. Controle de mudanças

Qualquer alteração que modifique:

- providers;
- consultas;
- limites;
- regra de identidade;
- taxonomia;
- pesos;
- tipos documentais;
- outputs;
- interpretação dos scores;

deve atualizar a documentação correspondente e ser validada por testes/CI antes do merge.

## 23. Referências internas

- arquitetura e pesos: `ARCHITECTURE.md`;
- providers: `SEARCH_PROVIDERS.md`;
- limitações: `KNOWN_LIMITATIONS.md`;
- release: `RELEASE_V1_0_0.md`;
- checklist de release: `RELEASE_CHECKLIST.md`;
- DOI/Zenodo: `ZENODO_SETUP.md`.
