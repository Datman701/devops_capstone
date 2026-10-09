# syntax=docker/dockerfile:1
#
# Backend image for the ClinicDesk API.
#
# Multi-stage: dependencies are compiled into a virtualenv in a builder stage,
# then only that virtualenv is copied into a slim runtime. Build tooling, pip
# caches and the compiler toolchain never reach the final image, which keeps it
# small and removes a large amount of attack surface (relevant to the Trivy
# scan in M6).

# ---------- Stage 1: build dependencies ----------
FROM python:3.12-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# `libpq5` is needed at runtime by psycopg; build-essential is only needed while
# compiling any source-only wheels.
RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install into a self-contained virtualenv so it can be copied across stages
# without dragging in the system site-packages.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# `python -m venv` seeds pip and setuptools from whatever the base image ships
# (70.3.0 at the time of writing), which Trivy reports as CVE-2025-47273, a path
# traversal in setuptools. Upgrade the build tooling before installing anything
# so the copy in the runtime stage is already patched.
RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install -r requirements.txt

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim-bookworm AS runtime

# curl is used by the Compose healthcheck; libpq5 by psycopg.
RUN apt-get update \
    && apt-get install --no-install-recommends -y libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_ENV=production

COPY --from=builder /opt/venv /opt/venv

# Strip pip, setuptools and pkg_resources from the runtime image.
#
# A running application never imports pip, but pip ships vendored copies of
# msgpack 1.1.2, urllib3 2.7.0 and setuptools 70.3.0 that Trivy reports as
# HIGH (GHSA-6v7p-g79w-8964, CVE-2026-97687, CVE-2025-47273). Those findings are
# not exploitable here, but removing the packages removes the findings honestly
# and shrinks the image. Nothing is compiled at run time, so pip is not needed.
RUN /opt/venv/bin/python -m pip uninstall -y pip setuptools wheel \
    && rm -rf \
        /opt/venv/lib/python3.12/site-packages/pip \
        /opt/venv/lib/python3.12/site-packages/pip-*.dist-info \
        /opt/venv/lib/python3.12/site-packages/setuptools \
        /opt/venv/lib/python3.12/site-packages/setuptools-*.dist-info \
        /opt/venv/lib/python3.12/site-packages/pkg_resources \
        /opt/venv/lib/python3.12/site-packages/_distutils_hack \
        /opt/venv/bin/pip /opt/venv/bin/pip3 /opt/venv/bin/pip3.12 \
        /opt/venv/bin/wheel

# Run as an unprivileged user. A fixed uid/gid keeps bind-mounted volumes
# predictable when the container is run with --user.
RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --create-home --home-dir /home/app app

WORKDIR /app

COPY --chown=app:app alembic.ini ./
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app app ./app

USER app

EXPOSE 8000

# Liveness only: deliberately does not touch the database, so a database outage
# cannot make Docker restart an otherwise healthy container. The Compose
# dependency check uses /ready for that.
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]