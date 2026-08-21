# NutEV Validation — deployment and operation

## Canonical current deployment

The current benchmark round uses the unified NutEV server:

```bash
python apps/nutev-web/server.py
```

Coordinator URL:

```text
http://127.0.0.1:8765/validation/
```

For assessors on the same LAN:

```bash
python apps/nutev-web/server.py --host 0.0.0.0
```

Then configure **Endereço dos avaliadores** in the coordinator page with the reachable LAN/HTTPS origin. Coordinator-only scientific actions remain loopback-restricted.

Do not expose the raw HTTP server directly to the public internet. Remote/institutional use requires an authenticated HTTPS layer or a dedicated hosted backend.

## Canonical smoke test before real judgments

Use only synthetic/non-scientific fixture data for software testing. Confirm:

- `/api/health` responds;
- the validation page loads;
- a round cannot prepare when scientific readiness fails;
- two distinct reviewer sessions are created when readiness passes;
- localhost reviewer-copy buttons stay blocked until a reachable reviewer base is configured;
- assessor A cannot use assessor B's token;
- save/resume works;
- incomplete assessment cannot be submitted;
- submitted assessments become immutable;
- adjudication opens only after both submissions are locked;
- only conflicts appear in adjudication;
- gold generation refuses unresolved conflicts or broken blinding;
- canonical gold validator must return PASS before metrics;
- metrics are restricted to `split=validation`, `nutev_full` vs `lexical_baseline`, depth 100;
- decision lock is deterministic and tamper-detecting;
- `external_test` remains sealed throughout the validation-stage workflow.

Synthetic labels are software-test fixtures only and must never be reported as benchmark evidence.

## Persistence

Private operational state is stored under:

```text
project_output_reference/16_validation_server/
```

The directory is ignored by Git. Preserve it when moving or backing up a live validation round.

## Legacy/optional hosted Supabase implementation

The repository still contains an earlier hosted implementation under:

```text
apps/nutev-validation/supabase/
```

and browser code in `app.js`.

That path is **not the canonical deployment for the current round**. It remains an optional foundation for a future authenticated multiuser deployment. If it is revived later, it requires a dedicated Supabase project, RLS review, HTTPS hosting, controlled role provisioning and a fresh security audit before real benchmark data are used.

Never place `service_role` or other secret credentials in browser code, and never expose assessor audit/ranking fields or sealed external-test data to initial assessors.
