# Current code hygiene inventory

Status: **canonical runtime cleanup substantially complete; release provenance remains separate**.

The active tree should contain supported scientific behavior, current governance, reusable downstream scientific assets and required provenance.

## Retired runtime layers

The inherited Local Deep Research runtime and the former parallel NutEV `master_pipeline/querypacks` architecture are not in the active tree. Historical code and required attribution remain in Git history, `LICENSE` and `NOTICE.md`.

The canonical computational path is now:

```text
registered/versioned strategy
        ↓
provider execution + attempt evidence
        ↓
corpus / identity resolution
        ↓
full-text resolution / extraction
        ↓
human-review queues
        ↓
versioned extraction/codebook outputs
```

## Semantic labels

New analytical outputs use `policy_systems`, `clinical_outcomes`, `implementation`, `framework` and `global_watch`. Historical `busca1`, `busca2a`, `busca2b`, `a3` and article-framework names are ingest aliases only. Evidence lenses no longer emit `lens_busca*` fields.

## Relevance/scoring retirement

`src/nutev/analysis/relevance.py` and `config/scoring_rules*.json` were audited before deletion. Repository code search found no supported runtime consumer: the module was referenced only by its dedicated tests, and the scoring configuration was used only by that module/tests and generic config provenance.

The subsystem and its dedicated tests were therefore retired instead of preserving an unused workstream-scoring layer through cosmetic renaming.

Preserved intentionally:

- `keyword_taxonomy*.json`, thematic taxonomy and ontology assets useful to downstream extraction/codebook work;
- `nutev_ontology.json` and semantic evidence lenses used by supported classification;
- source/provider/scientific registries;
- scientific governance and execution contracts;
- immutable release/provenance records.

## Scientific boundary

Code hygiene does not close GF-02, authorize PRESS/GF-10, create human screening decisions, make a run PRISMA-eligible or create a release. Those states require their own real evidence.

## Deletion acceptance rule

Retire a component only when no supported runtime consumes it (or its consumer is retired in the same change), exclusive tests move with it, no normative path requires it, independently useful scientific assets remain preserved, required provenance remains, and canonical CI/security/release validation stays green.

## Remaining release boundary

The inherited-code/license boundary and final copyright presentation remain tracked separately in #1014. A future citable release must archive one exact reviewed SHA and exclude protected full text, credentials, private/local outputs and other non-redistributable material.
