# Benchmark Plan

## Pergunta primária

O NutEV Reference Engine melhora a **priorização de leitura** e/ou reduz o volume necessário para localizar referências relevantes em comparação com baselines apropriados?

A alegação de **descoberta/cobertura** será testada separadamente. Um bom ranking dentro de um corpus não prova que o corpus contém a literatura relevante que deveria conter.

## Candidato congelado

Runtime NutEV a ser testado:

```text
6aa7a5fe6009776e611ca3e1506486606b05f4f6
```

O harness de benchmark pode evoluir fora desse SHA, mas não pode alterar o runtime congelado nem usar labels de `external_test` para recalibrá-lo.

## Unidade de análise

A unidade primária é a pergunta (`question_id`). Resultados agregados nunca devem esconder desempenho por pergunta.

## Duas camadas de benchmark

### A. COMMON_POOL_PRIORITIZATION

Objetivo: testar **ordenação/priorização** entre os registros já elegíveis no output congelado do NutEV.

Essa camada usa o mesmo conjunto de referências para todos os sistemas comparados. Ela permite testar o score NutEV contra baselines de ordenação sem confundir ranking com cobertura de busca.

Sistemas:

- `nutev_full`;
- `lexical_baseline` — BM25 label-blind usando apenas texto da pergunta e metadados do registro;
- `recency_baseline`;
- `union_unranked` — ordem pseudoaleatória determinística pré-especificada;
- `nutev_no_taxonomy`;
- `nutev_no_focus`;
- `nutev_no_provider_weight`;
- `nutev_no_recency`;
- `nutev_no_document_type`;
- `nutev_no_identifier_bonus`.

O `nutev_full` congelado não recebe `question_text` como parâmetro. Portanto sua mesma fila global é avaliada em cada pergunta. Isso é uma propriedade/limitação do produto congelado, não deve ser mascarada por uma adaptação criada depois do freeze.

As ablações são reconstruídas de forma label-blind a partir do `score_breakdown` congelado, removendo um componente por vez. Elas não re-treinam pesos.

**Limite:** `recall@k` nesta camada significa recuperação de itens julgados relevantes **dentro do common pool**. Não é estimativa de recall bibliográfico global.

### B. DISCOVERY_COVERAGE

Objetivo: testar se o conjunto recuperado pelo NutEV encontra referências relevantes que deveriam ser encontradas e como sua cobertura se compara a rotas independentes.

Comparadores mínimos quando a execução real estiver disponível:

- PubMed com estratégia registrada e ordenação nativa;
- providers/união multibase com estratégia registrada;
- busca independente usada na construção do gold standard;
- ferramentas externas somente quando houver exportação reproduzível e comparável.

Essa camada precisa de referências relevantes independentes que possam estar **fora** do corpus NutEV. Somente ela pode sustentar alegações de discovery recall.

`DISCOVERY_COVERAGE` permanece `NOT_TESTED` até existirem execuções comparáveis e gold standard independente.

## Harness label-blind

`tools/build_scientific_benchmark_rankings.py` constrói a camada common-pool sem abrir o gold standard.

Parâmetros pré-especificados:

- frozen runtime SHA obrigatório: `6aa7a5fe6009776e611ca3e1506486606b05f4f6`;
- BM25 `k1 = 1.2`, `b = 0.75`;
- `union_unranked` usa SHA-256 pseudoaleatório determinístico com seed `nutev-benchmark-v1`;
- identidade de ranking usa o contrato canônico do runtime;
- o manifesto declara `gold_standard_consumed = false`.

A ferramenta deve falhar se o SHA fornecido não corresponder ao candidato congelado.

## Métricas

### Ranking

- precision@10/20/50/100;
- recall@10/20/50/100;
- reciprocal rank;
- `average_precision@100` na profundidade completamente julgada;
- full-list average precision somente se toda a lista avaliada estiver julgada;
- nDCG@10/20/50/100.

### Judgment coverage

O avaliador reporta cobertura de julgamento por profundidade e o prefixo totalmente julgado. Documento não julgado **não** é convertido silenciosamente em irrelevante.

