# EvidenceSet Construction

Status: Fase 18 do Scientific Workspace v2.

## Objetivo

`EvidenceSet` organiza **EvidenceClaims source-level já aceitos e com ClaimEvaluation finalizada** em um conjunto científico rastreável.

O objeto responde:

> quais claims avaliados um curador decidiu agrupar sob uma determinada lente/foco científico, e por quê?

Ele **não** responde automaticamente:

- se os claims concordam;
- se os claims se contradizem;
- qual é a força do conjunto;
- qual é a certainty;
- qual é o risco de viés formal;
- qual é o efeito combinado;
- qual recomendação deve ser emitida.

## Fluxo

```text
EvidenceRecord
  -> accepted EvidenceClaim
  -> finalized ClaimEvaluation
  -> EvidenceSet draft
  -> human membership rationale
  -> finalized EvidenceSet
```

Nenhum membro é criado diretamente de ranking, taxonomy, similarity, pairwise relation, LLM ou cluster automático.

## Tipos

Draft:

```text
NUTEV_EVIDENCE_SET_CONSTRUCTION_DRAFT_V1
```

Registro final:

```text
NUTEV_CANONICAL_EVIDENCE_SET_RECORD_V1
```

Operações locais:

```text
STAGE_EVIDENCE_SET
FINALIZE_EVIDENCE_SET
```

As operações reutilizam o coordenador local-only já existente:

```text
GET  /api/synthesis/releases
POST /api/synthesis/releases/prepare
```

`server.py` não precisa de uma nova rota científica de escrita.

## Pré-condições de membership

Cada claim precisa satisfazer simultaneamente:

1. existir como `NUTEV_CANONICAL_EVIDENCE_CLAIM_RECORD_V1`;
2. estar ligado a um `EvidenceRecord` real;
3. manter proveniência válida até source snapshot/manifest/contexto;
4. possuir exatamente uma `NUTEV_CANONICAL_CLAIM_EVALUATION_RECORD_V1` finalizada;
5. manter o ClaimEvaluation consistente com o SHA do EvidenceClaim;
6. continuar válido contra o contexto científico atual.

Apenas um `claim_id` derivado ou um appraisal incompleto não satisfaz o gate.

## Integridade por membro

O draft preserva para cada membro:

- `claim_id`;
- SHA-256 do EvidenceClaim;
- `evaluation_id`;
- SHA-256 do ClaimEvaluation;
- `evidence_record_id`;
- `document_id`;
- `source_context_fingerprint`;
- `search_id`;
- `context_version`;
- statement source-level aceito;
- campos estruturados do claim;
- referência/source metadata disponível;
- dimensões humanas do ClaimEvaluation;
- assessment basis.

Isso permite revalidar o set sem alterar os artefatos upstream.

## Mesmo contexto científico

Na Fase 18, todos os membros do mesmo EvidenceSet precisam compartilhar:

```text
source_context_fingerprint
search_id
context_version
```

Esse gate evita misturar silenciosamente claims de snapshots científicos diferentes.

Uma futura camada de living evidence poderá modelar migração/supersession explicitamente; isso não deve ser antecipado por tolerância silenciosa nesta fase.

## Staging

O staging exige:

- `name`;
- `lens`;
- `focus_statement`;
- ao menos um `claim_id` elegível;
- responsável pelo staging;
- scope opcional.

Campos de scope suportados:

```text
domain
population
intervention_or_exposure
comparator
outcome
timeframe
context
```

O staging:

- ordena os claim IDs para identidade determinística;
- rejeita duplicatas;
- permite de 1 a 100 claims;
- revalida claim + appraisal + EvidenceRecord + contexto;
- cria somente um draft `canonical:false`;
- nunca finaliza automaticamente.

O operador de staging não faz parte da identidade científica do draft. Repetir a mesma proposta por outro operador devolve o mesmo draft.

## Um único claim é permitido

Um EvidenceSet pode conter apenas um claim.

Isso é útil quando uma lente científica é válida, mas somente uma proposição avaliada está disponível no momento.

O guardrail obrigatório é:

```text
single_claim_set_is_not_synthesis: true
```

Portanto:

```text
1 claim in EvidenceSet != synthesis
```

## Sobreposição entre EvidenceSets

Um claim pode participar de mais de um EvidenceSet quando isso for cientificamente justificável.

Exemplo:

```text
claim_X
  -> EvidenceSet: food_literacy_outcomes
  -> EvidenceSet: implementation_context
```

Isso é explicitamente permitido:

```text
overlapping_evidence_sets_allowed: true
```

A existência de uma membership anterior não preseleciona nem bloqueia uma nova membership.

