# NutEV on Hetzner

This deployment publishes the NutEV Search + Radar behind HTTPS and Basic Auth while keeping the Python service off the public interface.

## Production shape

```text
Internet
  -> 80/443 Caddy
  -> TLS + Basic Auth
  -> Docker private network
  -> NutEV web :8765
  -> persistent Docker volume: project_output_reference/
```

The NutEV service is also bound to `127.0.0.1:8765` on the host. That loopback binding is intended for health checks and SSH tunnelling only; port 8765 must never be opened in the Hetzner firewall.

The existing server intentionally keeps validation coordination/adjudication/gold/metrics/decision-lock endpoints loopback-only. Public deployment therefore exposes Search, Radar and reviewer-safe routes through Caddy, but administrative validation actions should be used through an SSH tunnel unless a future dedicated multi-user backend replaces this contract.

## Suggested first server

Use a current Ubuntu LTS x86_64 Hetzner Cloud VM with at least:

- 4 vCPU;
- 8 GB RAM;
- 80 GB SSD;
- public IPv4/IPv6;
- backups or snapshots enabled if the instance will hold primary runtime artifacts.

This is an operational starting point, not a benchmark. OCR and concurrent provider searches are the main reasons not to start at the smallest VM size.

## Firewall

Allow:

- TCP 22 only from trusted administration IPs when practical;
- TCP 80 from the internet;
- TCP 443 from the internet;
- UDP 443 from the internet for HTTP/3 (optional).

Do **not** allow public TCP 8765.

## DNS

Create an `A` record (and optionally `AAAA`) such as:

```text
nutev.example.org -> HETZNER_PUBLIC_IP
```

Wait until DNS resolves to the server before starting Caddy so automatic TLS can succeed.

## Host preparation

Install Docker Engine and the Docker Compose plugin using Docker's supported Ubuntu installation method. Then clone this repository on the server.

From the repository root:

```bash
cd deploy/hetzner
cp .env.example .env
```

Generate a Basic Auth password hash locally on the server:

```bash
docker run --rm caddy:2-alpine caddy hash-password --plaintext 'CHOOSE_A_STRONG_PASSWORD'
```

Place the returned hash in `NUTEV_BASIC_AUTH_HASH` and set the real domain/user in `.env`.

Provider credentials and contact e-mails are optional but should be configured in `.env` when used. Never commit `.env`.

## Start

From `deploy/hetzner/`:

```bash
docker compose up -d --build
```

Check status:

```bash
docker compose ps
docker compose logs --tail=100 nutev
docker compose logs --tail=100 caddy
```

Verify that the public proxy is enforcing authentication before entering credentials:

```bash
curl -I https://YOUR_DOMAIN/
```

An unauthenticated request should return an authentication challenge rather than application content. Use the browser for authenticated access.

The server-local health endpoint does not traverse the public proxy:

```bash
curl http://127.0.0.1:8765/api/health
```

## Administrative validation through SSH

Because sensitive coordination endpoints intentionally accept only loopback clients, create a tunnel from the administrator workstation:

```bash
ssh -L 8765:127.0.0.1:8765 USER@HETZNER_PUBLIC_IP
```

Then open locally:

```text
http://127.0.0.1:8765/validation/
```

This preserves the existing scientific access boundary instead of weakening `_require_loopback()` for convenience.

## Persistence

`project_output_reference/` is stored in the Docker named volume `nutev_output`. Container replacement therefore does not erase completed searches, CORE artifacts, Radar/Watch outputs or validation-server state stored under that tree.

Create a backup from `deploy/hetzner/`:

```bash
mkdir -p backups
docker compose exec -T nutev tar -C /app -czf - project_output_reference > "backups/nutev-output-$(date +%F-%H%M%S).tgz"
```

Backups should also be copied off the VM.

## Updating

After a reviewed merge to `main`:

```bash
git fetch origin
git checkout main
git pull --ff-only
docker compose build --pull nutev
docker compose up -d
curl http://127.0.0.1:8765/api/health
```

Do not deploy arbitrary feature branches over the production dataset.

## Rollback

Keep the previous Git commit SHA before every deploy. To roll back application code:

```bash
git checkout PREVIOUS_GOOD_SHA
docker compose build nutev
docker compose up -d
```

The named runtime volume is not replaced by this operation. If a future schema migration is introduced, its rollback rules must be documented separately before deployment.

## OCR

The image installs:

- `poppler-utils` (`pdftotext`, `pdftoppm`);
- Tesseract OCR;
- English language data;
- Portuguese language data.

Default `NUTEV_OCR_LANG=eng+por` can be changed in `.env`.

## Security boundaries

- Caddy is the only internet-facing service.
- NutEV port 8765 is host-loopback + Docker-network only.
- Basic Auth protects the public site in this first deployment.
- HTTPS certificates are managed automatically by Caddy after DNS is correct.
- Runtime outputs and `.env` are excluded from the container build context.
- Search/Radar metrics remain operational signals, not scientific quality/certainty/recommendations.
- PRISMA remains optional/downstream.

## Not solved by this first deployment

This stack is appropriate for a controlled private beta. It is **not** yet a full institutional multi-tenant backend. Before public self-registration or unrelated external users are allowed, add dedicated identity/RBAC, durable job queueing, database-backed sessions, audit-log retention policy, storage quotas and a formal privacy/security review.
