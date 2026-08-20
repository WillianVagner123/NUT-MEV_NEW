# NutEV Validation MVP threat model

## Assets to protect

1. assessor independence before decisions are locked;
2. hidden NutEV system/rank/score/taxonomy information;
3. another assessor's judgments;
4. immutable scientific identities (candidate runtime and frozen question set);
5. adjudication audit trail.

## Primary controls

- RLS on every public table.
- No anonymous table access.
- Role stored in `validation_profiles.role`; client cannot update that column.
- Assessors can select only their own assignment rows during assessment.
- Admin/adjudicator raw-decision access begins only after the round transitions to adjudication.
- Progress is materialized separately so admins can monitor completion without reading grades.
- Packet import rejects prohibited columns before inserting any reference data.
- Round transition trigger blocks incomplete/non-blind assessment closure.
- Round identity fields become immutable after draft.
- Final lock requires adjudication for every disagreement.

## Explicit non-goals

- This MVP does not host the external-test sealed set.
- It does not verify bibliographic truth or methodological quality.
- It does not protect against a malicious database owner/Supabase project administrator reading rows directly in SQL. Scientific governance must therefore ensure the project administrator is not one of the blinded assessors.
- It does not replace the repository's canonical `validate_gold_standard.py` or metric scripts.
