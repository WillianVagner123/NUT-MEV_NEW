# PRESS review workflow

Status: canonical operational workflow for Article 1 PubMed strategy peer review.

## Purpose

The PRESS screen is the GF-03 external peer-review gate for the stabilized PubMed strategies used by Article 1. It is not a search runner, not a freeze control, and not a PRISMA workflow.

Current package:

- B-NORM-PUBMED v0.7 — normative/guideline route.
- C-STRUCT-PUBMED v0.5.1 — structured/operational/implementation/competency route after syntax-clean micro-PILOT.

The two routes are complementary and must remain logically separate. PRESS review may assess their combined coverage, but the application must not silently merge them with OR.

## Reviewer independence

GF-03 requires an independent PRESS reviewer. The reviewer identity, affiliation, review date and explicit independence attestation are required before the review can be considered complete.

The authoring team may prepare the package and respond to comments, but may not fill the independent review in the reviewer's name.

## Materiality gate

Each checklist item is concluded by the reviewer as one of:

- adequate;
- non-material observation;
- material revision required;
- not applicable.

Final decisions are:

- ACCEPT;
- ACCEPT_MINOR;
- MATERIAL_REVISION;
- REJECT.

Any material checklist conclusion or MATERIAL_REVISION final decision produces `RETURN_TO_PILOT`. The query is not edited inside the PRESS screen. A material change requires a new strategy version, documented rationale, and a new PILOT before resubmission to PRESS.

ACCEPT or ACCEPT_MINOR with no material checklist items produces `PRESS_REVIEW_COMPLETE`, which means the external opinion is ready to be incorporated/versioned in the canonical control center. It does not by itself authorize freeze.

REJECT produces `PRESS_NOT_APPROVED` and GF-03 remains blocking.

## Freeze guardrail

The exported PRESS result always carries `freeze_authorized: false`.

After an acceptable PRESS review is incorporated, the global freeze still depends on all other active gates. In the current Article 1 state, regional technical routes such as LILACS/BVS and SciELO remain separate freeze dependencies and must not be recoded as zero results when unavailable.

## Audit artifacts

The screen can export:

1. a PRESS package JSON containing strategy IDs, versions, exact PubMed queries, PILOT evidence, version history, checklist and decision options;
2. a PRESS review JSON containing reviewer identity, independence attestation, per-item conclusions/comments, final decision, suggested changes, materiality gate result, and `freeze_authorized: false`.

These artifacts are evidence for GF-03 incorporation. They do not replace the canonical spreadsheet decision record.
