# NutEV Evidence Engine — deterministic control plane

## Status

This document is a normative architecture rule for the NutEV Evidence Engine. It separates the scientific control plane from any generative-AI assistance layer.

## Non-negotiable boundary

The **control plane is deterministic**. Scientific state, audit evidence, provenance, gates, authorization, workflow transitions, hashes, provider results, FORMAL eligibility and PRISMA eligibility are produced and validated by deterministic code and structured artifacts.

Generative AI is **not** a control-plane actor. It may assist with prose, translation, explanatory views, normalization proposals and presentation of already-structured data, but it must not decide or mutate scientific state.

The direction of truth is always:

`provider/files/database -> deterministic code -> canonical JSON -> guardrails/firewall -> scientific state`

The AI assistance direction is separate:

`canonical data -> AI assistance -> prose/presentation/non-canonical proposal`

Never:

`prose -> LLM interpretation -> canonical scientific state`

## Canonical artifacts

Canonical scientific state must be represented by structured JSON with closed fields and controlled enumerations. Invalid payloads fail closed.

Examples of control fields include:

- `stage`
- `search_type`
- `prisma_eligible`
- `formal_execution_authorized`
- `freeze_authorized`
- `human_validated`
- `human_decision`
- `blockers`

The LLM must not directly write or alter those fields.

## Scientific state machine

Workflow transitions are determined by boolean predicates over canonical artifacts. Natural-language interpretation is never a transition condition.

The canonical progression remains conceptually:

`PILOT -> noise review -> READY_FOR_PRESS -> PRESS -> licensed provider validation -> remaining scientific gates -> FREEZE -> FORMAL -> screening -> full text -> ABCD -> relations -> adjudication -> synthesis -> PRISMA -> complete`

A software success must never be promoted into a human scientific decision.

## Guardrails and firewall

Sensitive operations must pass deterministic guard functions. Each guard returns a structured result such as:

```json
{
  "allowed": false,
  "rule": "FORMAL_REQUIRES_FREEZE",
  "blockers": ["freeze_authorized=false"]
}
```

A failed or unvalidated prerequisite blocks the transition. There is no permissive fallback.

### FORMAL execution

At minimum, FORMAL execution requires all of the following:

- `search_type == "FORMAL"`
- `freeze_authorized == true`
- `formal_execution_authorized == true`
- `required_scientific_gates_closed == true`

### Formal PRISMA

At minimum, formal PRISMA generation requires:

- `formal_execution_completed == true`
- `screening_completed == true`
- `fulltext_completed == true`
- `adjudication_completed == true`
- `prisma_eligible == true`

Otherwise the operation is blocked.

## Provenance

Provider and computational evidence is immutable input to scientific control decisions. Canonical provenance includes, when applicable:

- provider
- exact query
- query hash
- execution timestamp
- records found
- records returned
- response status
- execution id
- software version / Git SHA
- source artifact
- source hash

An LLM may explain these values but may not rewrite them as truth.

## Human gates

Human decisions are also structured data. A valid human decision must identify the real human actor and preserve an audit timestamp and evidence linkage. The backend writes the canonical JSON only after an explicit human action.

An AI may help draft the rationale text. It may not choose the decision, invent the reviewer, infer approval from inactivity or mark a gate complete.

## AI assistance layer

The AI layer is outside the control plane. It may:

- improve or draft prose;
- summarize already-structured evidence;
- explain deterministic blockers;
- translate text non-destructively;
- propose terminology normalization;
- organize tables and narrative;
- prepare manuscript wording.

AI-assisted normalization must preserve the original value. A proposal should retain fields such as `raw_value`, `normalized_value`, `normalization_source`, `normalization_method` and `human_validated`.

Purely mechanical transformations may be promoted automatically only when implemented and validated deterministically.

## PRISMA

PRISMA counts are computed from the canonical database/corpus. They are never calculated by asking an LLM to infer counts from prose or partial context.

The LLM may turn validated PRISMA JSON into narrative. It may not alter those counts.

## ABCD-NutEV

Structured extraction records remain the source of truth. AI assistance may organize passages and draft explanatory text, but presence, depth and explicit relations remain governed by the protocol and required human validation. No global ABCD score is invented.

## Audit trail

Scientific mutations are append-only/auditable and should preserve before/after hashes, actor, timestamp and software version. Allowed scientific actors are deterministic system components and identified humans.

`AI_ASSISTANT` may be an actor only for non-canonical presentation/prose artifacts.

## Implementation rule

The architecture is summarized as:

- **LLM = language and assistance**
- **Python/SQL/JSON = operational truth**
- **JSON Schema = contract**
- **state machine = workflow**
- **guardrails = rules**
- **firewall = blocking**
- **hashes = integrity**
- **provider responses = execution evidence**
- **human-decision JSON = scientific responsibility**
- **PRISMA = deterministic calculation**

The AI may explain the system. It does not control the system.
