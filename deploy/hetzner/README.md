# NutEV no Hetzner — Production v1

Este stack publica o NutEV atrás de Caddy, com HTTPS automático, autenticação do coordenador e persistência dos outputs privados.

## Arquitetura

```text
Internet
  |
  | :80 / :443
  v
Caddy
  |-- reviewer page/API -> token privado do avaliador
  |-- demais rotas -> Basic Auth do coordenador
  |                    + segredo interno injetado no proxy
  v
NutEV production_server.py :8765 (somente rede Docker)
  |
  v
volume nutev_data -> /app/project_output_reference
```

A porta 8765 não deve ser publicada no host.

## 1. Servidor e firewall

Recomendação inicial: Ubuntu 24.04 LTS, 4+ vCPU, 8+ GB RAM e SSD suficiente para as buscas globais.

No Hetzner Cloud Firewall permita somente:

- TCP 22 a partir do seu IP administrativo;
- TCP 80 de qualquer origem;
- TCP 443 de qualquer origem;
- UDP 443 de qualquer origem (opcional, HTTP/3 do Caddy).

Mantenha saída liberada para que os providers científicos possam ser consultados.

## 2. DNS

Crie um registro A para o domínio escolhido apontando para o IPv4 do servidor, por exemplo:

```text
nutev.seudominio.com -> 203.0.113.10
```

Se usar IPv6, adicione também AAAA.

## 3. Instalar Docker Engine + Compose no Ubuntu

Execute como root ou com sudo:

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
mkdir -p /opt/nutev
cd /opt
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git nutev
cd /opt/nutev
```

Use `main` para produção. Para testar uma PR antes do merge, faça checkout explicitamente da branch correspondente e trate o ambiente como staging.

## 5. Preparar dados privados

```bash
mkdir -p /opt/nutev-private/validation_assessor_packets
chmod 700 /opt/nutev-private
```

Quando a rodada científica for realmente executada, coloque nesse diretório somente os pacotes privados necessários. Nunca versione esses arquivos.

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

## 7. Validar configuração antes de subir

```bash
docker compose \
  --env-file deploy/hetzner/.env \
  -f deploy/hetzner/compose.yaml \
  config
```

Não prossiga se houver variável vazia, erro de YAML ou caminho privado incorreto.

## 8. Build e start

```bash
docker compose \
  --env-file deploy/hetzner/.env \
  -f deploy/hetzner/compose.yaml \
  up -d --build
```

Verifique:

```bash
docker compose \
  --env-file deploy/hetzner/.env \
  -f deploy/hetzner/compose.yaml \
  ps
```

Logs:

```bash
docker compose \
  --env-file deploy/hetzner/.env \
  -f deploy/hetzner/compose.yaml \
  logs -f --tail=200
```

## 9. Testes pós-deploy

Sem credenciais, a home deve responder 401:

```bash
curl -I https://SEU_DOMINIO/
```

No navegador, acesse:

```text
https://SEU_DOMINIO/
```

O navegador solicitará usuário e senha do coordenador.

Teste também:

- Buscar evidências;
- Minhas buscas;
- Validação científica;
- `GET /api/health` após autenticação;
- link privado real de avaliador quando uma rodada existir.

O link do avaliador não usa a senha do coordenador; ele continua protegido pelo token no fragmento e pelo Bearer token interno da UI.

## 10. Atualizar produção

Nunca atualize no meio de uma Busca Global longa na versão v1.

```bash
cd /opt/nutev
git fetch origin
git checkout main
git pull --ff-only origin main

docker compose \
  --env-file deploy/hetzner/.env \
  -f deploy/hetzner/compose.yaml \
  up -d --build
```

## 11. Backup do estado persistente

```bash
mkdir -p /opt/nutev-backups

docker run --rm \
  -v nutev_data:/data:ro \
  -v /opt/nutev-backups:/backup \
  alpine sh -c 'tar czf /backup/nutev-data-$(date +%Y%m%d-%H%M%S).tgz -C /data .'
```

Esse volume contém histórico de buscas persistidas e o estado privado da validação server-backed.

## 12. Restore

Pare o stack antes de restore:

```bash
docker compose --env-file deploy/hetzner/.env -f deploy/hetzner/compose.yaml down
```

Restaure um backup somente depois de verificar o arquivo escolhido e mantenha uma cópia do estado atual antes de sobrescrever o volume.

## Limitação conhecida da Production v1

Os resultados concluídos e a base server-backed da validação são persistidos em volume. Porém o registro de um job de busca **em andamento** ainda vive na memória do processo web. Fechar o notebook do usuário não afeta a busca porque ela roda no Hetzner, mas reiniciar/redeployar o container no meio da busca pode interromper o job atual.

Antes de tratar Busca Global como workload durável de muitas horas/dias, a próxima hardening deve mover a fila de jobs para armazenamento persistente/worker recuperável.

## Segurança

- Não publique `8765:8765` no Compose.
- Não envie `NUTEV_PROXY_COORDINATOR_SECRET` para navegador, logs compartilhados ou avaliadores.
- Não coloque pacotes cegos, banco SQLite privado ou outputs de validação no Git.
- Reviewer token continua em fragmento URL e não deve ser convertido em query string.
- Scopus/Web of Science não devem ser simulados quando não houver acesso licenciado.
