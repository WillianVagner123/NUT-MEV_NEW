# Gold Standard Protocol

## Objetivo

Construir um conjunto de relevância independente do NutEV Reference Engine para testar descoberta, priorização e classificação sem validação circular.

## Princípio de independência

O Engine não pode definir os labels finais. A taxonomia, o score, a faixa, a origem do sistema e a posição NutEV não devem ser mostrados aos avaliadores durante a rotulagem inicial.

O conjunto de documentos a julgar pode ser formado por pooling de múltiplos sistemas e por busca independente, mas a apresentação aos avaliadores deve remover ordem, score e identidade do sistema que recuperou cada item.

## Perguntas

Usar `validation/templates/QUESTIONS_TEMPLATE.csv` e congelar cada pergunta com:

- `question_id` estável;
- texto completo da pergunta;
- split (`development`, `validation`, `external_test`);
- população/contexto;
- intervenção/exposição;
- comparador, quando aplicável;
- desfecho/construto;
- janela temporal;
- idiomas aceitos;
- tipos documentais aceitos;
- data de congelamento.

As perguntas de `external_test` devem ser congeladas antes de qualquer ajuste final de pesos ou regras. A seleção e redação final das perguntas exigem aprovação humana/editorial; o software não pode declarar um conjunto auto-gerado como independente apenas por ter sido produzido fora do ranking.

## Estratificação mínima

O conjunto deve cobrir, quando viável:

- padrões alimentares;
- prevenção/risco cardiometabólico;
- diabetes;
- obesidade;
- comportamento e adesão;
- food literacy/culinária;
- determinantes sociais/ambiente alimentar;
- implementação/modelos de cuidado;
- pelo menos dois temas deliberadamente fora dos focos históricos do Engine;
- inglês, português e espanhol quando a pergunta permitir.

A estratificação organiza as perguntas; ela não pré-determina quais referências são relevantes.

## Duas camadas de evidência

### Common-pool prioritization

A rodada humana primária julga a união top 100 de `nutev_full` e `lexical_baseline` para cada pergunta, conforme a pré-especificação e o amendment pré-resultados. Serve para precision, nDCG, AP, MRR e workload **condicionais ao pool**.

O recall calculado apenas dentro desse pool não deve ser descrito como recall bibliográfico global.

### Discovery coverage

Inclui referências relevantes obtidas por rotas independentes que podem estar ausentes do corpus NutEV. Esta camada é necessária para qualquer alegação de cobertura/descoberta.

A procedência da referência externa deve ser preservada sem expor aos avaliadores qual sistema está sendo testado durante o julgamento de relevância.

## Construção do pool cego

`tools/build_blinded_judgment_pool.py` recebe os rankings label-blind e os metadados do runtime congelado.

Por padrão ele usa somente os sistemas primários:

```text
nutev_full,lexical_baseline
```

com profundidade 100 por sistema. O arquivo cego contém metadados bibliográficos e identidade canônica, mas não contém score, rank ou sistema de origem. Um segundo arquivo de auditoria preserva `system_membership` e posições e deve ser mantido fora do alcance dos avaliadores até que os julgamentos iniciais estejam travados.

## Pacotes independentes de avaliação

`tools/build_assessor_packets.py` transforma o pool cego em um pacote separado para cada `assessor_id` pseudonimizado.

Regras:

- pelo menos dois assessor IDs;
- mesmo conjunto de referências para todos;
- ordem determinística específica de cada assessor;
- sem `system`, `rank`, `system_score`, `reference_score`, `reference_rank`, `score_breakdown`, taxonomia ou `system_membership`;
- campos `relevance_grade`, `reason` e `decision_timestamp` começam vazios;
- `blind_to_nutev = true` é registrado no pacote;
- um assessor não recebe a decisão do outro antes de finalizar o próprio pacote.

## Rotulagem bruta

Para benchmark-grade gold standard, cada par `question_id/reference_id` do **pool cego completo** deve receber pelo menos dois julgamentos independentes.

Arquivo consolidado:

```text
validation/data/ASSESSMENTS.csv
```

Template:

```text
validation/templates/ASSESSMENTS_TEMPLATE.csv
```

Escala:

- `0` = irrelevante;
- `1` = relevante periférico/útil;
- `2` = diretamente relevante/referência-chave.

Cada decisão registra:

