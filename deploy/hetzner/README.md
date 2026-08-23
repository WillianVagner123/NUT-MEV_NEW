# NutEV no Hetzner — Production v1

Este stack publica o NutEV com HTTPS/autenticação quando o VPS é dedicado e também oferece um modo seguro para encaixar o NutEV em um Hetzner que já hospeda outros sistemas.

## Primeiro: descubra se o VPS é dedicado ou compartilhado

Antes de instalar/subir qualquer proxy novo, rode no servidor:

```bash
hostname
ss -lntup | grep -E ':(22|80|443|8765)\b' || true
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}' || true
systemctl --type=service --state=running | grep -Ei 'nginx|caddy|apache|traefik|docker' || true
df -h
free -h
```

Se 80/443 já estiverem ocupadas por Nginx, Caddy, Traefik ou outro stack, use **Modo B — servidor compartilhado**. Não tente subir o Caddy embutido do NutEV por cima.

## Arquitetura

### Modo A — VPS dedicado ao NutEV

```text
Internet
  |
  | :80 / :443
  v
Caddy do NutEV
  |-- reviewer page/API -> token privado do avaliador
  |-- demais rotas -> Basic Auth do coordenador
  |                    + segredo interno injetado no proxy
  v
NutEV production_server.py :8765 (somente rede Docker)
  |
  v
volume nutev_data -> /app/project_output_reference
```

### Modo B — VPS compartilhado

```text
Internet
  |
  v
proxy que já existe no servidor
  |
  | HTTPS + autenticação do coordenador
  | + header X-NutEV-Coordinator-Secret
  v
127.0.0.1:8765
  |
  v
NutEV container
```

No modo compartilhado, 8765 fica ligada **somente ao loopback do host**.

## 1. Servidor e firewall

Recomendação inicial para Busca Global pesada: Ubuntu 24.04 LTS, 4+ vCPU, 8+ GB RAM e SSD suficiente para os resultados.

No Hetzner Cloud Firewall permita somente o necessário:

- TCP 22 a partir do seu IP administrativo;
- TCP 80 de qualquer origem se o proxy público usa HTTP/ACME;
- TCP 443 de qualquer origem;
- UDP 443 de qualquer origem somente se o proxy usa HTTP/3.

Mantenha saída liberada para que os providers científicos possam ser consultados.

## 2. DNS

Crie um registro A para o domínio escolhido apontando para o IPv4 do servidor, por exemplo:

```text
nutev.seudominio.com -> 203.0.113.10
```

Se usar IPv6, adicione AAAA.

## 3. Instalar Docker Engine + Compose no Ubuntu

Se Docker já existir, apenas confirme `docker compose version` e não reinstale.

Em servidor novo, execute como root ou com sudo:

```bash
apt update
apt install -y ca-certificates curl git openssl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

cat >/etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
docker compose version
```

## 4. Clonar o NutEV

```bash
cd /opt
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git nutev
cd /opt/nutev
```

Use `main` para produção. Branch/PR é apenas staging.

## 5. Preparar dados privados

```bash
mkdir -p /opt/nutev-private/validation_assessor_packets
chmod 700 /opt/nutev-private
```

Quando a rodada científica for executada, coloque nesse diretório somente os pacotes privados necessários. Nunca versione esses arquivos.

## 6. Criar o arquivo de ambiente

```bash
cd /opt/nutev
cp deploy/hetzner/env.example deploy/hetzner/.env
```

Gere o hash da senha do coordenador:

```bash
docker run --rm -it caddy:2-alpine caddy hash-password --algorithm argon2id
```

Gere o segredo interno do proxy:

```bash
openssl rand -hex 32
```

Edite:

```bash
nano deploy/hetzner/.env
```

Preencha obrigatoriamente:

- `NUTEV_DOMAIN`;
- `NUTEV_BASIC_USER`;
- `NUTEV_BASIC_HASH` (mantenha entre aspas simples);
- `NUTEV_PROXY_COORDINATOR_SECRET`;
- `NCBI_EMAIL` ou `ENTREZ_EMAIL` para operação responsável com PubMed.

Adicione chaves opcionais dos providers se disponíveis.

## 7. Validar Compose

```bash
docker compose \
  --env-file deploy/hetzner/.env \
  -f deploy/hetzner/compose.yaml \
  config
```

Não prossiga se houver variável vazia, erro de YAML ou caminho privado incorreto.

# Modo A — VPS dedicado

Use somente se 80/443 estiverem livres.

## 8A. Subir NutEV + Caddy

