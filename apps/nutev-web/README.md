# NutEV Web

Interface unificada para:

1. **Buscar evidências** no NutEV Reference Engine;
2. acompanhar o progresso de cada fonte durante a busca;
3. consultar os runs reais persistidos pelo Engine;
4. executar a **Validação científica** cega no mesmo servidor, do preparo da rodada ao lock da decisão de `validation`.

## Iniciar

Na raiz do repositório:

```bash
python apps/nutev-web/server.py
```

O navegador abre em `http://127.0.0.1:8765/`.

Para permitir que avaliadores em outros computadores da mesma rede local abram seus links privados, execute:

```bash
python apps/nutev-web/server.py --host 0.0.0.0
```

A coordenação científica continua protegida pelo servidor: endpoints de preparo, adjudicação, gold, métricas e lock da decisão aceitam somente requisições originadas da própria máquina do servidor. Os links dos avaliadores podem ser acessados remotamente na rede, mas cada avaliador recebe apenas o próprio token.

> Não exponha diretamente esse servidor HTTP à internet pública. Para uso fora da rede local, use uma camada HTTPS/autenticada administrada pela instituição. O backend multiusuário dedicado continua separado deste fluxo local.

## Busca interativa

A interface usa o fluxo progressivo:

1. `POST /api/search/jobs` cria um job local em background;
2. `GET /api/search/jobs/<job_id>` informa `queued`, `running`, conclusão/falha de cada provider e a etapa de deduplicação/ranking;
3. quando o job termina, o mesmo resultado canônico é persistido em disco e exibido na tela.

O endpoint síncrono `POST /api/search` continua disponível por compatibilidade.

A busca reutiliza os clientes/pipelines existentes de:

- PubMed;
- Europe PMC;
- OpenAlex;
- Crossref;
- DOAJ;
- Semantic Scholar;
- LILACS/BVS, via `tools/run_latin_sources.py`;
- SciELO, via `tools/run_latin_sources.py`.

Os providers continuam executando de forma sequencial nesta versão. A mudança é apenas de orquestração/feedback: cada fonte concluída atualiza o job, sem alterar query, deduplicação, score ou ordem científica do pipeline.

Os registros recuperados preservam `source`/`source_provider`, passam pela deduplicação canônica (`DOI -> PMID -> URL -> título normalizado`) e são priorizados com o score vigente de `config/reference_mode.json` e a taxonomia canônica.

LILACS/BVS e SciELO mantêm a regra do pipeline nativo: se a interface pública bloquear automação, a fonte aparece como `unavailable`/`failed`; o sistema nunca fabrica cobertura ou substitui silenciosamente outro provider.

Cada busca web concluída é persistida em:

```text
project_output_reference/15_web_searches/<search_id>/result.json
```

O endpoint `GET /api/searches` alimenta **Minhas buscas** a partir desses runs reais, sem depender de `localStorage`. `GET /api/searches/<search_id>` reabre um resultado já persistido sem executar a busca novamente.

### Limites atuais da busca

- Os jobs progressivos vivem em memória enquanto o servidor está rodando; um restart perde apenas o estado transitório do job. Runs já concluídos continuam persistidos no Engine.
- Scopus e Web of Science continuam não simulados; dependem de acesso licenciado.
- O score continua sendo **prioridade de leitura**, não recomendação clínica, elegibilidade científica ou avaliação de qualidade metodológica.

## Validação científica

A rota `/validation/` executa o fluxo operacional do benchmark congelado sem mostrar score, rank, taxonomia ou decisão do outro avaliador durante a avaliação inicial.

### Fluxo operacional completo

1. **Preparar rodada** — o servidor verifica perguntas congeladas, manifesto e dois packets assessor-safe e cria duas sessões privadas.
2. **Avaliação A/B** — cada avaliador recebe somente o próprio link, marca `0/1/2`, justifica e envia. O envio final trava as decisões daquele avaliador.
3. **Adjudicação** — somente discordâncias A/B aparecem. Nenhum conflito recebe nota automática; o adjudicador humano define a nota final e registra sua identificação.
4. **Gold standard** — o servidor monta o ledger bruto e o gold final e chama diretamente `tools/validate_gold_standard.py`. Sem `PASS`, o fluxo para.
5. **Métricas de validation** — somente após `gold_validated`, o servidor verifica o manifest/hashes dos rankings label-blind de coordenação e chama os avaliadores canônicos para `split=validation`, `nutev_full` vs `lexical_baseline`, com cobertura julgada até 100.
6. **Lock da decisão** — o sistema revalida a cadeia de hashes e deriva deterministicamente:
   - `CONTINUATION_CRITERIA_PASS` -> `CONTINUE_TO_EXTERNAL`;
   - `CONTINUATION_CRITERIA_FAIL` -> `STOP_AT_B`.
7. **External test** — continua selado. O lock de `validation` nunca libera, lê ou calcula o conjunto externo automaticamente.

### Persistência e retomada

A rodada, decisões e outputs científicos ficam em diretórios privados ignorados pelo Git:

```text
project_output_reference/16_validation_server/
```

O SQLite preserva o estado da rodada entre reinicializações. Um restart do servidor não apaga avaliações já salvas, submissões travadas, adjudicação, gold, métricas ou decisão bloqueada.

Os rankings de coordenação usados somente depois do gold ficam em:

```text
validation/data/validation_coordinator_audit/
```

Esse diretório é ignorado pelo Git e não deve ser entregue aos avaliadores. Também pode ser substituído por `NUTEV_VALIDATION_RANKINGS_DIR`.

### Regras que não podem ser quebradas

- nunca envie os dois links privados à mesma pessoa;
- avaliadores não recebem audit files, sistemas, ranks, scores ou taxonomia;
- `external_test` permanece fora da análise até existir uma decisão de `validation` bloqueada;
- nenhum script inventa relevância humana ou adjudica conflito automaticamente;
- `PASS` do gold valida completude/coerência do processo, não desempenho do NutEV;
- `CONTINUE_TO_EXTERNAL` é apenas autorização metodológica para a etapa seguinte; não é validação clínica nem prova de discovery recall.
