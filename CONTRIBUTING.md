# Contribuindo com o NutEV Reference Engine

O NutEV Reference Engine tem escopo deliberadamente restrito: descoberta de referências, normalização, deduplicação por identidade, ranking e exportação para Nutrição do Estilo de Vida.

## Princípios do produto

Toda contribuição deve preservar estes invariantes:

1. Nunca fabricar resultados, contagens, identificadores, URLs ou metadados de provider.
2. Manter falhas, rate limits, credenciais ausentes e mudanças de interface explícitos.
3. Preservar `source`/`source_provider` até os outputs.
4. Nunca simular Scopus ou Web of Science quando não houver acesso real.
5. Tratar o score como prioridade de leitura, não como decisão clínica ou científica.
6. Manter consultas, taxonomia e pesos versionados e inspecionáveis.
7. Não descrever deduplicação por identificadores como deduplicação semântica completa.
8. Não comprometer segredos, dados pessoais/participantes ou textos completos sem direito de redistribuição.
9. Não mover tags/releases publicadas.
10. Documentar qualquer mudança visível para o usuário.

## Ambiente de desenvolvimento

Requer Python 3.12 ou 3.13.

```bash
python -m pip install -e ".[dev]"
```

Testes:

```bash
PYTHONPATH=src python -m pytest -q nutev_tests
```

Compilação e lint:

```bash
python -m compileall -q src tools nutev_tests
ruff check src tools nutev_tests --select F,E9
```

O CI do repositório também executa validações adicionais como Python 3.12/3.13, Windows smoke, type checking, security scan, dependency review, CodeQL e validação de artefatos.

## Caminho operacional

```text
Iniciar-NutEV-Windows.bat
  -> RODAR_TUDO.cmd
     -> run_everything_now.cmd
        -> tools/run_everything_now.py
     -> tools/run_latin_sources.py
     -> tools/rank_references.py
```

## Mudanças em providers

Uma alteração em provider deve:

- preservar identidade da fonte;
- registrar erro/indisponibilidade sem transformar falha em zero-result evidence;
- respeitar termos e limites do serviço;
- não inserir dados de outro provider sob o rótulo do provider alterado;
- adicionar/ajustar teste quando houver mudança de contrato;
- atualizar `docs/SEARCH_PROVIDERS.md` quando o comportamento público mudar.

## Mudanças no ranking

Alterações em:

- regra de identidade/deduplicação;
- taxonomia;
- focus keywords;
- pesos por provider;
- sinais de tipo documental;
- bônus de recência;
- faixas A/B/C;
- schema de exportação;

devem atualizar testes e `docs/ARCHITECTURE.md`.

Quando uma alteração muda a interpretação do output, atualizar também `README.md`, a POP e `docs/KNOWN_LIMITATIONS.md` quando aplicável.

## Mudanças de documentação

Documentação deve descrever comportamento implementado ou evidência observada.

Não registrar como fato:

- execução que não aconteceu;
- DOI/ORCID/afiliação não verificados;
- provider não implementado;
- cobertura exaustiva não demonstrada;
- promessa de ausência de duplicatas semânticas;
- teste local que não foi executado.

## Pull requests

Um PR deve explicar:

- o problema;
- o que mudou;
- impacto para operador/desenvolvedor;
- arquivos/contratos afetados;
- validações executadas;
- limitações que permanecem.

Use uma branch dedicada e mantenha o diff dentro do escopo declarado.

## Outputs gerados

Não versione `project_output_reference` por padrão. Outputs de execução são artefatos locais e podem conter grandes volumes de metadados/URLs externos.

Fixtures de teste devem ser pequenas, deliberadas e sem conteúdo protegido.

## Segurança

Leia `SECURITY.md`.

Nunca coloque chaves reais em:

- `.env.example`;
- issues;
- PRs;
- logs de teste;
- screenshots;
- fixtures.

## Documentação relacionada

- `README.md`
- `AGENTS.md`
- `docs/README.md`
- `docs/ARCHITECTURE.md`
- `docs/SEARCH_PROVIDERS.md`
- `docs/KNOWN_LIMITATIONS.md`
- `SECURITY.md`
- `NOTICE.md`
