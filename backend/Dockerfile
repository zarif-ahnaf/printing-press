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
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

# Enable contrib and non-free-firmware in the new deb822 sources format
RUN sed -i 's/Components: main/Components: main contrib non-free-firmware/' /etc/apt/sources.list.d/debian.sources

# Pre-accept Microsoft fonts EULA
RUN echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections

# Now install packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-core libreoffice-writer libreoffice-calc libreoffice-impress \
    fontconfig \
    fonts-noto-core fonts-noto-ui-core fonts-noto-cjk fonts-noto-color-emoji fonts-noto-mono fonts-noto-extra \
    fonts-dejavu fonts-liberation fonts-freefont-ttf fonts-liberation2 fonts-cantarell fonts-droid-fallback \
    ttf-mscorefonts-installer \
    fonts-wqy-zenhei fonts-wqy-microhei fonts-ipafont-gothic fonts-ipafont-mincho \
    fonts-hosny-amiri fonts-hosny-thabit fonts-farsiweb fonts-lklug-sinhala \
    fonts-nanum \
    fonts-thai-tlwg \
    fonts-symbola fonts-font-awesome fonts-material-design-icons-iconfont fonts-stix fonts-lmodern \
    fonts-sil-padauk \
    && fc-cache -fv \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
# Copy virtual environment and project
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

# Expose ports
EXPOSE 8000/tcp 8000/udp

# Verify
RUN libreoffice --version && fc-list | wc -l && fc-list : family | sort -u | head -n 30

ENV PATH="/app/.venv/bin:$PATH"
