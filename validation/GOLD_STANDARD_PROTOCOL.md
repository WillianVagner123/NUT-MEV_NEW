# Gold Standard Protocol

## Objetivo

Construir um conjunto de relevância independente do NutEV Reference Engine para testar descoberta, priorização e classificação sem validação circular.

## Princípio de independência

O Engine não pode definir os labels finais. A taxonomia, o score e a ordem NutEV não devem ser mostrados aos avaliadores durante a rotulagem inicial.

## Estratificação mínima

O conjunto deve cobrir pelo menos:

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

A estratificação não deve ser usada para pré-determinar quais referências são relevantes.

## Construção das perguntas

Cada pergunta recebe:

- `question_id` estável;
- texto completo da pergunta;
- população/contexto, quando aplicável;
- intervenção/exposição;
- comparador, se relevante;
- desfecho/construto;
- janela temporal, se houver;
- idiomas aceitos;
- tipos documentais aceitos;
- data de congelamento.

As perguntas do conjunto `external_test` devem ser congeladas antes de qualquer ajuste final de pesos.

## Rotulagem

Preferência: dois avaliadores independentes.

Escala recomendada:

- `0` = irrelevante;
- `1` = relevante periférico/útil;
- `2` = diretamente relevante/referência-chave.

Para métricas binárias, `1` e `2` contam como relevantes. Para nDCG, preservar o grau 0/1/2.

Cada decisão registra:

- `assessor_id` pseudonimizado;
- `reference_id`;
- `relevance_grade`;
- `reason`;
- `decision_timestamp`;
- `conflict_status`.

## Adjudicação

Conflitos devem ser resolvidos por regra declarada previamente. A decisão adjudicada deve preservar os labels originais para cálculo de concordância.

## Identidade da referência

Prioridade para identificador canônico:

1. DOI normalizado e verificado;
2. PMID;
3. PMCID;
4. URL persistente verificável;
5. chave bibliográfica controlada criada manualmente.

Nunca usar posição no ranking como identidade.

## Prevenção de leakage

Separar:

- `development`: pode ser usado para depuração/calibração;
- `validation`: pode orientar escolha entre candidatos previamente definidos;
- `external_test`: aberto apenas após freeze final.

Nenhum label de `external_test` pode alterar query, taxonomia, peso ou regra antes do veredito.

## Tamanho

O tamanho deve ser definido por viabilidade e precisão desejada antes da análise. Não encerrar a coleta porque o resultado ficou favorável ou desfavorável.

## Arquivo canônico

Usar `validation/data/GOLD_STANDARD.csv` com o schema documentado em `validation/templates/GOLD_STANDARD_TEMPLATE.csv`.

## Estado atual

`NOT_TESTED` — nenhum gold standard independente foi registrado no repositório nesta data.
