# -------- Build stage --------
FROM ghcr.io/astral-sh/uv:python3.13-bookworm AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

WORKDIR /app

# Install dependencies only
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-default-groups

# Copy project and install remaining deps
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-default-groups

# -------- Final stage --------
FROM debian:trixie-slim

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

# Install LibreOffice + minimal common fonts + fontconfig
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-core libreoffice-writer libreoffice-calc libreoffice-impress \
    fonts-dejavu fonts-liberation fonts-freefont-ttf fontconfig \
    && fc-cache -fv \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy virtual environment and project
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

# Expose ports
EXPOSE 8000/tcp 8000/udp

# Check LibreOffice version
RUN libreoffice --version && fc-list | head -n 10

