# NutEV Web

Interface unificada para:

1. **Buscar evidências** no NutEV Reference Engine;
2. acompanhar o progresso de cada fonte durante a busca;
3. consultar os runs reais persistidos pelo Engine;
4. abrir o módulo existente de **Validação científica** no mesmo servidor.

## Iniciar

Na raiz do repositório:

```bash
python apps/nutev-web/server.py
```

O navegador abre em `http://127.0.0.1:8765/`.

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

### Limites atuais

- Os jobs progressivos vivem em memória enquanto o servidor está rodando; um restart perde apenas o estado transitório do job. Runs já concluídos continuam persistidos no Engine.
- Scopus e Web of Science continuam não simulados; dependem de acesso licenciado.
- O score continua sendo **prioridade de leitura**, não recomendação clínica, elegibilidade científica ou avaliação de qualidade metodológica.

## Validação científica

A rota `/validation/` serve o módulo `apps/nutev-validation` existente. Isso unifica a experiência sem misturar score/rank de uma busca comum do usuário com os julgamentos cegos do benchmark científico congelado.
