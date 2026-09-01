# Governed Publication Manifest & Citation Bundle

The Governed Publication Manifest is the publication-preparation layer that follows a persisted Governed Synthesis Release.

Its purpose is deliberately narrow: turn an already governed, revalidated human-synthesis release into a traceable citation bundle and a set of publication statement candidates **without accepting scientific claims automatically**.

## Flow

```text
Scientific Intelligence
  -> Human Synthesis Review
     -> Human Synthesis Brief
        -> Synthesis Governance Registry
           -> Governed Synthesis Release
              -> Governed Publication Manifest
```

## Coordinator boundary

Phase 15 reuses the existing local-only Governed Release coordinator instead of adding a new remotely addressable write surface.

Status is read through:

```text
GET /api/synthesis/releases
```

The response remains metadata-oriented and now also includes:

```text
publication_manifest_type
publication_count
publication_records
```

Publication preparation uses the existing protected endpoint:

```text
POST /api/synthesis/releases/prepare
```

with the explicit operation:

```json
{
  "operation": "PREPARE_PUBLICATION_MANIFEST",
  "package_id": "release_...",
  "publication_owner": "Human name",
  "intended_use": "Declared publication purpose..."
}
```

The server route already requires loopback. No new remote publication-write surface is introduced.

## Source gate and revalidation

The publication service does not trust the persisted release record by itself.

Before a manifest is produced it reloads the release package and record and verifies:

1. release record type;
2. release package type;
3. `canonical:false` on the package;
4. `canonical_release_record:true` only for operational provenance;
5. `release_package_canonical:false`;
6. `canonical_scientific_synthesis_created:false`;
7. deterministic release package content SHA-256;
8. release record SHA matches the package;
9. the original registry artifact is still valid;
10. the source Brief is still valid;
11. current context fingerprint still matches;
12. rebuilding the governed release from current governance/context produces the same release content SHA.

If the Workbench or scientific context changes materially after the release was prepared, publication preparation fails closed and a new governed release is required.

## Manifest contract

The manifest type is:

```text
NUTEV_GOVERNED_PUBLICATION_MANIFEST_V1
```

It remains:

```text
canonical: false
publication_scope: GOVERNED_PUBLICATION_PREPARATION
```

The manifest contains:

- source release package id;
- source release content SHA-256;
- context fingerprint;
- search id/context version/question;
- publication owner;
- intended use;
- citation bundle;
- publication statement candidates;
- scientific guardrails;
- deterministic manifest content SHA-256.

## Citation bundle

Each reviewed human decision generates two citation entries: anchor and candidate.

Citation entries preserve, when available:

```text
citation_id
decision_id
role
document_id
title
identifiers
bundle_id
source_sentence_sha256
result_text
outcomes
effect_measures
confidence_intervals
p_values
routes
source_reference
```

Identifiers are derived only from explicit document ids already present in the source snapshot. For example:

```text
doi:10.x/...   -> doi
pmid:123456    -> pmid
pmcid:PMC...   -> pmcid
```

The service does not invent bibliographic metadata that is absent from the source artifact.

A citation entry means only that this source-linked snapshot participated in a recorded human synthesis decision. Citation presence does not establish validity, eligibility, certainty, causality, recommendation strength or EvidenceClaim acceptance.

## Publication statement candidates

The statement type is:

```text
NUTEV_PUBLICATION_STATEMENT_CANDIDATE_V1
```

The generated wording is intentionally restricted to describing the recorded human judgement itself, for example:

```text
In the governed human synthesis review, the source-linked pair in Food / nutrition literacy was classified by the reviewer as CONVERGENT.
```

It must not be automatically rewritten into substantive scientific claims such as:

```text
The evidence proves that X causes Y.
The literature confirms X.
There is high-certainty evidence for X.
X should be recommended clinically.
```

Every candidate records:

```text
publication_status: CANDIDATE_ONLY
accepted_evidence_claim: false
machine_inferred_scientific_claim: false
requires_human_author_editing: true
citation_ids: [...]
```

This is a key boundary between publication preparation and a future EvidenceClaim review/promotion workflow.

## Persistence and idempotency

Outputs are stored under:

```text
project_output_reference/scientific/publication_manifests/
  manifests/
    publication_<sha-prefix>.json
  records/
    publication_<sha-prefix>.json
```

The manifest contains the full citation bundle and statement candidates.

The record is metadata-only and contains counts, hashes, source release id, publication owner and intended use.

The record may be canonical only as an operational record:

```text
canonical_manifest_record: true
publication_manifest_canonical: false
accepted_evidence_claims_created: false
canonical_scientific_synthesis_created: false
```

Preparing the same source release with the same publication owner and intended use is idempotent by manifest content hash.

## Scientific boundary

The manifest explicitly records:

```text
source_release_revalidated_against_current_context: true
publication_statements_are_candidate_only: true
citations_are_source_linked_snapshots_not_validity_endorsements: true
accepted_evidence_claims_created: false
canonical_scientific_synthesis_created: false
risk_of_bias_assessed: false
certainty_assessed: false
meta_analysis_performed: false
prisma_event_emitted: false
formal_search_state_changed: false
clinical_recommendation_created: false
relationship_counts_are_not_evidence_strength: true
identity_cryptographically_authenticated: false
external_llm_generated_scientific_claims: false
```

## UI

`/synthesis-publication.html` provides:

- Governed Release selection;
- publication owner;
- intended use;
- explicit preparation action;
- statement candidate inspection;
- citation-bundle inspection;
- manifest JSON export;
- metadata-only publication ledger;
- visible scientific-boundary language.

Loading the page never prepares a manifest automatically.

## Adversarial audit

CI runs:

```text
python tools/audit_governed_publication_manifest.py --compact
```

The audit fails if future code:

- bypasses the local-only coordinator;
- skips release/context revalidation;
- promotes candidate statements to accepted EvidenceClaims;
- drops citation linkage;
- converts human relations into scientific truth or certainty;
- creates RoB/certainty/meta-analysis/PRISMA/recommendation state;
- auto-prepares a manifest on page load;
- leaks full citation bundles into the metadata ledger;
- introduces external LLM scientific-claim generation or operational ranking into this layer.

JavaScript syntax is also checked with:

```text
node --check apps/nutev-web/synthesis-publication.js
```

## Interpretation

A successful Governed Publication Manifest means:

> a governed release was revalidated against the current NutEV state and transformed into a source-linked publication-preparation artifact whose candidate statements describe recorded human synthesis judgements.

It does **not** mean:

> those candidate statements are accepted scientific claims, the evidence was graded for certainty, risk of bias was assessed, a recommendation was created, a meta-analysis was performed, a PRISMA decision occurred, or a canonical scientific synthesis was established.
