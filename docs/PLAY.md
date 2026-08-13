# NutEV PLAY

`nutev play` is the one-command computational orchestrator for current NutEV PILOT workflows.

## Current scope

PLAY remains deliberately **PILOT-only**. It can execute a registered PILOT strategy, build a deduplicated corpus, resolve lawful open-access full text, download accessible artifacts, extract native text and use OCR when needed. It does not create human decisions and does not authorize FORMAL/PRISMA execution.

```text
registered PILOT strategy
        ↓
provider execution + immutable snapshots
        ↓
corpus + deterministic deduplication
        ↓
lawful OA resolution/download
        ↓
native extraction / OCR when needed
        ↓
12_play/<play_id>/ audit package
```

## Run

```powershell
.\.venv\Scripts\nutev.exe play --project-root .\project_output_scientific
```

Metadata-only:

```powershell
.\.venv\Scripts\nutev.exe play --project-root .\project_output_scientific --metadata-only
```

## Output

Each run writes an auditable package under `12_play/`, including state/summary files, provider summary, full-text ledger, download/failure manifests and extraction manifest. The final JSON summary is hashed separately. Provider-reported totals versus returned rows are compared so truncation cannot be hidden.

## Formal execution boundary

The lower canonical strategy executor now has a separate FORMAL safety guard. A strategy marked `FORMAL` or PRISMA-eligible cannot start there unless persisted GF-02…GF-10/freeze evidence authorizes the exact strategy version and matches the frozen Git SHA/configuration digest.

That guard does **not** make PLAY a formal one-command Article 1 orchestrator. PLAY continues to reject PRISMA-eligible versions until the complete multi-track formal workflow is integrated and validated.

## Human boundary

Neither PLAY nor the lower executor may infer `INCLUDE`, `EXCLUDE`, `ADJUDICATED`, PRESS approval, freeze authorization or a clinical recommendation. Human/external evidence must be recorded explicitly.

## Full-text boundary

PLAY attempts lawful open-access resolution and ordinary public retrieval only. Paywalls are not bypassed; unavailable content remains visible as paywall/metadata-only/failure evidence.

## Not yet one-command FORMAL

A definitive Article 1 run must still coordinate real GF-02 evidence, PRESS, final temporal/filter decisions, reviewer setup, GF-10, Scopus/Web of Science licensed/manual evidence, and verified institutional/guideline-repository routes. Those scientific dependencies are reported, not fabricated.
