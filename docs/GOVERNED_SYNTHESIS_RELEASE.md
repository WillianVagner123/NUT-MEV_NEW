# Governed Synthesis Release Package

The Governed Synthesis Release Package is the dissemination layer that follows the Human Synthesis Review, Human Synthesis Brief and Synthesis Governance Registry.

Its purpose is narrow: prepare an auditable package for manuscript drafting, defense boards, presentations or other controlled scientific communication **without creating a new scientific inference**.

## Flow

```text
Scientific Intelligence
  -> Human Synthesis Review
     -> Human Synthesis Brief
        -> Synthesis Governance Registry
           -> Governed Synthesis Release
```

The release source must already be:

```text
status: APPROVED_FOR_GOVERNED_USE
```

A `STAGED` or `REJECTED_BY_GOVERNANCE` registry entry cannot generate a release package.

## Local-only coordinator surface

The release APIs are available only to loopback clients of the NutEV web server:

```text
GET  /api/synthesis/releases
POST /api/synthesis/releases/prepare
```

Remote clients receive the same coordinator `403` used by governance and sensitive validation controls.

The public static page may load, but it cannot read release-ledger state or prepare a release through the coordinator API.

## Server-side revalidation

Release preparation does not trust a prior browser check and does not trust approval status alone.

At preparation time the server revalidates:

1. registry entry type;
2. registry status equals `APPROVED_FOR_GOVERNED_USE`;
3. registry entry is canonical only as a governance record;
4. the registry never declared canonical scientific synthesis creation;
5. governance action is explicitly `APPROVE`;
6. governance decision is human-entered;
7. source revalidation was recorded at governance decision time;
8. no unsupported cryptographic identity-authentication claim is present;
9. immutable source Brief is reloaded from the governance artifact store;
10. Brief content SHA-256 is recomputed;
11. current Article 1 context fingerprint is recomputed;
12. search id/context version/question remain compatible;
13. the source Brief still passes all Human Synthesis Brief scientific guardrails.

An entry approved under an older materialized Workbench/context therefore fails closed if the context changes before release preparation.

## Release package

The scientific payload type is:

```text
NUTEV_GOVERNED_SYNTHESIS_RELEASE_V1
```

It contains:

- source registry artifact id;
- governance status and decision provenance;
- source Brief content SHA-256;
- current context fingerprint;
- search id and context version;
- scientific question;
- reviewer provenance;
- governor provenance and rationale;
- release preparer;
- explicit dissemination purpose;
- relationship/domain/comparability summaries already present in the source Brief;
- source-linked reviewed decisions;
- release-specific scientific guardrails;
- deterministic package content SHA-256.

The package remains:

```text
canonical: false
release_scope: GOVERNED_DISSEMINATION_PACKAGE
```

## Persistent release ledger

Release outputs are stored under:

```text
project_output_reference/scientific/synthesis_releases/
  packages/
    release_<sha-prefix>.json
  records/
    release_<sha-prefix>.json
```

The package stores the complete governed dissemination artifact.

The release record stores metadata only. `GET /api/synthesis/releases` returns records and does **not** return the complete package or `reviewed_decisions`.

The record is canonical only as evidence that a dissemination package was prepared:

```text
canonical_release_record: true
release_package_canonical: false
canonical_scientific_synthesis_created: false
```

This distinction mirrors the governance registry boundary.

## Idempotency

The package content hash is computed over the stable scientific content, excluding `generated_at`.

The package id is:

```text
release_<first 24 characters of content_sha256>
```

Preparing the same approved source with the same `prepared_by` and `purpose` returns the already persisted package instead of creating a duplicate release record.

Changing the dissemination purpose or preparer changes the scientific-content payload and therefore produces a new package hash/record.

## Human requirements

Release preparation requires:

- an explicitly selected approved registry entry;
- a named `prepared_by` human operator;
- a dissemination `purpose` of at least 20 characters;
- an explicit user click on **Preparar governed release**.

Loading the page never prepares a package automatically.

Names in this workflow remain provenance metadata. The release does not claim cryptographic identity authentication.

## Scientific boundaries

A governed release does not create or imply:

- accepted EvidenceClaims;
- study eligibility;
- risk-of-bias assessment;
- evidence certainty;
- statistical pooling;
- meta-analysis;
- clinical recommendation;
- PRISMA event or inclusion/exclusion;
- formal-search state change;
- canonical scientific synthesis;
- authenticated authorship or identity.

The package explicitly records:

```text
canonical_scientific_synthesis_created: false
accepted_evidence_claims_created: false
risk_of_bias_assessed: false
certainty_assessed: false
meta_analysis_performed: false
prisma_event_emitted: false
formal_search_state_changed: false
relationship_counts_are_not_evidence_strength: true
governed_release_is_not_scientific_validation: true
identity_cryptographically_authenticated: false
```

## UI

`/synthesis-release.html` shows only registry entries that satisfy the approved human-governance contract.

The page provides:

- approved-source selection;
- preparer identity field;
- release-purpose field;
- explicit preparation action;
- server-revalidated prepared package summary;
- local JSON download of the returned package;
- metadata-only release ledger;
- visible scientific-boundary language.

The UI does not call external LLM APIs and does not use Bank rank or machine relevance to choose release content.

## Guardrail audits

CI runs three Scientific Workspace adversarial layers:

```text
python tools/audit_scientific_workspace_v2.py --compact
python tools/audit_synthesis_governance.py --compact
python tools/audit_governed_synthesis_release.py --compact
```

The release death test fails if future code:

- exposes coordinator release APIs remotely;
- allows non-approved registry entries to release;
- skips source/context revalidation;
- auto-prepares a release;
- turns the release into canonical synthesis;
- creates fake RoB/certainty/meta-analysis/PRISMA state;
- claims cryptographic identity authentication;
- leaks full packages into the release ledger;
- introduces external LLM or operational-ranking dependencies into release preparation.

CI also runs:

```text
node --check apps/nutev-web/synthesis-release.js
```

## Interpretation

A successful governed release means:

> an approved human-synthesis artifact was revalidated against the current NutEV context and packaged for a declared dissemination purpose with an auditable content hash.

It does **not** mean:

> the evidence was scientifically validated, graded for certainty, meta-analyzed, accepted into PRISMA, or promoted to canonical scientific truth.
