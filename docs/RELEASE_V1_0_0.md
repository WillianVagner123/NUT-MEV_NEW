# NutEV Reference Engine v1.0.0

**Primeira identidade estável publicada do NutEV Reference Engine.**

Data da release: `2026-08-18`

## Identidade do produto

NutEV Reference Engine é um engine de descoberta, normalização, deduplicação por identidade e priorização de referências para Nutrição do Estilo de Vida.

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT
```

O produto gera uma fila priorizada de leitura. Score e faixas A/B/C são sinais de recuperação de informação; não são avaliação de qualidade metodológica, elegibilidade científica ou recomendação clínica.

## Capacidades da release

- PubMed;
- Europe PMC;
- OpenAlex;
- Crossref;
- DOAJ;
- Semantic Scholar;
- fontes oficiais/institucionais configuradas;
- rotas nativas LILACS/BVS e SciELO;
- providers web opcionais quando credenciais estão configuradas;
- normalização de metadados;
- regra de identidade baseada em identificadores/metadados;
- matching de `keyword_taxonomy*.json`;
- focus keywords e provider weights configuráveis;
- sinais textuais de tipo documental;
- bônus leve de recência;
- exportação Markdown, CSV, JSONL e resumo JSON.

Scopus e Web of Science não são simulados.

## Deduplicação da release

A regra do ranker utiliza, em ordem:

```text
DOI -> PMID -> URL -> título normalizado
```

Quando a identidade coincide, é preferida a versão com texto descritivo mais rico.

Essa regra é determinística para os mesmos inputs, mas não deve ser interpretada como deduplicação semântica completa entre publicações relacionadas com identificadores diferentes.

## Outputs públicos

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/latest.json
```

## Metadata da release

- Version: `1.0.0`
- Published tag: `v1.0.0`
- Release commit: `5728d79b05e618897f01ba93886a17584c9f215f`
- License: MIT
- Archive metadata: `.zenodo.json`
- Citation metadata: `CITATION.cff`
- Zenodo record: `21998607`
- DOI: `10.5281/zenodo.21998607`

## Validação antes da tag

O candidato de release passou pelos checks automatizados usados no repositório para testes Python 3.12/3.13, Windows smoke, compile/lint, type checking, security scan, dependency review, CodeQL e validação de wheel/sdist antes da criação da tag.

## Imutabilidade

A tag `v1.0.0` aponta para:

```text
5728d79b05e618897f01ba93886a17584c9f215f
```

Ela permanece imutável.

Correções posteriores na `main`, incluindo ajustes de primeira execução, documentação operacional e registro do DOI real, não alteram o snapshot da release.

## Nota sobre o DOI

O registro Zenodo foi criado depois da publicação da GitHub Release. O DOI `10.5281/zenodo.21998607` foi então incorporado à metadata corrente sem mover a tag.

Futuras versões devem receber seu próprio DOI version-specific; o DOI de `v1.0.0` não deve ser reutilizado como DOI de uma nova release.
