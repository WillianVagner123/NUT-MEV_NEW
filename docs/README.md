# Documentação do NutEV Reference Engine

Esta pasta contém a documentação operacional, técnica, de release e de proveniência do produto suportado atualmente.

## Ordem recomendada de leitura

1. [`POP_USO_NUTEV_REFERENCE_ENGINE.md`](POP_USO_NUTEV_REFERENCE_ENGINE.md) — como instalar, atualizar, executar, verificar sucesso e recuperar falhas.
2. [`ARCHITECTURE.md`](ARCHITECTURE.md) — arquitetura real do pipeline, regras de deduplicação, scoring e contratos de saída.
3. [`SEARCH_PROVIDERS.md`](SEARCH_PROVIDERS.md) — providers, limites, credenciais, estados `failed`/`unavailable` e comportamento de cobertura.
4. [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) — limitações conhecidas e interpretação responsável dos outputs.
5. [`VALIDATED_WINDOWS_RUN_2026-08-18.md`](VALIDATED_WINDOWS_RUN_2026-08-18.md) — registro de uma execução real bem-sucedida.

## Release, DOI e proveniência

- [`RELEASE_V1_0_0.md`](RELEASE_V1_0_0.md) — identidade e conteúdo da release estável `v1.0.0`.
- [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) — checklist para futuras releases.
- [`ZENODO_SETUP.md`](ZENODO_SETUP.md) — publicação GitHub/Zenodo e regra de DOI.
- [`PROVENANCE_AND_LICENSE.md`](PROVENANCE_AND_LICENSE.md) — proveniência do código e fronteira de licenciamento.
- [`REFERENCE_ENGINE_CLEANUP_AUDIT.md`](REFERENCE_ENGINE_CLEANUP_AUDIT.md) — auditoria histórica da redução do repositório ao Reference Engine.

## Produto suportado

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT
```

Entrada operacional no Windows:

```text
Iniciar-NutEV-Windows.bat
```

Fluxo interno:

```text
Iniciar-NutEV-Windows.bat
  -> RODAR_TUDO.cmd
     -> run_everything_now.cmd
        -> tools/run_everything_now.py
     -> tools/run_latin_sources.py
     -> tools/rank_references.py
```

## Saídas canônicas

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/latest.json
```

## Fronteira de interpretação

O Reference Engine é uma ferramenta de **descoberta e priorização de leitura**.

Ele não substitui:

- triagem científica;
- avaliação metodológica;
- avaliação de risco de viés;
- síntese de evidências;
- decisão clínica;
- julgamento humano sobre a pertinência de uma referência.

A deduplicação atual é orientada por DOI, PMID, URL e, como fallback, título normalizado. Ela não garante unicidade semântica entre publicações relacionadas.

## Evidência operacional registrada

Uma execução real no Windows, em 18/08/2026, terminou com status `COMPLETE`, `8.702` registros de entrada no ranking, `8.702` registros únicos segundo a regra ativa, `115` grupos de taxonomia carregados e TOP 100 exportado.

Esses números descrevem uma execução observada, não uma promessa de volume ou cobertura para execuções futuras.

## Release publicada

- versão: `1.0.0`
- tag: `v1.0.0`
- release commit: `5728d79b05e618897f01ba93886a17584c9f215f`
- Zenodo record: `21998607`
- DOI: `10.5281/zenodo.21998607`

A `main` pode conter correções pós-release. A tag publicada permanece imutável.
