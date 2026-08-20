# Local blind-review mode

`NutEV Validation` can now run without Supabase for early usability testing or isolated assessor work.

## What it does

The landing page offers **Local blind mode** and the future **Online multi-user mode**. Local mode:

- reads files entirely in the browser;
- requires the frozen `QUESTIONS.csv`, the assessor-packets manifest, and exactly one assessor packet;
- verifies the current frozen question-set SHA-256;
- verifies the selected packet SHA-256 against the assessor manifest;
- rejects score/rank/taxonomy/system-origin fields before review;
- stores the packet, decisions, and in-progress drafts in browser IndexedDB;
- supports 0/1/2 grading, mandatory reason, review-later flag, blind-status declaration, keyboard shortcuts, and progress;
- resumes after closing/reopening the browser;
- exports the completed assessor CSV in the benchmark packet schema;
- can export a local JSON backup of the session.

## Scientific boundary

Local mode is **not a replacement for independent custody**. For real blinded assessment:

1. use one browser profile or device per assessor;
2. never load assessor A and assessor B packets into the same browser profile;
3. never provide audit/rank/system artifacts to assessors;
4. preserve the exported completed assessor CSVs separately;
5. do not use the local JSON backup as the canonical benchmark evidence file;
6. external-test remains outside this MVP.

The eventual online mode remains preferable for multi-user auditability because backend RLS can enforce reviewer isolation centrally.

## Files to load

For the current validation round, load only:

- canonical `validation/data/QUESTIONS.csv`;
- `VALIDATION_ASSESSOR_PACKETS_MANIFEST.json`;
- the assessor's own `ASSESSOR_*.csv`.

Do not load `BENCHMARK_RANKINGS.csv`, `VALIDATION_POOL_AUDIT.csv`, NutEV outputs, or the other assessor's completed packet.