- `question_id`;
- `reference_id`;
- `assessor_id` pseudonimizado;
- `relevance_grade`;
- justificativa (`reason`);
- timestamp;
- `blind_to_nutev = true`;
- identificadores/metadados bibliográficos disponíveis para auditoria.

O assessor pode ver título/abstract e os critérios da pergunta; não deve ver `reference_score`, `reference_rank`, taxonomia NutEV, sistema de origem do resultado ou decisão do outro assessor.

## Adjudicação

Os julgamentos brutos nunca são sobrescritos.

Se os avaliadores concordarem, o gold final deve registrar `adjudication_status = AGREED` e preservar a nota comum.

Se discordarem, a decisão final exige adjudicação humana explícita:

- `adjudication_status = RESOLVED`;
- `adjudicator_id`;
- `adjudication_timestamp`;
- `relevance_grade` final 0/1/2.

Nenhum script pode escolher automaticamente qual assessor está correto.

## Gold standard final e cobertura obrigatória do pool

Arquivo canônico consumido pelo avaliador de métricas:

```text
validation/data/GOLD_STANDARD.csv
```

Template:

```text
validation/templates/GOLD_STANDARD_TEMPLATE.csv
```

O arquivo final tem **uma linha por `question_id/reference_id`**. Isso o separa do ledger bruto com múltiplos avaliadores e evita que discordâncias sejam silenciosamente interpretadas como múltiplas verdades.

`tools/validate_gold_standard.py` recebe obrigatoriamente:

- `--pool`: o pool cego original;
- `--assessments`: o ledger bruto consolidado;
- `--gold`: o gold final adjudicado.

O validator exige igualdade exata entre o conjunto de pares pergunta/referência do pool, dos julgamentos e do gold. Assim, um item não pode desaparecer simultaneamente dos julgamentos e do gold e ainda produzir `PASS`.

Ele também exige pelo menos dois assessores independentes por item, cegamento declarado e adjudicação humana explícita de conflitos. Um `PASS` valida cobertura/processo/coerência; não significa que o julgamento humano é cientificamente correto.

## Identidade da referência

Para outputs do runtime congelado, preservar o `reference_id` derivado do contrato canônico daquele runtime. Para referências externas do discovery benchmark, preservar também DOI/PMID/PMCID/URL/título e uma chave manual controlada quando necessário.

Reconciliação entre uma referência externa e um item do ranking deve ser explícita e auditável. Não aproximar por similaridade sem registrar a decisão e não usar a posição no ranking como identidade.

## Prevenção de leakage

Separar:

- `development`: pode ser usado para depuração/calibração declarada;
- `validation`: pode orientar escolha entre candidatos previamente definidos;
- `external_test`: aberto somente após freeze e pré-especificação final.

Nenhum label de `external_test` pode alterar query, taxonomia, peso, regra de identidade ou guardrail do candidato congelado.

O harness `tools/build_scientific_benchmark_rankings.py` não recebe o gold standard como entrada e registra `gold_standard_consumed = false` no manifesto da construção dos rankings.

O audit do pool e qualquer arquivo contendo sistema/rank permanecem segregados dos assessores durante a avaliação inicial.

## Tamanho e encerramento

O tamanho das perguntas e do pool julgado deve ser definido por viabilidade e precisão desejada antes da análise final. Não encerrar a rotulagem porque os resultados parecem favoráveis ou desfavoráveis.

Para o endpoint primário, o pool top 100 candidato+baseline precisa de cobertura humana completa. Uma redução de profundidade só pode ocorrer por amendment registrado antes dos rótulos da rodada afetada.

## Auditoria mínima antes de calcular métricas

1. perguntas aprovadas e congeladas;
2. runtime candidate SHA registrado;
3. rankings construídos sem labels;
4. pool primário cego construído e audit preservado separadamente;
5. pacotes independentes gerados para dois ou mais avaliadores;
6. dois ou mais julgamentos por todo par do pool;
7. conflitos adjudicados humanamente;
8. raw assessments preservados;
9. `validate_gold_standard.py` com cobertura de pool 100% e `status: PASS`;
10. somente então executar `tools/evaluate_scientific_validation.py` e a comparação pareada.

## Estado atual

**INFRASTRUCTURE_READY / HUMAN_LABELS_NOT_AVAILABLE.**

Nenhum gold standard independente real foi registrado. Portanto nenhuma métrica científica deve ser preenchida ainda e o veredito permanece **B — DEMOTE**.
