# GF-02 — Priority sentinel identity audit

Status: **identity audit completed for NORM-035 and NORM-063; retrieval validation still pending**.

Date of reconciliation: 2026-08-12.

This record resolves the intellectual-document identity of the two priority sentinels required by GF-02. It does **not** claim that either item has been recovered by the candidate v0.3 search, does not create PRESS approval, and does not authorize FORMAL/PRISMA execution.

## Sources used

1. Canonical Article 1 Drive staging sheet: `A1 — STAGING — GUIAS ALIMENTARES E NORMATIVOS — AUDITORIA`, tab `03_NORMATIVOS_AFINS_56`.
   - NORM-035: staging row 39; linked NORM-036 row 40.
   - NORM-063: staging row 67; linked Executive Summary manifestations NORM-037/NORM-038 rows 41–42.
2. NCBI PubMed/PMC bibliographic records used to verify canonical identifiers.

Drive source:
`https://docs.google.com/spreadsheets/d/1_oK7HpFT42t-VJsmF9TCndgUVqYyLMEueZ2fZ0oM5Vo/edit`

## NORM-035

**Canonical title**

> Management of dyslipidemia in adults. A consensus statement from the French Society of Endocrinology (SFE), the French-speaking Diabetes Society (SFD), the New French-speaking Atherosclerosis Society (NSFA) and the French Society of Cardiology (SFC).

**Canonical identifiers**

- DOI: `10.1016/j.acvd.2026.01.001`
- PMID: `41651737`
- Year: `2026`
- PubMed: `https://pubmed.ncbi.nlm.nih.gov/41651737/`

**Document-unit rule**

Treat the joint French dyslipidemia consensus as one intellectual guideline/consensus unit anchored to NORM-035. The Drive audit identifies NORM-036 (`10.1016/j.ando.2025.102471`) and another Diabetes & Metabolism manifestation as linked co-publications of the same intellectual document. Those manifestations may provide retrieval/provenance evidence, but they do not create independent sentinel denominator units and must not silently replace the canonical NORM-035 identity.

## NORM-063

**Canonical title**

> Evidence and consensus-based clinical practice guidelines for management of overweight and obesity in midlife women: An AIIMS-DST initiative

**Canonical identifiers**

- DOI: `10.4103/jfmpc.jfmpc_51_22`
- PMID: `36994026`
- PMCID: `PMC10041015`
- Year: `2022`
- PubMed: `https://pubmed.ncbi.nlm.nih.gov/36994026/`
- PMC: `https://pmc.ncbi.nlm.nih.gov/articles/PMC10041015/`

**Document-unit rule**

Treat the complete AIIMS-DST clinical practice guideline as the parent intellectual document. The Drive audit identifies NORM-037 (`PMC9190956`; DOI `10.4103/jmh.jmh_7_22`) and NORM-038 (DOI `10.1016/j.dsx.2022.102426`) as Executive Summary/parallel manifestations. They can support locators and provenance but do not substitute for or increase the denominator of the parent NORM-063 unit.

## Matching rule for GF-02

Because both priority sentinels now have explicit canonical bibliographic identifiers, GF-02 matching uses DOI/PMID/PMCID identity rather than permissive title-only matching. A derivative manifestation with the same or similar title does not satisfy the parent sentinel unless it is explicitly reconciled to the canonical intellectual-document unit.

## Remaining GF-02 work

Identity resolution removes only the first blocker. GF-02 still requires:

- exact PubMed candidate v0.3 execution evidence;
- v0.2 and v0.3 recall using the same resolved sentinel suite;
- explicit status/explanation for NORM-035 and NORM-063;
- reproducible noise/precision sample;
- actual Scopus validation evidence or `MANUAL_EXECUTION_REQUIRED` followed by documented manual import;
- actual Web of Science validation evidence under the same rule;
- explicit human decision `READY_FOR_PRESS` or `NOT_READY_FOR_PRESS` after evidence completeness.

No value in this document should be used as a substitute for an execution ledger or provider export.
