FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    NUTEV_OCR_LANG=eng+por

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        poppler-utils \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app
RUN python -m pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin nutev \
    && mkdir -p /app/project_output_reference/agent_context \
    && mkdir -p /app/apps/nutev-web/agent-context \
    && ln -s /app/project_output_reference/agent_context/article1 /app/apps/nutev-web/agent-context/article1 \
    && chown -R nutev:nutev /app

USER nutev
EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/health', timeout=4).read()" || exit 1

CMD ["sh", "-lc", "if python tools/build_article1_agent_context.py --output-root /app/project_output_reference; then echo '[nutev] Article 1 agent context refreshed'; else echo '[nutev] Article 1 agent context unavailable; dashboard will run in partial mode' >&2; fi; exec python apps/nutev-web/server.py --host 0.0.0.0 --port 8765 --no-browser"]