Para a comparação pré-registrada:

- `nDCG@20` exige 100% de julgamento até rank 20 em `nutev_full` e `lexical_baseline`;
- `recall@100` exige 100% de julgamento até rank 100 nos dois sistemas;
- cobertura incompleta nesses endpoints encerra a comparação com erro, em vez de produzir uma métrica enviesada.

### Workload

- registros lidos até 80% de recall disponível;
- registros lidos até 90%;
- registros lidos até 95%;
- fração da lista lida até cada marco.

### Discovery coverage

Quando a camada B for executada, reportar adicionalmente:

- recall contra o gold standard independente;
- relevantes exclusivos por sistema/provider;
- referências do gold standard ausentes do NutEV;
- contribuição marginal por provider;
- efeito da quarentena na cobertura.

## Relevance

- binária: `relevance_grade > 0`;
- graduada para nDCG: valores 0/1/2 preservados.

## Identidade

Rankings e gold standard precisam de reconciliação explícita de identidade. Não usar posição no ranking como identidade e não aproximar títulos silenciosamente.

O common-pool usa o `reference_id` derivado do contrato do runtime congelado. A camada de discovery pode preservar DOI/PMID/PMCID/URL e uma chave manual controlada para referências externas, mas qualquer reconciliação com o ranking precisa ficar auditável.

## Pré-especificação

Antes de abrir `external_test`, registrar:

- commit SHA do candidato;
- hash de `reference_mode.json`;
- hash de `reference_search.json`;
- hash de `taxonomy_registry.json`;
- hashes de `keyword_taxonomy*.json`;
- queries e provider limits;
- versão da política de guardrails;
- versão/hash dos scripts de benchmark;
- comparadores e parâmetros;
- critério primário de sucesso.

## Critério para sair de B_DEMOTE

Para `C — SCIENTIFIC_CANDIDATE`, o split `validation` deve cumprir os critérios pré-registrados: mediana do delta `nDCG@20 > 0`, mais vitórias que derrotas e mediana do delta `recall@100 >= -0.05`.

Para `D — VALIDATED_FOR_DEFINED_USE` no escopo de common-pool prioritization, o split `external_test` deve ter pelo menos 12 perguntas benchmark-grade e cumprir simultaneamente os critérios registrados em `BENCHMARK_PREREGISTRATION.md`, incluindo limite inferior do IC bootstrap de 95% da média do delta `nDCG@20` maior que zero. Menos de 12 perguntas resulta em `INSUFFICIENT_EVIDENCE_SAMPLE_SIZE`, não em promoção.

Nenhum resultado desta camada autoriza alegações de discovery recall, qualidade metodológica da evidência ou validade clínica.

## Relato

Para cada sistema:

- métricas por pergunta;
- média e mediana;
- dispersão;
- pior e melhor caso;
- perguntas vencidas/empatadas/perdidas versus baseline primário;
- cobertura de julgamento nos endpoints;
- análise de erros;
- distinção explícita entre common-pool e discovery coverage.

## Estatística

A comparação principal é pareada no nível da pergunta. O harness usa bootstrap determinístico de 10.000 reamostragens da pergunta, seed `nutev-paired-bootstrap-v1`, e intervalo percentil de 95% para a média do delta `nDCG@20`. Não tratar milhares de referências dentro da mesma pergunta como observações independentes para inflar precisão estatística.

O limiar mínimo de 12 perguntas externas é um piso operacional pré-resultados, não uma garantia universal de poder ou generalização.

## Ablations

As ablações alteram um componente por vez no score congelado usando o mesmo common pool e os mesmos labels. Se a remoção de um componente melhorar consistentemente o desempenho, o componente removido deve ser tratado como potencialmente prejudicial ou desnecessário até explicação adicional.

## Estado atual

- `COMMON_POOL_PRIORITIZATION`: **INFRASTRUCTURE_READY / LABELS_NOT_AVAILABLE**;
- `DISCOVERY_COVERAGE`: **NOT_TESTED**;
- veredito científico do produto: **B — DEMOTE**.
