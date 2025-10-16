# -------- Build stage --------
FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim AS builder
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

# Add contrib and non-free-firmware to sources.list (required for mscorefonts)
RUN sed -i 's/main/main contrib non-free-firmware/g' /etc/apt/sources.list

# Pre-accept Microsoft fonts EULA
RUN echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections

# Install LibreOffice + only available, verified font packages in trixie
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Core
    libreoffice-core libreoffice-writer libreoffice-calc libreoffice-impress \
    fontconfig \
    \
    # Universal coverage (Google Noto = best for global support)
    fonts-noto-core fonts-noto-ui-core fonts-noto-cjk fonts-noto-color-emoji fonts-noto-mono fonts-noto-extra \
    \
    # Common fallbacks
    fonts-dejavu fonts-liberation fonts-freefont-ttf fonts-liberation2 fonts-cantarell fonts-droid-fallback \
    \
    # Microsoft core fonts (Arial, Times, etc.)
    ttf-mscorefonts-installer \
    \
    # CJK
    fonts-wqy-zenhei fonts-wqy-microhei fonts-ipafont-gothic fonts-ipafont-mincho \
    \
    # Arabic, Persian, Hebrew
    fonts-hosny-amiri fonts-hosny-thabit fonts-farsiweb fonts-lklug-sinhala \
    \
    # Korean
    fonts-nanum \
    \
    # Thai
    fonts-thai-tlwg \
    \
    # Symbols, emoji, math
    fonts-symbola fonts-font-awesome fonts-material-design-icons-iconfont fonts-stix fonts-lmodern \
    \
    # Myanmar, Tibetan, etc. (if available)
    fonts-sil-padauk \
    \
    && fc-cache -fv \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy virtual environment and project
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

# Expose ports
EXPOSE 8000/tcp 8000/udp

# Verify
RUN libreoffice --version && fc-list | wc -l && fc-list : family | sort -u | head -n 30