FROM ghcr.io/astral-sh/uv:python3.14-alpine AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install dependencies only (no project code yet)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-default-groups

# Copy the actual project and install remaining deps
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-default-groups


# -------- Final stage --------
FROM python:3.14-alpine


WORKDIR /app

RUN apk add libreoffice

# Copy .venv first so PATH points to working environment
COPY --from=builder /app/.venv /app/.venv

# Copy the application source code
COPY --from=builder --chown=app:app /app /app



# Ensure our venv is first in PATH
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000/udp 8000/tcp