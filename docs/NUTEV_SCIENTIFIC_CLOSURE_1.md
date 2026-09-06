# NutEV Scientific Closure 1.0

Status document for the Article 1 scientific-closure milestone.

## Canonical state

At the start of this milestone, `main` was `473c5c573dc12a96bbe5a4adb9a259a1567bff40` and the canonical Article 1 Search Master declared:

- `status = DISCOVERY_CLOSED_FORMAL_SEARCH_PENDING_PRESS_FREEZE`
- `press_status = NOT_YET_RECORDED_AS_PASS`
- `gf10_authorized = false`
- `query_freeze_complete = false`
- `formal_provider_search_executed = false`
- `prisma_search_event_emitted = false`

This document does not promote any of those states.

## What this milestone fixes

The web PRESS surface pre-dated the current Search Master and still centered an older PubMed-only profile (`GF-03`, `B-NORM-PUBMED v0.7`, `C-STRUCT-PUBMED v0.5.1`). The current canonical query draft instead defines:

- `B-NORM`
- `C1-CARE-PROCESS`
- `C2-COMPETENCY-LITERACY`
- `C3-IMPLEMENTATION`
- `C4-SOCIAL-CONTEXT` as `PRESS_ONLY_CANDIDATE_NOT_APPROVED`

The PRESS surface is therefore aligned to the current pre-freeze design and treats `GF-10` as a separate downstream gate.

## Canonical PRESS record

`config/nutev/article1_press_review_v1.json` is the machine-readable closure worksheet.

Initial state is intentionally fail-closed:

- `status = DRAFT`
- no reviewer
- no PRESS decision
- all mandatory review items pending
- all five delta tests pending
- C4 human decision pending
- provider-native formal strings pending
- GF-10 unauthorized

Only a real human review may justify a PRESS PASS. Software must never write PASS merely because the worksheet is complete.

## Required delta tests

1. B-NORM baseline vs `+ food based` orthographic variant.
2. B-NORM baseline vs `+ healthy eating`.
3. C1 with vs without `meal plan*`.
4. C3 standalone yield and manual precision sample.
5. C4 incremental yield and manual precision sample.

Counts alone do not decide a term. Incremental records require human relevance review.

## C4 decision

After its stress test, C4 must receive one explicit human decision:

- `ADOPT_C4`
- `REVISE_C4`
- `REJECT_C4`

Until then it remains a PRESS-only candidate.

## Formal bibliographic providers

The closure record has explicit slots for:

- PubMed
- LILACS/BVS
- SciELO
- Scopus
- Web of Science

Scopus and Web of Science must not be simulated. Provider-native syntax must be validated against the real provider/access path before freeze.

Europe PMC, OpenAlex, Crossref, DOAJ and Semantic Scholar remain discovery/supplementary/QA sources unless a later explicit protocol decision changes their role.

## Gate order

The enforced order is:

```text
human PRESS review
  -> mandatory delta tests complete
  -> explicit C4 decision
  -> provider-native syntax + known-item/sentinel + cross-database translation review
  -> PRESS PASS recorded canonically
  -> explicit GF-10 authorization
  -> immutable query freeze
  -> formal provider search
  -> PRISMA identification event
```

No downstream state may imply or back-fill an upstream state.

## Scientific validation of the Engine

This milestone does not alter the frozen validation runtime:

`6aa7a5fe6009776e611ca3e1506486606b05f4f6`

The validation program remains at the human initial-assessment gate. No synthetic labels, gold standard, benchmark metrics, external-test labels or upgraded scientific verdict are created here.

## ClaimEvaluation, Risk of Bias and GRADE

The existing `ClaimEvaluation` remains `NUTEV_GENERIC_CLAIM_APPRAISAL_V1`.

It is not formal Risk of Bias, GRADE or certainty assessment. Recommendation Adoption also remains scope-limited governance and does not become a clinical/guideline recommendation, recommendation-strength decision, GRADE EtD assessment or meta-analysis.

Formal design-specific RoB and certainty layers are future scientific work after formal search/screening provides the appropriate study set. They must not be fabricated to make the product appear complete.

## CI death test

`tools/audit_nutev_scientific_closure.py` fails closed if the repository tries to:

- record PRESS PASS without the canonical human record;
- authorize GF-10 before PRESS;
- freeze before GF-10;
- execute formal search before freeze;
- emit PRISMA before formal search;
- treat the legacy PRESS profile as current;
- use substring matching to turn `NOT_YET_RECORDED_AS_PASS` into PASS;
- lose the generic-appraisal boundary of ClaimEvaluation;
- turn Recommendation Adoption into strength/GRADE/RoB/clinical recommendation/meta-analysis;
- move the frozen scientific-validation runtime silently;
- omit the formal-provider slots or allow Scopus/WoS simulation.

## Production verification

Repository deployment code is not proof of the SHA currently serving production. Production identity must be verified independently using the live service/host and recorded as evidence. Until that succeeds, the correct state is `BUILD_IDENTITY_NOT_PROVABLE`, not `PRODUCTION_MATCHES_MAIN`.

## Next real gate

The next scientific gate is not another feature phase.

It is completion of the PRESS evidence package and human review, beginning with the five registered delta tests and the explicit C4 decision, while preserving all formal-search fields as false until their prerequisites genuinely close.
