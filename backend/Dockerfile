FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
  --mount=type=bind,source=uv.lock,target=uv.lock \
  --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
  uv sync --frozen --no-install-project --no-dev

ADD . /app

RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-dev

FROM python:3.13-slim-bookworm

RUN apt-get update && apt-get install -y \
  build-essential \
  curl \
  software-properties-common \
  libgl1-mesa-glx \
  && rm -rf /var/lib/apt/lists/*

COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH"

RUN hf download climatebert/distilroberta-base-climate-f

ARG VERSION
ENV VERSION=${VERSION}
ARG VERSION_REVISION=""
ENV VERSION_REVISION=${VERSION_REVISION}

EXPOSE 8080

ENV HF_HUB_OFFLINE=1

ENTRYPOINT ["fastapi", "run", "/app/main.py", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]
