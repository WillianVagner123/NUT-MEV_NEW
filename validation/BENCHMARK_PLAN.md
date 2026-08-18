# Benchmark Plan

## Pergunta primária

O NutEV Reference Engine melhora a priorização de referências relevantes e/ou reduz o volume necessário de leitura em comparação com baselines apropriados?

## Unidade de análise

A unidade primária é a pergunta (`question_id`). Resultados agregados nunca devem esconder desempenho por pergunta.

## Sistemas mínimos

- `nutev_full`;
- `pubmed_native`;
- `union_unranked`;
- `lexical_baseline`;
- `recency_baseline`;
- `nutev_no_taxonomy`;
- `nutev_no_focus`;
- `nutev_no_provider_weight`;
- `nutev_no_recency`;
- `nutev_no_document_type`;
- `nutev_no_identifier_bonus`.

Ferramentas externas podem ser adicionadas quando houver forma reprodutível e comparável de exportar resultados.

## Métricas

### Ranking

- precision@10/20/50/100;
- recall@10/20/50/100;
- reciprocal rank;
- average precision;
- nDCG@10/20/50/100.

### Workload

- registros lidos até 80% de recall;
- registros lidos até 90% de recall;
- registros lidos até 95% de recall;
- fração do ranking lida até cada marco.

## Relevance

- binária: `relevance_grade > 0`;
- graduada para nDCG: valores 0/1/2 preservados.

## Identidade

Os rankings e o gold standard devem usar o mesmo `reference_id` canônico. Registros sem identidade reconciliável devem ser reportados, não aproximados silenciosamente.

## Pré-especificação

Antes de abrir `external_test`, registrar:

- commit SHA do candidato;
- hash de `reference_mode.json`;
- hash de `taxonomy_registry.json`;
- hashes de `keyword_taxonomy*.json`;
- queries e provider limits;
- versão da política de guardrails;
- scripts e versões de comparadores;
- critérios primários de sucesso.

## Critério mínimo para sair de B_DEMOTE

Não existe limiar universal pré-declarado neste scaffold. Antes do teste externo, deve ser escolhido um critério material e defensável, por exemplo ganho em `recall@100`, `nDCG@20` ou redução de workload sem perda inaceitável de recall.

O critério deve ser escolhido antes de observar o conjunto externo e permanecer registrado mesmo se o resultado for desfavorável.

## Relato

Para cada sistema:

- métricas por pergunta;
- média e mediana;
- dispersão;
- pior caso;
- melhor caso;
- número de perguntas vencidas/empatadas/perdidas versus baseline primário;
- análise de erros qualitativa.

## Estatística

Quando o número de perguntas permitir, usar intervalos de confiança por reamostragem no nível da pergunta e comparação pareada entre sistemas. Não tratar milhares de referências dentro da mesma pergunta como observações independentes para inflar precisão estatística.

## Ablations

Ablations devem alterar um componente por vez usando o mesmo corpus e gold standard. Se uma ablação melhorar consistentemente o resultado, o componente removido deve ser considerado prejudicial ou desnecessário até explicação adicional.

## Estado atual

`NOT_TESTED` — o scaffold de métricas pode ser executado somente após existir gold standard e arquivos de ranking comparáveis.
