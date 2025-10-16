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

# Pre-accept Microsoft fonts EULA
RUN echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections

# Install LibreOffice + massive font coverage
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Core apps
    libreoffice-core libreoffice-writer libreoffice-calc libreoffice-impress \
    \
    # Fontconfig & utils
    fontconfig fonts-noto-core fonts-noto-ui-core fonts-noto-color-emoji \
    \
    # Microsoft fonts (Arial, Times, etc.)
    ttf-mscorefonts-installer \
    \
    # Latin & extended
    fonts-dejavu fonts-liberation fonts-freefont-ttf fonts-liberation2 \
    fonts-cantarell fonts-ubuntu fonts-droid-fallback \
    \
    # CJK (Chinese, Japanese, Korean)
    fonts-noto-cjk fonts-wqy-zenhei fonts-wqy-microhei fonts-ipafont-gothic fonts-ipafont-mincho \
    fonts-hanazono \
    \
    # Arabic, Hebrew, Persian
    fonts-hosny-amiri fonts-khmeros-core fonts-lklug-sinhala \
    fonts-nanum fonts-lohit-devanagari fonts-lohit-bengali fonts-lohit-gujarati \
    fonts-lohit-kannada fonts-lohit-malayalam fonts-lohit-oriya fonts-lohit-punjabi \
    fonts-lohit-tamil fonts-lohit-telugu fonts-samyak-devanagari fonts-samyak-tamil \
    fonts-guru fonts-gubbi fonts-telu fonts-telu-extra fonts-kalapi \
    fonts-arabeyes fonts-hosny-thabit fonts-farsiweb \
    \
    # Thai, Vietnamese, etc.
    fonts-thai-tlwg fonts-sil-padauk fonts-sil-nuosu \
    \
    # Emoji & symbols
    fonts-symbola fonts-font-awesome fonts-material-design-icons-iconfont \
    \
    # Math & special
    fonts-stix fonts-asana-math fonts-lmodern \
    \
    # Fallback & coverage
    fonts-noto-mono fonts-noto-extra \
    && fc-cache -fv \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy virtual environment and project
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

# Expose ports
EXPOSE 8000/tcp 8000/udp

# Verify
RUN libreoffice --version && fc-list | wc -l && fc-list : family | sort -u | head -n 30