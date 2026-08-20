# NutEV Web

Interface unificada para:

1. **Buscar evidências** no NutEV Reference Engine;
2. consultar o histórico local de buscas;
3. abrir o módulo existente de **Validação científica** no mesmo servidor.

## Iniciar

Na raiz do repositório:

```bash
python apps/nutev-web/server.py
```

O navegador abre em `http://127.0.0.1:8765/`.

## Busca interativa

O endpoint `POST /api/search` recebe uma pergunta e consulta diretamente os clientes existentes de:

- PubMed;
- Europe PMC;
- OpenAlex;
- Crossref;
- DOAJ;
- Semantic Scholar.

Os registros recuperados preservam `source`/`source_provider`, passam pela deduplicação canônica (`DOI -> PMID -> URL -> título normalizado`) e são priorizados com o score vigente de `config/reference_mode.json` e a taxonomia canônica.

Falhas de provider aparecem explicitamente no resultado. Nenhum provider é simulado.

### Limites atuais

- LILACS/BVS e SciELO continuam no estágio canônico separado (`tools/run_latin_sources.py`) e ainda não foram ligados à consulta web interativa.
- Scopus e Web of Science continuam não simulados; dependem de acesso licenciado.
- A busca web é síncrona nesta primeira versão. Para produção multiusuário, o próximo passo é fila/job persistente com progresso.
- O score continua sendo **prioridade de leitura**, não recomendação clínica, elegibilidade científica ou avaliação de qualidade metodológica.

## Validação científica

A rota `/validation/` serve o módulo `apps/nutev-validation` existente. Isso unifica a experiência sem misturar score/rank do Engine com os julgamentos cegos do benchmark.
