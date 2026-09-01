# Synthesis Governance Registry

The Synthesis Governance Registry is the first server-backed governance layer for NutEV human-synthesis artifacts.

Its purpose is narrow: preserve an authoritative record of **governance state** for a verified Human Synthesis Brief without turning registry operations into scientific conclusions.

## Flow

```text
Scientific Intelligence
  -> Human Synthesis Review
     -> Human Synthesis Brief
        -> Synthesis Governance Registry
```

The source Brief remains:

```text
NUTEV_HUMAN_SYNTHESIS_BRIEF_V1
canonical: false
```

The registry never rewrites that source artifact as `canonical:true`.

## Local-only coordinator surface

Registry APIs are available only from loopback clients of the NutEV web server:

```text
GET  /api/synthesis/governance
POST /api/synthesis/governance/stage
POST /api/synthesis/governance/decide
```

All three routes call the same `_require_loopback()` coordinator guard used by sensitive validation controls.

A remote browser may load the static governance page, but coordinator API calls return `403`. Therefore public deployment does not expose registry state or mutation controls remotely.

The default API JSON-body limit remains 256 KiB. Only the governance stage/decision endpoints accept up to 2 MiB because a source-linked Brief can exceed the generic request size.

## Persistent storage

The default registry root is:

```text
project_output_reference/scientific/synthesis_registry/
  artifacts/
    <content_sha256>.json
  entries/
    brief_<sha-prefix>.json
```

The stored artifact is the imported Brief content. Registry listing endpoints return entry metadata only; they do not send the stored Brief body or reviewed-decision payloads back to the browser.

Writes use temporary files followed by atomic replacement under an in-process registry lock.

## Staging

Staging requires:

- a named human operator (`actor`);
- an imported `NUTEV_HUMAN_SYNTHESIS_BRIEF_V1`;
- `canonical:false`;
- `integrity_verified:true`;
- `current_context_match:true`;
- a source `NUTEV_HUMAN_SYNTHESIS_REVIEW_DRAFT_V1`;
- valid human pairwise decisions;
- expected scientific guardrails;
- a correct deterministic Brief `content_sha256`;
- a `source_context_fingerprint` matching the live Article 1 context;
- matching search id, context version and question.

The server does **not** trust the browser's previous verification. It independently recomputes the Brief hash and live context fingerprint.

Successful import creates:

```text
status: STAGED
```

Staging never calls the governance-decision function and never produces an approved status.

## Idempotency

The registry identity is derived from the Brief `content_sha256`:

```text
brief_<first 24 hex characters>
```

Staging the same Brief again returns the existing registry entry rather than creating a duplicate or changing the original `staged_by` record.

## Governance decision

A `STAGED` entry can receive one explicit human governance action:

```text
APPROVE
REJECT
```

The resulting registry statuses are:

```text
APPROVED_FOR_GOVERNED_USE
REJECTED_BY_GOVERNANCE
```

Before recording either result the service:

1. reloads the immutable source Brief from the registry artifact store;
2. recomputes its content hash;
3. recomputes the current Article 1 context fingerprint;
4. validates the source human decisions and guardrails again;
5. confirms the source hash still matches the registry entry.

If the Workbench/context changed after staging, governance fails closed. A previously staged file is not grandfathered into approval.

## Human requirements

A governance decision requires:

- `governor` name;
- action `APPROVE` or `REJECT`;
- rationale of at least 20 characters.

The decision records:

```text
human_entered: true
source_revalidated_at_decision: true
identity_cryptographically_authenticated: false
```

The typed name is provenance metadata only. This phase has no cryptographic identity provider, signature or attestation mechanism.

## What APPROVED means

`APPROVED_FOR_GOVERNED_USE` means only that a human governance decision was recorded after source/context revalidation.

It does not mean:

- evidence certainty;
- methodological quality;
- risk-of-bias approval;
- accepted EvidenceClaims;
- statistical pooling;
- meta-analysis;
- clinical recommendation;
- PRISMA inclusion;
- authenticated reviewer identity;
- canonical scientific synthesis.

Every registry entry explicitly keeps:

```text
source_artifact_canonical: false
canonical_scientific_synthesis_created: false
reviewer_identity_cryptographically_authenticated: false
```

The registry entry itself is canonical only as an **authoritative governance record** (`canonical_registry_record:true`). This is deliberately distinct from canonical scientific synthesis.

## What REJECTED means

`REJECTED_BY_GOVERNANCE` means the artifact was not accepted for governed use in this registry workflow.

It is not a title/abstract or full-text exclusion decision and must not be counted as a PRISMA exclusion.

## UI

`/synthesis-governance.html` provides:

- local-only registry status;
- Brief file selection;
- named staging operator;
- explicit `STAGED` action;
- metadata-only ledger;
- named governance decision + rationale;
- explicit Approve/Reject actions;
- visible scientific-boundary language.

The UI never auto-approves after import.

## Guardrail audits

Two adversarial audits run in CI:

```text
python tools/audit_scientific_workspace_v2.py --compact
python tools/audit_synthesis_governance.py --compact
```

The governance death test protects:

- loopback-only coordinator routes;
- staged-not-approved import semantics;
- explicit human governance action;
- mandatory rationale;
- source/context revalidation at decision time;
- no canonical scientific synthesis creation;
- no claim of cryptographic human identity authentication;
- no PRISMA/certainty semantics;
- metadata-only registry listing;
- no external LLM calls;
- no Bank/machine ranking semantics.

CI also runs `node --check apps/nutev-web/synthesis-governance.js`.
