# NutEV Hetzner auto-deploy

## Goal

Deploy the exact commit that passed the `ci` workflow on `main` to the existing Hetzner host without deleting the persistent NutEV data volume.

## Trigger

`.github/workflows/deploy-hetzner.yml` listens for a completed `ci` workflow. Production deploy runs only when:

- CI concluded with `success`;
- CI head branch is `main`;
- repository/environment variable `HETZNER_AUTODEPLOY` equals `true`.

`workflow_dispatch` remains available for an explicit redeploy of the current commit, still requiring the enable flag.

## GitHub production environment

Create an environment named `production` and configure these secrets:

- `HETZNER_HOST`: server hostname or IP;
- `HETZNER_USER`: SSH deployment user;
- `HETZNER_SSH_KEY`: private SSH key dedicated to deployment;
- `HETZNER_APP_DIR`: absolute repository path on the server;
- `HETZNER_PORT`: optional SSH port; blank means 22.

Set the Actions variable:

- `HETZNER_AUTODEPLOY=true`

Until that variable exists, the deploy job is skipped.

## Server prerequisites

The deployment user must be able to:

- read/write the repository at `HETZNER_APP_DIR`;
- fetch `origin/main`;
- run Docker and Docker Compose;
- read `deploy/hetzner/.env`.

The production `.env` remains on the server and is never committed.

## Deployment sequence

```text
main commit
  -> CI success
  -> SSH to Hetzner
  -> fetch exact CI head SHA
  -> build nutev:<sha>
  -> isolated preflight container on 127.0.0.1:18765
  -> /api/health must pass
  -> switch production nutev service to nutev:<sha>
  -> /api/health on 127.0.0.1:8765 must pass
  -> success
```

The previous running image is tagged `nutev:rollback` before the switch. If the production health check fails, Compose restores that image and the workflow exits as failed.

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

Caddy is the public 80/443 entrypoint and applies TLS plus Basic Auth. Do not expose 8765 in the Hetzner firewall.

## First activation

Before setting `HETZNER_AUTODEPLOY=true`, verify once on the server:

```bash
cd /absolute/path/to/NutEV-Evidence-Engine
cp deploy/hetzner/.env.example deploy/hetzner/.env  # only if .env does not already exist
# fill real domain/auth/provider values in deploy/hetzner/.env
docker compose --env-file deploy/hetzner/.env -f deploy/hetzner/compose.yaml config
docker compose --env-file deploy/hetzner/.env -f deploy/hetzner/compose.yaml up -d --build
curl -fsS http://127.0.0.1:8765/api/health
```

If the current live server already has a valid `.env`, keep it. Do not overwrite it during activation.
