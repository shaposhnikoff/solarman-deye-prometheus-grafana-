FROM python:3.13.4-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.7.17 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    VIRTUAL_ENV=/opt/venv

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv venv "$VIRTUAL_ENV" \
    && uv sync --active --locked --no-dev --no-install-project

COPY solarman_exporter ./solarman_exporter
RUN uv sync --active --locked --no-dev --no-editable

FROM python:3.13.4-slim-bookworm

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system --gid 10001 solarman \
    && useradd --system --uid 10001 --gid solarman --create-home solarman

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY profiles/deye_hybrid.yaml ./profiles/deye_hybrid.yaml

USER solarman
EXPOSE 9800
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:9800/health', timeout=2)"

ENTRYPOINT ["solarman-exporter"]
