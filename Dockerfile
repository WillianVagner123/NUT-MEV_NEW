FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN useradd --system --uid 10001 --create-home --home-dir /home/nutev nutev

COPY . /app

RUN python -m pip install --no-cache-dir . \
    && mkdir -p /app/project_output_reference \
    && chown -R nutev:nutev /app

USER nutev

EXPOSE 8765

CMD ["python", "apps/nutev-web/production_server.py", "--host", "0.0.0.0", "--port", "8765"]
