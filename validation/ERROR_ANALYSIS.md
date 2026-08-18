# Error Analysis

Status: `NOT_TESTED`

Este documento deve ser preenchido somente com erros observados em benchmark real ou validação humana.

## Categorias obrigatórias

- relevant reference not retrieved;
- relevant reference retrieved but ranked too low;
- irrelevant reference ranked too high;
- taxonomy false positive;
- taxonomy false negative;
- provider/metadata-driven rank distortion;
- missed duplicate;
- false duplicate merge;
- quarantine false exclusion;
- identifier/provenance failure;
- language/indexing failure;
- comparator-specific difference.

## Formato por caso

`CLAIM -> BASELINE -> METHOD -> EVIDENCE -> RESULT -> UNCERTAINTY -> DECISION`

Não preencher exemplos inventados. Casos precisam apontar para `question_id`, `reference_id`, commit/configuração e evidência verificável.
