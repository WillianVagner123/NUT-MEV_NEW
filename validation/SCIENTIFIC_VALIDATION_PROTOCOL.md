# Protocolo de Reabilitação Científica do NutEV Reference Engine

Status inicial: `B_DEMOTE`  
Data de início: 2026-08-18  
Taxonomia candidata: `2026-08-v2`

## 1. Hipótese nula

> O NutEV Reference Engine não possui utilidade científica incremental demonstrada em relação a alternativas mais simples ou já existentes.

O projeto só sai de `B_DEMOTE` por evidência quantitativa externa. CI verde, hashes, rastreabilidade, DOI da release, volume recuperado e documentação são requisitos de engenharia; não são validação científica.

## 2. Claim candidato, restrito e testável

> Para perguntas relacionadas à Nutrição do Estilo de Vida, o NutEV Reference Engine melhora a descoberta e/ou a priorização de referências relevantes em comparação com baselines apropriados, mantendo rastreabilidade e reduzindo carga de curadoria.

Esse claim deve ser decomposto por tarefa. Não é permitido concluir "cientificamente validado" de forma geral.

## 3. Regra de congelamento

Antes do benchmark científico deve existir um `FREEZE` explícito do algoritmo a ser testado. Depois do freeze:

- pesos, queries, taxonomia e regras de ranking não podem ser alterados usando o conjunto de teste externo;
- qualquer ajuste deve usar apenas conjunto de desenvolvimento;
- mudança classificatória exige nova versão de taxonomia;
- mudança de algoritmo exige novo candidato e nova rodada de validação.

O freeze não pode ser declarado enquanto houver falha crítica no `ENGINEERING AUDIT`.

## 4. Gate 1 — Engineering audit

Verificar, com resultado `PASS`, `FAIL` ou `NOT_TESTED`:

1. identificadores sintaticamente plausíveis no gate de rastreabilidade;
2. consistência entre rastreabilidade e bônus de identificador no score;
3. mesma regra de identidade/deduplicação na coleta e no ranking;
4. documentação coerente com o runtime;
5. `workstreams.*` fora do score;
6. `global.document_types.*` fora da taxonomia;
7. código, queries, taxonomia, pesos e guardrails versionados;
8. hashes de inputs/configurações/outputs;
9. testes fail-closed;
10. tag estável `v1.0.0` preservada e imutável.

Qualquer `FAIL` crítico bloqueia o freeze científico.

## 5. Gate 2 — Gold standard externo

O gold standard não pode ser produzido pelo próprio ranker. Deve ser definido e rotulado por processo humano independente, preferencialmente com dois avaliadores e resolução pré-definida de conflitos.

Deve conter perguntas em múltiplos estratos e incluir perguntas fora dos focos históricos usados para construir o Engine.

Para cada registro, preservar:

- `question_id`;
- identificador canônico verificável;
- relevância binária ou graduada;
- avaliador;
- data;
- justificativa;
- estado de conflito/adjudicação.

O conjunto final de teste externo deve permanecer fechado durante calibração.

## 6. Gate 3 — Comparadores

Comparadores mínimos:

1. PubMed/ordenação nativa;
2. união multibase sem score NutEV;
3. ranking lexical simples;
4. ordenação por recência;
5. NutEV sem taxonomia;
6. NutEV sem provider weights;
7. NutEV sem focus keywords;
8. NutEV sem tipo documental.

Comparadores externos devem ser registrados com versão/data e configuração usada. Alegações de fornecedores devem ser marcadas como `VENDOR_REPORTED` até reprodução independente.

## 7. Métricas primárias

Por pergunta e agregadas:

- `precision@10`;
- `precision@20`;
- `precision@50`;
- `precision@100`;
- `recall@20`;
- `recall@50`;
- `recall@100`;
- `MRR`;
- `MAP`;
- `nDCG@10`;
- `nDCG@20`;
- `nDCG@100`.

Métricas operacionais:

- número de registros até 80%, 90% e 95% do recall disponível;
- fração do corpus lida até esses pontos;
- tempo humano quando houver estudo de usuário;
- referências irrelevantes examinadas antes de marcos de recall.

Relatar distribuição e resultados por pergunta, não apenas média global.

## 8. Validação da taxonomia

A taxonomia `2026-08-v2` é hipótese classificatória. Deve ser avaliada contra classificação humana independente para:

- `domain`;
- `context`;
- `condition`;
- `outcome`;
- `taxonomy_primary`;
- taxonomias secundárias.

