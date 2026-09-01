# Recommendation Development — Fase 21

## Objetivo

A Fase 21 cria um worksheet humano de desenvolvimento de recomendação a partir de uma `HumanValidation` com decisão `ACCEPT`.

Fluxo:

```text
RecommendationCandidate
  -> HumanValidation ACCEPT
  -> Recommendation Development draft
  -> finalized Recommendation Development record
```

O resultado é um registro canônico do **worksheet e de sua proveniência**. Ele não é, por si só, uma recomendação clínica, guideline recommendation ou aplicação de GRADE Evidence-to-Decision.

## Gate de entrada

Somente `NUTEV_CANONICAL_HUMAN_VALIDATION_RECORD_V1` com decisão `accept` pode alimentar a Fase 21.

Antes do staging e novamente antes da finalização, o sistema revalida:

- HumanValidation canônica;
- SHA-256 do registro de HumanValidation;
- decisão `accept`;
- `candidate_accepted_for_declared_scope:true`;
- RecommendationCandidate source;
- SHA-256 do RecommendationCandidate;
- EvidenceSets e snapshots upstream;
- EvidenceClaims / ClaimEvaluations materializados pelos EvidenceSets;
- context fingerprint;
- search id;
- context version.

Se o contexto ou qualquer artefato upstream divergir, a operação falha fechado.

## Método

```text
NUTEV_GENERIC_RECOMMENDATION_DEVELOPMENT_V1
```

O nome é deliberadamente genérico.

Esta fase **não declara**:

- GRADE Evidence-to-Decision aplicado;
- GRADE certainty;
- recommendation strength;
- formal risk-of-bias assessment;
- formal benefit-harm balance;
- formal values/preferences assessment;
- formal resource-use assessment;
- formal equity assessment;
- formal acceptability assessment;
- formal feasibility assessment.

## Campos humanos obrigatórios

O humano precisa registrar:

- proposed recommendation text;
- population / scope;
- intervention or action;
- comparator or alternative;
- benefits consideration;
- harms / burdens consideration;
- values / preferences consideration;
- resources consideration;
- equity consideration;
- acceptability consideration;
- feasibility consideration;
- implementation considerations;
- uncertainty notes;
- developer rationale;
- prepared by.

Esses campos são **considerações narrativas humanas**. A existência do texto não significa que cada domínio foi formalmente medido ou julgado por um framework validado.

## Wording não é promovido automaticamente

A tela mostra o `RecommendationCandidate` aceito como source read-only.

O campo `proposed_recommendation_text` começa vazio.

O NutEV não:

- copia o candidate para o novo wording;
- completa o texto;
- sugere automaticamente a linguagem;
- calcula força;
- calcula direção;
- calcula certainty;
- decide recommendation status;
- chama LLM externo para tomar essa decisão.

## Recommendation strength

Nesta fase:

```text
recommendation_strength = not_evaluated
```

Esse valor permanece fixo no draft e no registro finalizado.

## Staging

Operação:

```text
STAGE_RECOMMENDATION_DEVELOPMENT
```

O staging:

- exige HumanValidation `ACCEPT`;
- revalida toda a cadeia;
- exige autoria humana;
- exige confirmação de que o método é genérico e não GRADE EtD;
- cria apenas um draft;
- não finaliza automaticamente;
- não cria recommendation formal.

Há um worksheet por HumanValidation aceita nesta versão. Retry idêntico é idempotente. Tentativa de restaging com conteúdo diferente falha fechado em vez de sobrescrever o draft existente.

## Finalização

Operação:

```text
FINALIZE_RECOMMENDATION_DEVELOPMENT
```

A finalização exige:

- finalizer;
- rationale;
- confirmação de que GRADE EtD não está sendo declarado;
- confirmação de que recommendation strength segue `not_evaluated`;
- confirmação de que o worksheet não cria clinical/guideline recommendation;
- confirmação de imutabilidade de HumanValidation e RecommendationCandidate upstream.

Record type:

```text
NUTEV_CANONICAL_RECOMMENDATION_DEVELOPMENT_RECORD_V1
```

`canonical:true` significa apenas que o worksheet e sua proveniência são o registro autoritativo NutEV daquela etapa.

Não significa recomendação científica autoritativa.

## Guardrails

O registro finalizado mantém:

```text
source_human_validation_accept_revalidated: true
source_candidate_revalidated: true
automatic_recommendation_generation_performed: false
candidate_statement_auto_promoted: false
recommendation_strength_evaluated: false
formal_etd_framework_applied: false
grade_etd_applied: false
certainty_assessed: false
grade_assessed: false
formal_risk_of_bias_assessed: false
formal_benefit_harm_balance_determined: false
values_preferences_formally_assessed: false
resource_use_formally_assessed: false
equity_formally_assessed: false
acceptability_formally_assessed: false
feasibility_formally_assessed: false
recommendation_development_record_created: true
validated_recommendation_created: false
clinical_recommendation_created: false
guideline_recommendation_created: false
canonical_scientific_synthesis_created: false
meta_analysis_performed: false
prisma_event_emitted: false
source_human_validation_changed: false
source_recommendation_candidate_changed: false
identity_cryptographically_authenticated: false
```

## Upstream immutability

A Fase 21 cria artefatos separados em:

```text
project_output_reference/scientific/recommendation_development/
  drafts/
  states/
  finalized/
```

Ela não reescreve:

- HumanValidation;
- RecommendationCandidate;
- EvidenceSet;
- ClaimEvaluation;
- EvidenceClaim;
- EvidenceRecord.

## UI

Página:

```text
/recommendation-development.html
```

A interface:

- lista HumanValidations `ACCEPT`;
- mostra o candidate source apenas como leitura;
- inicia todos os campos de desenvolvimento vazios;
- exige input humano;
- mostra drafts e finalizados;
- expõe explicitamente `strength=not_evaluated`;
- mostra `GRADE EtD applied: NO`;
- mostra `validated recommendation: NO`;
- mostra `clinical: NO`;
- mostra `guideline: NO`.

## Coordinator boundary

A fase reutiliza o coordenador local-only existente:

```text
GET  /api/synthesis/releases
POST /api/synthesis/releases/prepare
```

Não cria nova rota remota e não altera `server.py`.

## Verificação

Testes:

```text
nutev_tests/test_recommendation_development.py
nutev_tests/test_recommendation_development_web_contract.py
```

Death test:

```text
tools/audit_recommendation_development.py
```

O CI executa esse auditor como o décimo death test do Scientific Workspace.

## Fronteira científica

```text
HumanValidation ACCEPT
  != recommendation strength
  != recommendation formal

Recommendation Development
  != GRADE EtD
  != GRADE certainty
  != formal Risk of Bias
  != formal benefit-harm balance
  != validated recommendation
  != clinical recommendation
  != guideline recommendation
  != canonical scientific synthesis
  != meta-analysis
  != PRISMA
```

A etapa seguinte, se implementada, deve continuar exigindo decisão humana explícita e um método formalmente declarado antes de qualquer objeto ser chamado de recommendation validada, guideline recommendation ou recommendation com força atribuída.
