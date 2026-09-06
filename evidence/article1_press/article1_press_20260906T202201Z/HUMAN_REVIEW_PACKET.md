# Article 1 PRESS — PubMed delta run human-review packet

## Run identity

- Run: `article1_press_20260906T202201Z`
- Provider: PubMed
- Draft: `article1-query-draft-v1`
- Technical run SHA-256: `2ffae67debc73bfb29e271ee1f46ac3332760704188f6be3f08817d63253b63d`
- Workflow run: `34057757287`
- Workflow artifact: `9996495101`
- Artifact digest: `sha256:10edddf5b16edd677cfe893c33dad0172c2b60da488de0b76abff10eca50d7de`
- Artifact expiry: `2026-10-06T20:22:37Z`
- Persistent sample custody: `SAMPLE_MANIFEST.json`
- Technical status: `TECHNICAL_DELTA_RUN_COMPLETE_HUMAN_REVIEW_PENDING`

This packet records technical evidence only. It does **not** record PRESS PASS, a C4 decision, GF-10 authorization, query freeze, formal search, eligibility decisions, or PRISMA.

The exact identities of the incremental samples are now persisted in `SAMPLE_MANIFEST.json` as PMID/DOI pairs in the same order recorded by the immutable workflow artifact. Titles, abstracts and full text are deliberately not duplicated into Git. The manifest proves sample custody; it does not label any record as relevant or irrelevant.

## Delta results

| Test | Route | Baseline | Variant / standalone | Incremental | Human status |
| --- | --- | ---: | ---: | ---: | --- |
| D01 | B-NORM · `food based` | 138,913 | 138,913 | **0** | review/decision pending |
| D02 | B-NORM · `healthy eating` | 138,913 | 139,576 | **663** | 25-record precision sample pending |
| D03 | C1 · `meal plan*` | 4,053 | 4,586 | **533** | 25-record precision sample pending |
| D04 | C3 · implementation | — | 1,855 | **1,855** standalone | 25-record precision sample pending |
| D05 | C4 · social context | 143,873 non-C4 union | 149,928 with C4 | **6,055** | 25-record precision sample pending |

## Technical observations — not scientific decisions

### D01 · `food based`

The PubMed run returned no incremental records beyond the baseline query. This is a technical retrieval result. Whether the orthographic variant is retained for transparency, portability to other databases, or removed from the final PubMed string remains a PRESS decision.

### D02 · `healthy eating`

The term added 663 PubMed records. The incremental sample is heterogeneous and includes, among other topics, school healthy-eating initiatives, guidance, implementation work, behavioral interventions and unrelated/indirect health literature. Relevance must be judged against the Article 1 review question rather than inferred from the presence of the phrase.

### D03 · `meal plan*`

The term added 533 PubMed records. The sample includes direct meal-plan/dietetics material as well as broader AI, education, food-service and dietary-recommendation studies. Human review must decide whether the incremental sensitivity is worth the additional screening burden.

### D04 · C3 implementation

The standalone route returned 1,855 PubMed records. The sample spans implementation of nutrition/clinical programs but also items whose implementation/framework language belongs to unrelated domains. This demonstrates that a precision review is necessary before PRESS can accept the route unchanged.

### D05 · C4 social context

C4 added 6,055 records beyond the non-C4 union. The sample contains food insecurity, food environment, family meals and social-support material, but also broad social/food/environment uses outside the intended human nutrition-care scope (for example One Health microbiology, bacteriophage genomics, agricultural food-chain microbiology and animal social behavior). This is evidence of query breadth, not an automatic decision to reject C4.

## Human review fields

Use `SAMPLE_MANIFEST.json` as the permanent identity/order reference for the sampled records. Use the original workflow artifact while it remains available for the richer retrieval payload needed by the reviewer.

For each sampled record, record:

- `Y` — relevant to the Article 1 review question / route purpose;
- `N` — not relevant;
- `U` — uncertain / requires abstract or full-text inspection;
- brief reason;
- reviewer identity;
- review timestamp.

Then calculate the manual precision sample for D02–D05. D01 has no incremental sample because incremental yield was zero.

## Decision boundary

The technical run and sample manifest may support, but cannot make, the following decisions:

- D01: retain or omit `food based` in PubMed;
- D02: adopt, revise or omit `healthy eating`;
- D03: retain, revise or omit `meal plan*`;
- D04: accept or revise C3 implementation logic;
- D05: `ADOPT_C4`, `REVISE_C4`, or `REJECT_C4`.

Only after those judgments and the remaining PRESS/provider-native checks may PRESS be recorded as PASS and GF-10 be considered separately.