## Finalização humana

Finalizar exige:

- `curator`;
- rationale geral >= 30 caracteres;
- rationale >= 15 caracteres para **cada** claim;
- confirmação de membership humana;
- confirmação de que grouping não implica consensus/contradiction;
- confirmação de que EvidenceSet não equivale a certainty/síntese/recomendação.

As membership rationales precisam corresponder exatamente ao conjunto de `claim_ids` do draft.

Claim ausente ou rationale extra faz o gate falhar.

## Revalidação no momento da finalização

Antes da finalização, o sistema reconstrói o draft a partir dos artefatos atuais.

Se mudou qualquer elemento relevante, por exemplo:

- Workbench database SHA;
- context fingerprint;
- EvidenceClaim;
- EvidenceRecord;
- ClaimEvaluation;
- source candidate;
- publication/source provenance;

a finalização falha fechado e exige novo staging.

Não há grandfathering silencioso de memberships antigas.

## Objeto `EvidenceSet`

O payload final respeita o modelo científico existente:

```text
EvidenceSet
  id
  name
  claim_ids
  lens
  metadata
```

A metadata inclui:

- `construction_semantics`;
- `focus_statement`;
- scope humano;
- curator;
- rationale geral;
- membership rationale por claim;
- SHA do claim/evaluation;
- EvidenceRecord/document id;
- provenance humana.

## Significado de `canonical:true`

No registro:

```text
NUTEV_CANONICAL_EVIDENCE_SET_RECORD_V1
```

`canonical:true` significa:

> este é o registro autoritativo NutEV da membership e proveniência daquele EvidenceSet.

Não significa:

- canonical scientific synthesis;
- scientific truth;
- consensus;
- high certainty;
- low risk of bias;
- meta-analysis;
- recommendation.

Essa separação é registrada por:

```text
canonical_scientific_synthesis_created: false
certainty_assessed: false
formal_risk_of_bias_assessed: false
clinical_recommendation_created: false
meta_analysis_performed: false
prisma_event_emitted: false
```

## Nenhuma agregação automática

O sistema não soma nem resume automaticamente os julgamentos dos ClaimEvaluations.

Guardrails:

```text
automatic_claim_grouping_performed: false
automatic_relation_inference_performed: false
claim_evaluation_scores_aggregated: false
consensus_inferred: false
contradiction_inferred: false
overall_certainty_grade_created: false
```

Exemplos proibidos:

```text
2 FAVORABLE + 1 SOME_CONCERNS = HIGH certainty
```

```text
3 claims no mesmo set = consensus
```

```text
2 resultados em direções diferentes = proven contradiction
```

Nenhuma dessas inferências é válida na Fase 18.

## Imutabilidade upstream

Finalizar um EvidenceSet não modifica:

- EvidenceClaim;
- ClaimEvaluation;
- EvidenceRecord;
- screening state;
- PRISMA events;
- publication manifest;
- governance/release artifacts.

A membership atual é exposta por join metadata-only:

```text
evidence_set_ids
evidence_set_membership_count
```

Há teste byte-a-byte protegendo EvidenceClaim e ClaimEvaluation contra mutação downstream.

## UI

Nova superfície:

```text
/evidence-sets.html
```

A página oferece:

- claims elegíveis avaliados;
- seleção manual sem defaults;
- name/lens/focus/scope;
- staging de draft;
- membership rationale por claim;
- três confirmações científicas;
- ledger de EvidenceSets finalizados;
- contexto de memberships existentes.

A UI não executa ranking, clustering ou LLM para escolher membros.

## Persistência

```text
project_output_reference/scientific/evidence_sets/
  drafts/
    evidence_set_draft_<sha>.json
  states/
    evidence_set_draft_<sha>.json
  finalized/
    evidence_set_<sha>.json
```

## Death test

```text
python tools/audit_evidence_set_construction.py --compact
```

O audit falha se detectar, entre outros:

- staging que chama finalização;
- preselection automática de claims;
- external LLM;
- grouping automático;
- relation inference automática;
- aggregation de ClaimEvaluation;
- consensus/contradiction automáticos;
- certainty grade;
- pooled effect;
- ausência de revalidação;
- perda da fronteira EvidenceSet != synthesis.

## Fronteira final

```text
EvidenceSet membership != agreement
EvidenceSet membership != contradiction
EvidenceSet != certainty/GRADE
EvidenceSet != formal Risk of Bias
EvidenceSet != pooled effect
EvidenceSet != meta-analysis
EvidenceSet != recommendation
EvidenceSet != PRISMA
canonical EvidenceSet record != canonical scientific synthesis
```
