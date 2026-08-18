# Taxonomia canônica do NutEV Reference Engine

Versão canônica: `2026-08-v2`

## Objetivo

A taxonomia organiza as referências por **tema/intervenção**, **contexto/implementação**, **condição clínica** e **desfecho**. Ela serve para classificação, navegação e rankeamento dentro de cada domínio.

A taxonomia **não representa qualidade metodológica, nível de evidência, elegibilidade de revisão ou recomendação clínica**.

## Por que a taxonomia foi reorganizada

O repositório acumulou, ao longo do desenvolvimento, um arquivo-base e diversos `keyword_taxonomy_supplement*.json`. Esses arquivos preservam vocabulário útil, mas também carregam estruturas históricas como `workstreams.busca1`, `busca2a`, `busca2b`, `a3` e `artigo3_framework`.

O ranker antigo achatava recursivamente todos os caminhos dos arquivos `keyword_taxonomy*.json`. Como consequência, termos repetidos em workstreams, outcomes e supplements podiam criar grupos extras de score, e nomes de projetos históricos apareciam no output público.

A organização atual separa duas camadas:

1. **Vocabulário/proveniência** — os arquivos `keyword_taxonomy*.json` existentes permanecem como fontes de termos.
2. **Taxonomia canônica** — `config/taxonomy_registry.json` mapeia apenas os caminhos semânticos autorizados para IDs canônicos neutros e estáveis.

## Dimensões canônicas

### `domain`

Descreve o tema ou intervenção principal de Nutrição do Estilo de Vida.

Principais famílias:

- `domain.lifestyle_medicine.*`
- `domain.dietary_patterns.*`
- `domain.nutrition_composition.*`
- `domain.culinary_food_literacy.*`

### `context`

Descreve implementação, comportamento, modelo de cuidado, ambiente alimentar e contexto social.

Principais famílias:

- `context.behavior_change.*`
- `context.social_environment.*`
- `context.care_delivery.*`
- `context.implementation.*`
- `context.food_access.*`

### `condition`

Descreve condições clínicas associadas à referência.

Famílias atuais:

- obesidade/adiposidade;
- diabetes;
- hipertensão;
- dislipidemia;
- doença/risco cardiovascular;
- síndrome metabólica;
- doença hepática esteatótica metabólica;
- saúde cardiovascular-rim-metabólica/cardiorrenal.

### `outcome`

Descreve o desfecho ou construto avaliado.

Famílias atuais:

- antropometria;
- glicemia;
- pressão arterial;
- lipídios;
- inflamação;
- qualidade da dieta e adesão;
- comportamento;
- cardiometabólico/cardiorrenal;
- acesso alimentar/implementação;
- literacia e competência alimentar;
- adesão em cuidado personalizado.

## O que foi explicitamente retirado do score taxonômico

### Workstreams históricos

Todo o root `workstreams.*` é ignorado pelo compilador canônico.

Isso inclui nomes como:

```text
workstreams.busca1
workstreams.busca2a
workstreams.busca2b
workstreams.a3
workstreams.artigo3_framework
```

Os termos não são apagados do histórico do Git. Quando um conceito continua útil, ele deve existir em um caminho semântico autorizado de `global`, `clinical` ou `outcomes` e ser mapeado no registry.

### Tipos documentais

`global.document_types.*` também não entra mais no score taxonômico.

Tipo documental é um eixo diferente de assunto. O ranker possui uma camada própria de `document_type_hits` e `document_type_applied`, que impede empilhamento de bônus de termos documentais sobrepostos.

## Fail-closed da taxonomia

Quando `taxonomy_registry.json` existe, a compilação é estrita.

Se um novo caminho semântico aparecer sob `global`, `clinical` ou `outcomes` e não estiver registrado, o ranking falha com `TaxonomyError`.

Isso evita que a simples adição de um supplement altere silenciosamente o score e a ordem das referências.

Fluxo:

```text
keyword_taxonomy*.json
        ↓
identificação de leaf paths
        ↓
raízes autorizadas?
        ├─ não → excluído do score
        ↓ sim
caminho registrado no taxonomy_registry.json?
        ├─ não → FAIL CLOSED
        ↓ sim
merge/deduplicação de termos
        ↓
grupo canônico
```

## Taxonomia primária e secundária

Cada referência pode pertencer a vários grupos.

O ranker calcula score por grupo e registra:

- `taxonomy_primary`;
- `taxonomy_primary_rank`;
- `taxonomy_secondary`;
- `taxonomy_dimensions`;
- `taxonomy_groups`;
- `taxonomy_group_scores`;
- `taxonomy_ranks`.

A prioridade para escolher a taxonomia principal é:

```text
domain → context → condition → outcome
```

Dentro da primeira dimensão presente, vence o grupo com maior score taxonômico para aquela referência. Empates são resolvidos deterministicamente pelo ID canônico.

## Rank dentro da taxonomia

Além do `reference_rank` global, cada referência recebe posição dentro de todos os grupos taxonômicos em que foi classificada.

Exemplo conceitual:

```text
reference_rank: 12
reference_score: 74

taxonomy_primary: domain.dietary_patterns.mediterranean
taxonomy_primary_rank: 3

taxonomy_ranks:
  domain.dietary_patterns.mediterranean: 3
  condition.diabetes: 18
  outcome.glycemia: 21
```

Isso permite consultar tanto “quais referências devo ler primeiro?” quanto “quais são as referências mais prioritárias dentro de padrão mediterrâneo, diabetes, food literacy ou outro domínio?”.

## Regras de governança

Qualquer mudança taxonômica deve:

1. preservar os IDs canônicos existentes sempre que o conceito não mudou;
2. evitar nomes de artigos, buscas, workstreams ou fases de projeto nos IDs canônicos;
3. mapear novos caminhos explicitamente no registry;
4. manter tipo documental fora do score taxonômico;
5. incluir teste quando cria uma nova família ou dimensão;
6. passar pelo CI antes de merge;
7. registrar mudança de `taxonomy_version` quando o significado classificatório mudar.

## Arquivos relevantes

```text
config/taxonomy_registry.json
config/keyword_taxonomy.json
config/keyword_taxonomy_supplement*.json
src/nutev/taxonomy.py
tools/rank_references.py
nutev_tests/test_taxonomy_registry.py
```

## Auditoria

`AUDIT_MANIFEST.json` registra a versão da taxonomia, modo do registry, número de grupos brutos mapeados, grupos brutos excluídos e hashes dos arquivos de configuração usados.

O hash do `taxonomy_registry.json` é incluído na configuração auditada. Assim, duas execuções podem ser comparadas para determinar se a taxonomia usada era exatamente a mesma.

## Limite científico

A classificação taxonômica é baseada em correspondência de termos nos metadados disponíveis. Uma associação taxonômica não prova:

- que o artigo tenha alta qualidade;
- que o termo seja o objetivo principal do estudo;
- que a intervenção tenha sido eficaz;
- que o documento deva ser incluído em uma revisão;
- que exista recomendação clínica.

Essas decisões permanecem fora do ranker e exigem avaliação científica humana.
