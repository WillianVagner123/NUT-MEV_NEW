# Deployment checklist

The frontend is static; the backend is Supabase. Deployment should use HTTPS.

## 1. Supabase

- Create a dedicated project (recommended rather than reusing unrelated production data).
- Run `supabase/schema.sql` in SQL Editor.
- Create/invite admin and assessor users.
- Promote only the admin/adjudicator roles in SQL Editor.
- In Auth URL Configuration, add the exact deployed origin/path used by the app.
- Obtain the Project URL and **Publishable key** from the Connect dialog.

## 2. Static hosting

Set the host's publish/root directory to:

```text
apps/nutev-validation
```

No build command is required.

Examples:

- Vercel: Root Directory `apps/nutev-validation`, Framework Preset `Other`, no build command.
- Netlify: Publish directory `apps/nutev-validation`, no build command.
- Cloudflare Pages: output directory `apps/nutev-validation`, no build command.

The first browser visit asks for Supabase URL + Publishable key. This avoids committing environment-specific configuration to the repository.

## 3. Auth smoke test

- Known assessor receives a magic link and can sign in.
- Unknown e-mail is rejected because `shouldCreateUser=false`.
- Assessor can see only their own assigned rows.
- Admin sees progress counts during assessment, but raw assessor grades remain inaccessible until the status becomes `adjudication`.

## 4. Scientific smoke test

Before real judgments:

- use a disposable draft round and tiny synthetic/non-scientific demo packet;
- verify 0/1/2 + reason + timestamp save correctly;
- verify assessor A cannot read assessor B assignment rows;
- verify transition to adjudication fails while any decision is incomplete;
- verify export headers match `tools/validate_gold_standard.py`;
- delete the disposable round;
- only then import the real assessor-safe artifact.

Do not use synthetic labels as benchmark evidence. The disposable round is UI testing only.
