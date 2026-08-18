## Resumo

<!-- O que muda e por quê? -->

## Tipo de mudança

- [ ] Provider / busca
- [ ] Ranking / taxonomia / deduplicação
- [ ] Output contract
- [ ] Bug fix
- [ ] Documentação
- [ ] Build / CI / dependências
- [ ] Refactor / limpeza
- [ ] Release metadata

## Impacto

<!-- O que muda para operador, desenvolvedor ou output? -->

## Contratos afetados

- [ ] `config/reference_search.json`
- [ ] `config/reference_mode.json`
- [ ] `config/keyword_taxonomy*.json`
- [ ] providers / `src/nutev/search/`
- [ ] `tools/run_everything_now.py`
- [ ] `tools/run_latin_sources.py`
- [ ] `tools/rank_references.py`
- [ ] outputs / schema
- [ ] documentação apenas

## Integridade do Reference Engine

- [ ] Nenhum resultado, identificador, DOI, contagem ou evidência de execução foi fabricado.
- [ ] Falhas e providers indisponíveis permanecem explícitos.
- [ ] Source/provider identity é preservada.
- [ ] Scopus/Web of Science não são simulados sem acesso real.
- [ ] Ranking continua sendo prioridade de leitura, não decisão científica/ clínica automática.
- [ ] A deduplicação atual não é descrita como semanticamente completa sem implementação/evidência correspondente.
- [ ] Tags/releases publicadas não foram movidas.

## Segurança e dados

- [ ] Nenhum segredo, token, chave ou `.env` real foi versionado.
- [ ] Nenhum dado pessoal/paciente/participante foi incluído.
- [ ] Nenhum texto completo protegido foi adicionado sem direito de redistribuição.
- [ ] Nenhum output local grande/privado foi commitado por acidente.

## Validação

Marque o que foi realmente executado:

- [ ] `PYTHONPATH=src python -m pytest -q nutev_tests`
- [ ] `python -m compileall -q src tools nutev_tests`
- [ ] `ruff check src tools nutev_tests --select F,E9`
- [ ] Python 3.12 CI
- [ ] Python 3.13 CI
- [ ] Windows smoke
- [ ] typecheck
- [ ] security scan
- [ ] dependency review
- [ ] CodeQL
- [ ] release artifact validation

Se algum check não foi executado, explicar abaixo em vez de marcar.

## Documentação

- [ ] Mudança visível ao usuário está documentada.
- [ ] Se scoring/identity/output mudou, `docs/ARCHITECTURE.md` foi atualizado.
- [ ] Se limitações mudaram, `docs/KNOWN_LIMITATIONS.md` foi revisado.
- [ ] Se provider mudou, `docs/SEARCH_PROVIDERS.md` foi revisado.

## Limitações que permanecem

<!-- O que este PR não resolve? -->

## Notas para revisão

<!-- Pontos que merecem atenção específica. -->
