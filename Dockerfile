# Single-service build for Railway: one image runs BOTH the Next.js frontend and
# the Django API in one container (see CLAUDE.md §3 — exactly two Railway
# services: this one + Postgres). scripts/start.sh launches both processes;
# Next proxies /api and /admin to Django on a private in-container port, so only
# Next's port is ever exposed publicly.

# ── Stage 1: build the Next.js frontend ──
FROM node:20-slim AS web-build
WORKDIR /app/web
COPY web/package.json web/package-lock.json* ./
RUN npm ci
COPY web/ ./
# Values baked into the client bundle at build time (safe to be public — see
# .env.example). API_INTERNAL_URL is a server-only default and can be overridden
# at runtime; it's not read during the build.
ARG NEXT_PUBLIC_SITE_URL
ENV NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL}
# next.config.mjs reads these to allow-list R2 as an image host for next/image.
# Standalone output freezes the resolved config at build time — Railway setting
# these as runtime Variables doesn't reach this isolated build stage on its own,
# they have to be threaded through explicitly, same as NEXT_PUBLIC_SITE_URL above.
ARG R2_ENDPOINT_URL
ARG R2_PUBLIC_BASE_URL
ENV R2_ENDPOINT_URL=${R2_ENDPOINT_URL}
ENV R2_PUBLIC_BASE_URL=${R2_PUBLIC_BASE_URL}
RUN npm run build

# ── Stage 2: install Python deps ──
FROM python:3.12-slim AS api-build
WORKDIR /app/api
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY api/requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 3: runtime — Python + Node together, nothing else ──
FROM python:3.12-slim AS runtime
# libicu72: the .NET runtime (needed below for the WiX toolchain) hard-crashes
# on startup without ICU globalization data — python:3.12-slim (Debian
# bookworm) doesn't ship it by default.
RUN apt-get update && apt-get install -y --no-install-recommends curl libpq5 libicu72 \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# ── WiX toolchain (auto-generated plugin installers — see api/installer/) ──
# Installed via Microsoft's official script rather than the apt repo, to stay
# portable across Debian base image versions. Pinned to WiX v5 — v7+ requires
# accepting a paid "Open Source Maintenance Fee" just to run, avoid it. HOME
# is fixed here (not the `bimhive` user's normal home, created below) because
# `wix extension add -g` caches under $HOME/.wix — this build step and the
# app's runtime user both need to resolve that same cache location, and ENV
# values apply to every USER in a Dockerfile, not just the one active when set.
ENV HOME=/opt/dotnet-home \
    DOTNET_ROOT=/usr/local/dotnet \
    PATH="/usr/local/dotnet:/usr/local/dotnet/tools:${PATH}" \
    DOTNET_NOLOGO=1 \
    DOTNET_CLI_TELEMETRY_OPTOUT=1
RUN mkdir -p "$HOME" /usr/local/dotnet/tools \
    && curl -fsSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh \
    && bash /tmp/dotnet-install.sh --channel 9.0 --install-dir /usr/local/dotnet \
    && rm /tmp/dotnet-install.sh \
    && dotnet tool install --tool-path /usr/local/dotnet/tools wix --version 5.0.2 \
    && wix extension add -g WixToolset.UI.wixext/5.0.2

WORKDIR /app
COPY --from=api-build /install /usr/local

COPY api/ api/
# Standalone output's root == web/ (Next was built from /app/web with no
# monorepo tracing root), so server.js lands at web/server.js; static assets
# and public/ are excluded from standalone by design and must be added back
# at the same paths Next expects them relative to that root.
COPY --from=web-build /app/web/.next/standalone web/
COPY --from=web-build /app/web/.next/static web/.next/static
COPY --from=web-build /app/web/public web/public
COPY scripts/start.sh scripts/start.sh
RUN chmod +x scripts/start.sh

RUN useradd --create-home --shell /bin/bash bimhive \
    && mkdir -p api/staticfiles api/media \
    && chown -R bimhive:bimhive /app "$HOME"
USER bimhive

ENV PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    API_INTERNAL_URL=http://127.0.0.1:8000 \
    HOSTNAME=0.0.0.0

EXPOSE 3000
CMD ["bash", "scripts/start.sh"]
