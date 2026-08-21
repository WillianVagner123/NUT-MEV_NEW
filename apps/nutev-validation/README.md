# NutEV Validation

Interface web do **fluxo humano cego de validação científica** do NutEV Evidence Engine.

O caminho operacional canônico não exige que avaliadores carreguem, editem ou exportem CSVs. O coordenador prepara a rodada no site, distribui dois links privados, acompanha apenas o progresso, conduz a adjudicação, valida o gold standard, calcula a etapa `validation` e bloqueia a decisão pré-especificada.

O sistema permanece cientificamente em:

```text
B — DEMOTE
```

até que julgamentos humanos independentes reais sejam concluídos e os critérios pré-registrados sejam satisfeitos. **Prontidão do software não é promoção científica.**

## Caminho operacional canônico

Inicie o servidor unificado na raiz do repositório:

```bash
python apps/nutev-web/server.py
```

Abra:

```text
http://127.0.0.1:8765/validation/
```

O fluxo principal é:

```text
PREPARAR RODADA
    ↓
AVALIAÇÃO CEGA A / B
    ↓
SUBMIT + LOCK INDIVIDUAL
    ↓
ADJUDICAÇÃO HUMANA DOS CONFLITOS
    ↓
GOLD STANDARD + VALIDATOR CANÔNICO
    ↓
MÉTRICAS SOMENTE DO SPLIT validation
    ↓
LOCK DA DECISÃO PRÉ-ESPECIFICADA
```

A decisão de `validation` não é escolhida manualmente:

```text
CONTINUATION_CRITERIA_PASS
    -> CONTINUE_TO_EXTERNAL

CONTINUATION_CRITERIA_FAIL
    -> STOP_AT_B
```

O `external_test` continua selado em ambos os casos até uma ação posterior e separada do custodiante.

## Avaliadores em outros computadores

Para receber conexões da rede local:

```bash
python apps/nutev-web/server.py --host 0.0.0.0
```

Mantenha a coordenação aberta localmente e, em **Endereço dos avaliadores**, informe uma URL que os outros computadores consigam abrir, por exemplo:

```text
http://192.168.1.50:8765
```

Enquanto esse endereço não estiver configurado em uma sessão de coordenação aberta por `localhost`, `127.0.0.1` ou `0.0.0.0`, os botões **Copiar link privado** ficam bloqueados para impedir o envio acidental de um link inutilizável.

Cada link contém somente o token daquele avaliador em `#token=...`. O fragmento não é enviado ao servidor nos logs HTTP; a página do avaliador o move para o header `Authorization` durante as chamadas de API.

Nunca entregue os dois links à mesma pessoa.

## O que o avaliador vê

Cada avaliador recebe somente:

- pergunta congelada e contexto de elegibilidade;
- referência cega;
- título, resumo e metadados bibliográficos permitidos;
- escala `0 / 1 / 2`;
- campo de justificativa;
- opção de revisar depois;
- progresso e envio final.

O avaliador **não recebe**:

- rank do NutEV;
- score do NutEV;
- sistema de origem do item;
- membership `nutev_full`/baseline;
- taxonomia usada no ranking;
- decisão do outro avaliador;
- audit artifact;
- resultados do `external_test`.

## Submit e lock

O envio final exige:

- todos os itens julgados;
- justificativa em todos os itens;
- timestamp de decisão;
- `blind_to_nutev = true` em todos os itens.

Depois do envio, as decisões daquele avaliador ficam travadas.

Quando os dois avaliadores terminam, a rodada avança para `ready_for_adjudication`.

## Adjudicação

A tela de adjudicação mostra **somente discordâncias**.

- concordâncias não são reabertas;
- nenhum algoritmo seleciona a nota vencedora;
- cada conflito exige nota humana final `0/1/2`;
- exige identificação do adjudicador e timestamp;
- a decisão é armazenada separadamente dos julgamentos brutos A/B.

## Gold standard

Após a adjudicação completa, o servidor gera internamente os artefatos canônicos e chama diretamente:

```text
tools/validate_gold_standard.py
```

O fluxo só avança se o validator retornar `PASS` e confirmar cobertura completa e pelo menos dois avaliadores por referência.

`PASS` nessa etapa significa **completude e coerência processual**, não que os julgamentos humanos sejam cientificamente corretos e não que o NutEV tenha desempenho superior.

## Métricas de validation

Depois de `gold_validated`, os rankings label-blind de coordenação são lidos de uma área privada e ignorada pelo Git:

```text
validation/data/validation_coordinator_audit/
```

ou de `NUTEV_VALIDATION_RANKINGS_DIR`.

Antes de calcular qualquer métrica, o sistema verifica:

- `label_blind_build = true`;
- `gold_standard_consumed = false`;
- candidate SHA congelado;
- SHA das perguntas;
- SHA dos rankings.

A avaliação é fixada em:

```text
split = validation
candidate = nutev_full
baseline = lexical_baseline
judged depth = 100
```

usando as ferramentas canônicas:

```text
tools/evaluate_scientific_validation.py
tools/compare_scientific_benchmark.py
```

Nenhum label ou resultado do `external_test` é consumido nesta etapa.

## Lock da decisão

Após `validation_metrics_complete`, o sistema revalida os hashes de todos os outputs e cria:

```text
VALIDATION_DECISION.json
```

A decisão é derivada deterministicamente do gate pré-registrado. O sistema registra explicitamente:

```text
external_test_released = false
external_test_labels_consumed = false
external_test_metrics_calculated = false
automatic_external_release = false
```

## Persistência privada

O estado operacional fica em:

```text
project_output_reference/16_validation_server/
```

incluindo SQLite e outputs da rodada. Esse caminho é ignorado pelo Git.

Um restart do servidor preserva avaliações salvas, submissões travadas, adjudicação, gold, métricas e decisão bloqueada. Apenas jobs transitórios de busca comum vivem em memória.

## Identidade científica congelada atual

```text
candidate runtime:
6aa7a5fe6009776e611ca3e1506486606b05f4f6

questions SHA-256:
55a0f654e49cb5a9b10249c373df168cac585167a245b828d667c7724fb64589
```

Mudanças nesses identificadores constituem uma rodada científica diferente e devem ser documentadas.

## Segurança e limites de implantação

O servidor local protege preparo de rodada, adjudicação, gold, métricas e lock da decisão com restrição de loopback. Os endpoints do avaliador são protegidos pelo token individual.

Para uso em LAN, não é necessário Supabase.

**Não exponha diretamente o servidor HTTP local à internet pública.** Para revisão fora da rede local, coloque o sistema atrás de HTTPS/autenticação institucional ou implemente um backend multiusuário dedicado.

## Backend Supabase legado/opcional

Os arquivos `app.js`, `supabase/schema.sql` e a documentação histórica de Supabase permanecem no repositório como **implementação alternativa/legada e base para uma futura implantação multiusuário hospedada**. Eles não são o caminho canônico da rodada atual e não devem ser confundidos com o fluxo site-first servido por `apps/nutev-web/server.py`.

O modo legado nunca deve receber o audit artifact nem qualquer material de `external_test` antes do gate metodológico apropriado.