Calcular precision, recall e F1 por categoria quando houver amostra suficiente, além de concordância entre humanos e Engine-humano. A regra fixa `domain -> context -> condition -> outcome` deve ser testada, não presumida correta.

## 9. Ablation study

Executar no mesmo conjunto, sem alterar labels:

- Engine completo;
- sem taxonomia;
- sem focus keywords;
- sem provider weights;
- sem recência;
- sem tipo documental;
- sem bônus de identificador;
- lexical simples;
- score trivial.

Componente que não acrescentar desempenho ou robustez deve ser candidato a simplificação/remoção.

## 10. Sensibilidade do score

Perturbar parâmetros em faixa pré-especificada e medir:

- correlação de ranking;
- mudança de composição do TOP 10/20/100;
- mudança de `nDCG`;
- mudança de recall.

Pequenas perturbações com grandes mudanças implicam `UNSTABLE_SCORE`.

## 11. Provider e metadata bias

Testar a mesma obra com origem/provider diferente mantendo metadados constantes. Testar também versões do mesmo registro com título apenas, título+abstract, título+keywords e metadados completos.

Provider deve ser tratado prioritariamente como proveniência. Peso de provider só sobrevive se houver benefício empírico independente e reproduzível.

## 12. Deduplicação

Construir conjunto dedicado com duplicatas exatas e casos de work-level equivalence: republicações, versões, traduções, preprint/final, guidelines paralelos e documentos irmãos.

Medir:

- precision de merge;
- recall de merge;
- false merges;
- missed duplicates;
- impacto de duplicatas no TOP N.

Nenhum clustering futuro pode apagar manifestações/proveniência alternativas silenciosamente.

## 13. Quarentena

Revisar amostra da quarentena e medir perda de recall atribuível ao gate. Melhorar recall somente por recuperação verificável do dado-fonte; nunca por preenchimento inventado.

## 14. Generalização

Separar `development`, `validation` e `external_test`. Incluir português, espanhol e inglês e perguntas fora das prioridades históricas. Queda importante no teste externo deve ser marcada como `CONCEPTUAL_OVERFITTING`.

## 15. Estudo de usuário

Quando o benchmark técnico justificar, comparar fluxo controle versus NutEV em tempo, workload, referências relevantes encontradas/perdidas e interpretação dos rótulos de prioridade.

Se usuários confundirem score/faixas com qualidade da evidência, a nomenclatura deve ser alterada.

## 16. Vereditos permitidos

### A — KILL

Evidência de ausência de valor suficiente ou inferioridade material no propósito alegado.

### B — DEMOTE

Funciona operacionalmente, mas benefício científico permanece não demonstrado.

### C — SCIENTIFIC_CANDIDATE

Há sinal quantitativo de benefício, porém validação externa ainda é insuficiente.

### D — VALIDATED_FOR_DEFINED_USE

Há benefício incremental reproduzível e externamente testado para tarefa delimitada. Toda conclusão D deve declarar exatamente: `Validado para: <uso específico>`.

## 17. Política de não fabricação

Nunca inventar resultados, métricas, gold standards, comparadores, DOI, performance ou concordância humana. Usar explicitamente:

- `OBSERVED`;
- `CALCULATED`;
- `INFERRED`;
- `NOT_TESTED`;
- `INSUFFICIENT_EVIDENCE`.

## 18. Formato de cada achado

`CLAIM -> BASELINE -> METHOD -> EVIDENCE -> RESULT -> UNCERTAINTY -> DECISION`

## 19. Outputs obrigatórios

- `SCIENTIFIC_VALIDATION_STATUS.md`;
- `GOLD_STANDARD_PROTOCOL.md`;
- `BENCHMARK_PLAN.md`;
- `COMPARATOR_REGISTER.md`;
- `BENCHMARK_RESULTS.csv`;
- `ABLATION_RESULTS.csv`;
- `TAXONOMY_VALIDATION.csv`;
- `DEDUPLICATION_BENCHMARK.csv`;
- `PROVIDER_CONTRIBUTION.csv`;
- `QUARANTINE_RECALL_AUDIT.csv`;
- `RANKING_SENSITIVITY.csv`;
- `ERROR_ANALYSIS.md`;
- `SCIENTIFIC_VALIDATION_REPORT.md`.

Arquivos de resultado devem permanecer vazios/templates ou conter `NOT_TESTED` até existirem dados reais.
