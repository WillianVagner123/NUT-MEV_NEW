from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy" / "hetzner"


def test_hetzner_backend_is_not_publicly_published() -> None:
    compose = (DEPLOY / "compose.yaml").read_text(encoding="utf-8")
    assert '"127.0.0.1:8765:8765"' in compose
    assert '"8765:8765"' not in compose.replace('"127.0.0.1:8765:8765"', "")
    assert '"80:80"' in compose
    assert '"443:443"' in compose


def test_hetzner_proxy_requires_authentication_and_tls_hostname() -> None:
    caddy = (DEPLOY / "Caddyfile").read_text(encoding="utf-8")
    assert "{$NUTEV_DOMAIN}" in caddy
    assert "basic_auth" in caddy
    assert "{$NUTEV_BASIC_AUTH_USER}" in caddy
    assert "{$NUTEV_BASIC_AUTH_HASH}" in caddy
    assert "reverse_proxy nutev:8765" in caddy


def test_production_image_contains_ocr_and_healthcheck() -> None:
    dockerfile = (DEPLOY / "Dockerfile").read_text(encoding="utf-8")
    assert "poppler-utils" in dockerfile
    assert "tesseract-ocr-eng" in dockerfile
    assert "tesseract-ocr-por" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "/api/health" in dockerfile
    assert '"--no-browser"' in dockerfile


def test_env_template_contains_no_real_secret() -> None:
    template = (DEPLOY / ".env.example").read_text(encoding="utf-8")
    assert "REPLACE_WITH_CADDY_PASSWORD_HASH" in template
    assert "NUTEV_BASIC_AUTH_HASH=" in template
    assert "NUTEV_DOMAIN=nutev.example.com" in template
