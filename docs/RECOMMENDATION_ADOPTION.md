# Recommendation Adoption — Fase 22

## Propósito

A Fase 22 adiciona um gate humano de governance depois de um `Recommendation Development` finalizado.

Fluxo:

```text
Recommendation Development FINALIZED
  -> Recommendation Adoption case PENDING
  -> ADOPT_FOR_DEFINED_SCOPE | REJECT | RETURN_FOR_REVISION
  -> canonical Recommendation Adoption record
```

O objetivo é responder uma pergunta estreita:

> Este wording humano pode ser adotado para o escopo explicitamente definido pela governance?

A fase **não** responde automaticamente:

- qual é a força da recomendação;
- qual é a certeza da evidência;
- se a recomendação é forte ou condicional;
- se um framework GRADE Evidence-to-Decision foi aplicado;
- se o texto é uma guideline recommendation;
- se o texto é uma clinical recommendation universal.

## Gate de entrada

Somente `NUTEV_CANONICAL_RECOMMENDATION_DEVELOPMENT_RECORD_V1` humano-finalizado pode abrir um Adoption Case.

Antes do staging e novamente antes da decisão, o serviço revalida:

- record type;
- `canonical:true`;
- `human_finalized:true`;
- SHA-256 científico do Recommendation Development;
- método `NUTEV_GENERIC_RECOMMENDATION_DEVELOPMENT_V1`;
- `recommendation_strength=not_evaluated`;
- guardrails da Fase 21;
- source draft;
- HumanValidation ACCEPT;
- RecommendationCandidate;
- EvidenceSets/claims/evaluations;
- context fingerprint;
- search id/context version.

Mudança upstream ou contexto stale falha fechado e exige novo staging.

## Estados

### `PENDING`

Staging cria apenas um caso pendente. Não há decisão implícita.

### `ADOPT_FOR_DEFINED_SCOPE`

Significa apenas:

> Um governor humano adotou o wording para o `adoption_scope` registrado neste caso.

Não significa:

- strong recommendation;
- conditional recommendation;
- high/moderate/low certainty;
- GRADE;
- GRADE EtD;
- clinical recommendation universal;
- guideline recommendation universal.

### `REJECT`

O wording não foi adotado para aquele gate/escopo.

### `RETURN_FOR_REVISION`

O development precisa ser revisitado. A Fase 22 registra instruções, mas **não edita automaticamente** o Recommendation Development.

## Recommendation strength

A fase preserva:

```text
recommendation_strength = not_evaluated
```

Não existe algoritmo, regra de maioria, contagem de EvidenceSets ou mapeamento de HumanValidation para força.

## Confirmações humanas obrigatórias

Toda decisão exige confirmação explícita de que:

1. a decisão foi inserida por humano;
2. eventual ADOPT vale somente para o escopo definido;
3. a decisão não infere recommendation strength, certainty ou GRADE;
4. a decisão não cria clinical/guideline recommendation automaticamente;
5. Recommendation Development e artefatos upstream permanecem imutáveis.

## Record canônico

```text
NUTEV_CANONICAL_RECOMMENDATION_ADOPTION_RECORD_V1
```

`canonical:true` significa apenas que o registro NutEV da decisão de governance e sua provenance é autoritativo.

Não significa que a recomendação é cientificamente canônica, universalmente aplicável ou metodologicamente graduada.

## Guardrails

Mesmo em `ADOPT_FOR_DEFINED_SCOPE`:

```text
recommendation_adoption_record_created: true
source_recommendation_development_revalidated: true
adopted_for_defined_scope: true
automatic_adoption_decision_performed: false
automatic_revision_applied: false
recommendation_strength_evaluated: false
certainty_assessed: false
grade_assessed: false
formal_etd_framework_applied: false
grade_etd_applied: false
formal_risk_of_bias_assessed: false
validated_recommendation_created: false
clinical_recommendation_created: false
guideline_recommendation_created: false
universal_recommendation_created: false
canonical_scientific_synthesis_created: false
meta_analysis_performed: false
prisma_event_emitted: false
source_recommendation_development_changed: false
identity_cryptographically_authenticated: false
```

## Imutabilidade

A decisão é persistida em artefato separado.

A Fase 22 não reescreve:

- Recommendation Development;
- HumanValidation;
- RecommendationCandidate;
- EvidenceSet;
- ClaimEvaluation;
- EvidenceClaim.

O coordinator apenas faz join metadata-only para mostrar o estado downstream.

## Local-only coordinator

A fase reutiliza:

```text
GET  /api/synthesis/releases
POST /api/synthesis/releases/prepare
```

Operações explícitas:

```text
STAGE_RECOMMENDATION_ADOPTION
DECIDE_RECOMMENDATION_ADOPTION
```

`server.py` permanece intocado.

## UI

`/recommendation-adoption.html`

A superfície oferece:

- finalized Recommendation Development records;
- staging manual do Adoption Case;
- `adoption_scope` e `governance_purpose` explícitos;
- decision selector vazio por padrão;
- `ADOPT_FOR_DEFINED_SCOPE`, `REJECT`, `RETURN_FOR_REVISION`;
- governor + rationale;
- revision instructions somente para `RETURN_FOR_REVISION`;
- cinco confirmações científicas/governance;
- ledger dos records canônicos.

## Auditoria

A fase inclui:

- `nutev_tests/test_recommendation_adoption.py`;
- `nutev_tests/test_recommendation_adoption_web_contract.py`;
- `tools/audit_recommendation_adoption.py`;
- 11º death test no CI;
- `node --check apps/nutev-web/recommendation-adoption.js`.

## Fronteira científica

```text
ADOPT_FOR_DEFINED_SCOPE != recommendation strength
Recommendation Adoption != certainty/GRADE
Recommendation Adoption != GRADE EtD
Recommendation Adoption != formal Risk of Bias
Recommendation Adoption != clinical recommendation
Recommendation Adoption != guideline recommendation
Recommendation Adoption != universal recommendation
Recommendation Adoption != canonical scientific synthesis
Recommendation Adoption != meta-analysis
Recommendation Adoption != PRISMA
```

Uma fase posterior pode definir um método formal de strength/certainty/adoption para guideline, mas deverá registrar explicitamente qual framework foi aplicado e não poderá retroativamente reinterpretar a Fase 22 como se esse método já tivesse sido usado.
