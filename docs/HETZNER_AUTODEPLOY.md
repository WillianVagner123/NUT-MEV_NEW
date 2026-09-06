# NutEV Hetzner auto-deploy

## Goal

Deploy the exact commit that passed the `ci` workflow on `main` to the existing Hetzner host without deleting the persistent NutEV data volume.

## Trigger

`.github/workflows/deploy-hetzner.yml` supports two distinct paths.

### Automatic deploy

A completed `ci` workflow triggers production deploy only when:

- CI concluded with `success`;
- CI head branch is `main`;
- repository/environment variable `HETZNER_AUTODEPLOY` equals `true`.

### Manual deploy

`workflow_dispatch` can explicitly deploy the currently selected `main` commit even when `HETZNER_AUTODEPLOY` is disabled. Manual dispatch is restricted to `refs/heads/main`; it cannot be used to publish an arbitrary feature branch.

This separation allows an operator to keep continuous auto-deploy disabled while still performing an intentional, auditable production release.

## GitHub production environment

Create an environment named `HETZNER` to match the workflow and configure:

### Environment/repository variables

- `HETZNER_HOST`: server hostname or IP;
- `HETZNER_USER`: SSH deployment user;
- `HETZNER_APP_DIR`: absolute repository path on the server;
- `HETZNER_PORT`: optional SSH port; blank means 22;
- `HETZNER_AUTODEPLOY`: optional; set to `true` only when every successful `main` CI should deploy automatically.

### Secret

- `HETZNER_SSH_KEY`: complete **private** SSH key dedicated to deployment. Use an unencrypted OpenSSH/PEM private key whose public half is installed in the target user's `~/.ssh/authorized_keys`. Do not store the `.pub` key in this secret.

The workflow normalizes Windows CRLF and one-line secrets containing literal `\n` sequences before use. It then validates the private key locally with `ssh-keygen` and performs a non-interactive SSH probe before any Git/Docker operation on the server. Invalid, public-only or passphrase-protected key material fails before deployment with an explicit error.

Leaving `HETZNER_AUTODEPLOY` unset or false disables only the automatic `workflow_run` path. It does not disable an explicit manual deploy from `main`.

## Server prerequisites

The deployment user must be able to:

- authenticate with the public half of `HETZNER_SSH_KEY`;
- read/write the repository at `HETZNER_APP_DIR`;
- fetch `origin/main`;
- run Docker and Docker Compose;
- read `deploy/hetzner/.env`.

The production `.env` remains on the server and is never committed.

## Deployment sequence

```text
manual main dispatch OR successful main CI with autodeploy enabled
  -> resolve exact TARGET_SHA
  -> normalize and validate private SSH key
  -> non-interactive SSH probe
  -> SSH to Hetzner
  -> fetch origin/main and reset to TARGET_SHA
  -> build nutev:<sha> with build identity
  -> isolated preflight container on 127.0.0.1:18765
  -> /api/health must pass
  -> /api/version commit must equal TARGET_SHA
  -> switch production nutev service to nutev:<sha>
  -> /api/health on 127.0.0.1:8765 must pass
  -> /api/version commit must still equal TARGET_SHA
  -> success
```

The previous running image is tagged `nutev:rollback` before the switch. If the production health check or build-identity check fails, Compose restores that image and the workflow exits as failed.

## SSH troubleshooting

If Actions reports `Load key ... error in libcrypto`, first re-save `HETZNER_SSH_KEY` with the complete private-key block, including the BEGIN/END lines. The workflow handles CRLF and literal `\n`, but it cannot reconstruct a truncated key, convert a public key into a private key, or unlock a passphrase-protected key.

The secret should resemble one of these private-key envelopes:

```text
-----BEGIN OPENSSH PRIVATE KEY-----
...
-----END OPENSSH PRIVATE KEY-----
```

or another private PEM format accepted by `ssh-keygen`. Never paste `ssh-ed25519 AAAA...` / `ssh-rsa AAAA...` into `HETZNER_SSH_KEY`; that is the public key format and belongs in the server's `authorized_keys`.

## Persistence

`deploy/hetzner/compose.yaml` uses the named volume:

```text
nutev_output:/app/project_output_reference
```

Normal deploys use `docker compose up`, not `down -v`, so searches, CORE outputs, Workbench SQLite, Radar/Watch and other persisted data survive container recreation.

## Network boundary

NutEV port 8765 binds only to host loopback:

```text
127.0.0.1:8765:8765
```

Caddy is the public 80/443 entrypoint and applies TLS plus Basic Auth where configured. Do not expose 8765 in the Hetzner firewall.

## First activation

Before enabling automatic deployment, verify once on the server:

```bash
cd /absolute/path/to/NutEV-Evidence-Engine
cp deploy/hetzner/.env.example deploy/hetzner/.env  # only if .env does not already exist
# fill real domain/auth/provider values in deploy/hetzner/.env
docker compose --env-file deploy/hetzner/.env -f deploy/hetzner/compose.yaml config
docker compose --env-file deploy/hetzner/.env -f deploy/hetzner/compose.yaml up -d --build
curl -fsS http://127.0.0.1:8765/api/health
```

If the current live server already has a valid `.env`, keep it. Do not overwrite it during activation.

After this preflight, either keep `HETZNER_AUTODEPLOY` disabled and release with `workflow_dispatch` from `main`, or set it to `true` to enable automatic deployment after successful `main` CI.
