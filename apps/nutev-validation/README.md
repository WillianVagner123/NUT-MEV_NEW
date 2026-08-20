# NutEV Validation MVP

A lightweight, Rayyan-like web interface for the **blinded human relevance assessment** phase of the NutEV scientific validation benchmark.

This app is intentionally separate from the Reference Engine runtime. It does **not** calculate NutEV scores, rankings, benchmark metrics, or relevance labels automatically.

## What the MVP does

- passwordless/magic-link login through Supabase Auth;
- separate roles: `assessor`, `admin`, `adjudicator`;
- RLS-enforced assessor isolation;
- one-reference-at-a-time review with `0 / 1 / 2` relevance grades;
- mandatory reason, timestamp, review-later flag, keyboard shortcuts and progress;
- browser-side packet validation that rejects score/rank/taxonomy/system fields;
- admin import of the canonical `QUESTIONS.csv` plus two assessor-safe packet CSVs;
- transition guard from `assessment` to `adjudication` only after all blinded decisions are complete;
- conflict-only adjudication;
- export of `VALIDATION_ASSESSMENTS.csv` and `VALIDATION_GOLD_STANDARD.csv` in schemas compatible with `tools/validate_gold_standard.py`;
- hard MVP boundary: only `split = validation` is accepted. External-test data stays out of this application round.

## Scientific guardrails

The application must never receive the segregated audit artifact or benchmark rankings during initial assessment. Upload only the assessor-safe files:

- `ASSESSOR_assessor_A.csv`
- `ASSESSOR_assessor_B.csv`
- `VALIDATION_ASSESSOR_PACKETS_MANIFEST.json`
- canonical `validation/data/QUESTIONS.csv`

Do **not** upload or expose:

- `BENCHMARK_RANKINGS.csv`;
- `VALIDATION_POOL_AUDIT.csv`;
- NutEV score/rank/taxonomy;
- system membership/origin;
- another assessor's completed decisions before the round enters adjudication.

The database RLS policies reinforce this boundary: assessors can select only their own assignment rows; admin/adjudicator raw-decision access is blocked while the round is in `assessment`.

## Backend setup

1. Create a dedicated hosted Supabase project.
2. Open the SQL Editor and execute `supabase/schema.sql`.
3. Create/invite the assessor users in Supabase Auth. New users receive role `assessor` automatically.
4. Create your admin user and promote it once in the SQL Editor:

```sql
update public.validation_profiles
set role = 'admin', display_name = 'NutEV Admin'
where id = '<ADMIN_AUTH_USER_UUID>';
```

5. If using a separate adjudicator, promote that user similarly:

```sql
update public.validation_profiles
set role = 'adjudicator', display_name = 'Human Adjudicator'
where id = '<ADJUDICATOR_AUTH_USER_UUID>';
```

6. Configure Auth > URL Configuration with the deployed site URL and redirect URL.
7. Use a **Publishable key** (`sb_publishable_...`) in the browser. Never use `service_role` or a secret key.

Supabase's current documentation recommends publishable keys for client-side use and notes that legacy `anon` / `service_role` keys remain compatible only during the transition period. Magic-link login uses `signInWithOtp(..., { shouldCreateUser: false })` so unknown e-mails are not silently registered.

## Frontend setup

No build step is required. The app is plain static HTML/CSS/JS with version-pinned browser imports:

- `@supabase/supabase-js@2.112.3`
- `papaparse@5.6.0`

Serve this directory from any HTTPS static host (Vercel, Netlify, Cloudflare Pages, GitHub Pages, etc.). On first visit, the browser asks for:

- Supabase project URL;
- Supabase Publishable key.

Those values are stored only in that browser's `localStorage`. The publishable key is not a server secret; data authorization is enforced by RLS.

For local smoke testing:

```bash
cd apps/nutev-validation
python -m http.server 8080
```

Then open `http://localhost:8080`.

## Running the current validation round

1. Admin creates a round with the frozen candidate SHA and question-set SHA.
2. Admin selects two distinct users with role `assessor`.
3. Admin uploads `QUESTIONS.csv`, the assessor-packets manifest, packet A and packet B.
4. The browser verifies the question-set SHA-256, both packet SHA-256 values, manifest blind/order declarations, and rejects forbidden fields or non-empty decisions.
5. Import inserts the validation questions, common-pool references and each assessor's independent order, then changes the round to `assessment`.
6. Assessors work independently. No other assessor decisions are visible.
7. When both progress counters reach 100%, admin closes assessment. The database refuses the transition if any decision/reason/timestamp is missing or if `blind_to_nutev != true`.
8. Adjudicator resolves only disagreements.
9. Round can be locked only after every conflict is resolved.
10. Export assessments and gold CSVs, then run the repository's canonical validator and metrics tooling outside this web app.

## Current benchmark identity

The UI pre-fills, but does not silently alter, the current frozen identities:

- candidate runtime: `6aa7a5fe6009776e611ca3e1506486606b05f4f6`
- questions SHA-256: `55a0f654e49cb5a9b10249c373df168cac585167a245b828d667c7724fb64589`

Changing either value creates a distinct validation round and should be scientifically documented.

## Security notes

- Every exposed table has RLS enabled.
- SQL-created tables receive explicit Data API grants because current Supabase projects may not automatically expose new tables.
- Authorization roles live in a database table, not user-editable `user_metadata`.
- The browser never contains a `service_role` / secret key.
- Assessor update grants are column-limited so reviewer identity/order cannot be reassigned by the client.
- The app does not persist audit-system fields because they are rejected on import.
- A role is singular: an admin cannot simultaneously be assigned as an assessor by the provided RLS policy.

This MVP is designed for the current scientific gate, not as a general systematic-review platform yet.
