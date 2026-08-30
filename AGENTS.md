# AGENTS.md — NutEV Reference Engine

Este arquivo define o escopo e as invariantes que agentes automatizados devem preservar ao modificar este repositório.

## Produto suportado

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT
```

O NutEV Reference Engine coleta metadados de referências, preserva identidade de provider, normaliza registros, aplica deduplicação por identidade, cruza taxonomia/focus terms, calcula prioridade de leitura e exporta resultados estruturados.

## Invariantes não negociáveis

1. Nunca fabricar provider results, contagens, identificadores, URLs, DOIs, PMIDs ou evidência de execução.
2. Falhas, rate limits, ausência de credenciais e mudanças de interface devem permanecer explícitos.
3. Scopus e Web of Science nunca devem ser simulados.
4. Ranking é prioridade de leitura; não é recomendação clínica, elegibilidade científica ou qualidade metodológica.
5. `source`/`source_provider` deve sobreviver ao fluxo até os outputs.
6. Queries, limites, taxonomia e pesos devem permanecer versionados e inspecionáveis.
7. Não descrever a regra atual como deduplicação semântica completa.
8. Mudanças no scoring devem atualizar testes e `docs/ARCHITECTURE.md`.
9. Mudanças no comportamento do usuário devem atualizar README/POP/documentação correspondente.
10. Outputs públicos devem respeitar a allowlist do ranker.
11. Nunca inventar DOI, ORCID, afiliação, funding, autoria ou resultado de teste.
12. Não versionar segredos, dados privados ou texto completo protegido sem direito de redistribuição.
13. Tags e releases publicadas são imutáveis.

## Contexto compartilhado para agentes

Para trabalho científico ou operacional no Artigo 1, agentes ChatGPT/Codex, Claude e similares devem usar a mesma fonte de verdade:

1. `AI_CONTEXT.md` — ponto de entrada compartilhado;
2. `ARTICLE1_SEARCH_MASTER.md` — estado humano canônico da busca;
3. `config/nutev/article1_search_master_v1.json` — estado machine-readable;
4. quando existir, `project_output_reference/agent_context/article1/CONTEXT_MANIFEST.json` — snapshot vivo de produção.

O bundle de agentes é somente navegação/contexto. Ele não autoriza PRESS, GF-10, freeze, inclusão/exclusão ou PRISMA e não deve expor full text, Bank rank/score/tier ou machine relevance score/band.

## Runtime canônico

- `Iniciar-NutEV-Windows.bat`
- `RODAR_TUDO.cmd`
- `run_everything_now.cmd`
- `tools/run_everything_now.py`
- `tools/run_latin_sources.py`
- `tools/rank_references.py`
- `config/reference_search.json`
- `config/reference_mode.json`
- `config/keyword_taxonomy*.json`
- `src/nutev/search/`

## Outputs canônicos

- `project_output_reference/reference_ranking/TOP_REFERENCIAS.md`
- `project_output_reference/reference_ranking/reference_ranking.csv`
- `project_output_reference/reference_ranking/reference_ranking.jsonl`
- `project_output_reference/reference_ranking/latest.json`

## Regra de identidade atual

```text
DOI -> PMID -> URL -> título normalizado
```

Quando a identidade coincide, é preferida a versão com texto descritivo mais rico.

Registros semanticamente equivalentes com identificadores diferentes podem permanecer separados.

## Workflow de mudança

Para alterações não triviais:

1. verificar o SHA atual de `main`;
2. criar branch dedicada;
3. limitar o diff ao escopo declarado;
4. adicionar/ajustar testes para mudança de contrato;
5. atualizar documentação quando houver comportamento público afetado;
6. obter CI/security/build no SHA candidato;
7. abrir PR;
8. não fazer merge com checks necessários falhando;
9. não mover tags publicadas.

## Mudanças de provider

Exigir:

- identidade preservada;
- falha explícita;
- nenhum fallback silencioso rotulado como outro provider;
- nenhum bypass de controle de acesso;
- documentação de credenciais/limites/status atualizada.

## Mudanças de ranking

Se alterar taxonomia, pesos, focus terms, tipo documental, recência, identidade/deduplicação, tiers ou schema:

- atualizar `docs/ARCHITECTURE.md`;
- revisar `docs/KNOWN_LIMITATIONS.md`;
- adicionar regressão em `nutev_tests`;
- documentar impacto no README/POP quando visível ao operador.

## Release atual

- versão publicada: `1.0.0`;
- tag: `v1.0.0`;
- release commit: `5728d79b05e618897f01ba93886a17584c9f215f`;
- Zenodo record: `21998607`;
- DOI: `10.5281/zenodo.21998607`.

A `main` contém correções pós-release e documentação. Isso não altera o snapshot arquivado.

## Futuras releases

Versão, tag, GitHub Release, `CITATION.cff`, `.zenodo.json`, changelog e release notes devem referir-se à mesma identidade de release.

Um novo DOI version-specific só deve ser registrado depois que o serviço de arquivo realmente o emitir. Nunca reutilizar o DOI de `v1.0.0` como DOI de depósito de uma versão futura.