```bash
docker compose \
  --profile edge \
  --env-file deploy/hetzner/.env \
  -f deploy/hetzner/compose.yaml \
  up -d --build
```

Verifique:

```bash
docker compose \
  --profile edge \
  --env-file deploy/hetzner/.env \
  -f deploy/hetzner/compose.yaml \
  ps
```

Sem credenciais, a home deve responder 401:

```bash
curl -I https://SEU_DOMINIO/
```

No navegador, acesse `https://SEU_DOMINIO/` e use o usuário/senha do coordenador.

Os links privados dos avaliadores não exigem a senha do coordenador; continuam protegidos pelo token cego da rodada.

# Modo B — servidor Hetzner compartilhado

Use quando já existe Nginx/Caddy/Traefik/site em 80/443.

## 8B. Subir somente o backend NutEV

```bash
docker compose \
  --env-file deploy/hetzner/.env \
  -f deploy/hetzner/compose.yaml \
  -f deploy/hetzner/compose.shared.yaml \
  up -d --build nutev
```

Confirme que o backend está apenas no loopback:

```bash
ss -lntp | grep 8765
curl http://127.0.0.1:8765/api/health
```

O resultado esperado no `ss` é `127.0.0.1:8765`, nunca `0.0.0.0:8765`.

Depois configure o reverse proxy existente para:

1. servir `NUTEV_DOMAIN` por HTTPS;
2. exigir autenticação do coordenador nas rotas normais;
3. permitir publicamente somente:
   - `/validation/review.html`;
   - `/validation/styles.css`;
   - `/validation/server-review.css`;
   - `/validation/server-review.js`;
   - `/api/validation/reviewer`;
   - `/api/validation/reviewer/save`;
   - `/api/validation/reviewer/submit`;
4. encaminhar as rotas autenticadas para `http://127.0.0.1:8765` adicionando:

```text
X-NutEV-Coordinator-Secret: <mesmo valor de NUTEV_PROXY_COORDINATOR_SECRET>
```

Não adicione esse header nas rotas públicas do avaliador.

Se o proxy atual for Caddy, o arquivo `deploy/hetzner/Caddyfile` serve como referência. Se for Nginx/Traefik, replique exatamente a mesma separação de rotas e segredo interno.

## 9. Logs

Modo dedicado:

```bash
docker compose --profile edge --env-file deploy/hetzner/.env -f deploy/hetzner/compose.yaml logs -f --tail=200
```

Modo compartilhado:

```bash
docker compose --env-file deploy/hetzner/.env -f deploy/hetzner/compose.yaml -f deploy/hetzner/compose.shared.yaml logs -f --tail=200 nutev
```

## 10. Testes funcionais

Depois do domínio estar respondendo:

- Buscar evidências;
- Minhas buscas;
- Validação científica;
- `GET /api/health` após autenticação;
- preparar uma rodada somente quando os materiais privados reais estiverem instalados;
- abrir um link privado de avaliador em janela anônima e confirmar que ele não recebe credenciais de coordenador.

## 11. Atualizar produção

Nunca atualize no meio de uma Busca Global longa na Production v1.

```bash
cd /opt/nutev
git fetch origin
git checkout main
git pull --ff-only origin main
```

Depois repita o `docker compose ... up -d --build` do modo escolhido.

## 12. Backup do estado persistente

```bash
mkdir -p /opt/nutev-backups

docker run --rm \
  -v nutev_data:/data:ro \
  -v /opt/nutev-backups:/backup \
  alpine sh -c 'tar czf /backup/nutev-data-$(date +%Y%m%d-%H%M%S).tgz -C /data .'
```

Esse volume contém histórico de buscas persistidas e o estado privado da validação server-backed.

## Limitação conhecida da Production v1

Resultados concluídos e a base server-backed da validação são persistidos em volume. Porém o registro de um job de busca **em andamento** ainda vive na memória do processo web.

Fechar o notebook do usuário não afeta a busca porque ela roda no Hetzner. Porém reiniciar/redeployar o container no meio da busca pode interromper o job atual.

A próxima hardening é mover fila/status de busca para armazenamento persistente e worker recuperável.

## Segurança

- Em VPS dedicado, não publique `8765:8765`.
- Em VPS compartilhado, publique somente `127.0.0.1:8765:8765`.
- Não envie `NUTEV_PROXY_COORDINATOR_SECRET` ao navegador, logs compartilhados ou avaliadores.
- Não coloque pacotes cegos, banco SQLite privado ou outputs de validação no Git.
- Reviewer token continua em fragmento URL e não deve ser convertido em query string.
- Scopus/Web of Science não devem ser simulados quando não houver acesso licenciado.
