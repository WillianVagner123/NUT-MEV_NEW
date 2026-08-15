# Article 1 coding — compatibility note for the historical four-domain heuristic

The functions in `nutev.analysis.article1_coding` and `nutev.analysis.domain_states` are retained for reproducibility of historical runs and for assistive broad lexical inspection. They are **not** the canonical Article 1 ABCD scientific object.

## Current canonical model

The active methodological object is **ABCD-NutEV v1.1-candidate**, implemented in `nutev.analysis.article1_abcd`:

- A1-A5;
- B1-B9;
- C1-C10;
- D1-D10.

The unit of coding is `document x component x reviewer`, with presence first and depth second. A final included document must have 34/34 resolved components. Missing means unassessed, not absence. `DOUBT` is retained during review/calibration and cannot be a final closed state.

No global score, profile, number-of-domains-positive, mean depth, maturity score or ranking is a valid manuscript-facing ABCD result.

## What the historical heuristic may still do

The legacy code can suggest broad textual signals in A/B/C/D and preserve old outputs for reproducibility. It must remain visibly labelled as machine assistance/legacy compatibility and must not be used to:

- declare final ABCD presence/absence;
- assign final 34-component depth;
- infer integration or causal/function relations;
- rank documents;
- substitute for R1/R2 human coding or adjudication.

## Current implementation references

- Canonical ABCD contract: `src/nutev/analysis/article1_abcd.py`
- Screening calibration and decision semantics: `src/nutev/review/screening.py`
- Manuscript-safe 34-component export: `src/nutev/export/article1_exports.py::abcd_34_matrix_rows`
- Method note: `docs/ARTICLE1_ABCD_V11_IMPLEMENTATION.md`

This separation preserves historical reproducibility without allowing the deprecated four-domain heuristic to compete with the current protocol.
