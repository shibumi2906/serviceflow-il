# syntax=docker/dockerfile:1.7

FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254 AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN python -m venv /opt/venv \
    && python -m venv /opt/buildenv \
    && /opt/buildenv/bin/python -m pip install \
       setuptools==84.0.0 wheel==0.48.0
COPY requirements.runtime.lock ./
RUN /opt/venv/bin/python -m pip install -r requirements.runtime.lock

COPY pyproject.toml README.md ./
COPY src/ src/
RUN /opt/buildenv/bin/python -m pip wheel \
       --no-deps --no-build-isolation --wheel-dir /wheels . \
    && /opt/venv/bin/python -m pip install --no-deps /wheels/*.whl


FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254 AS runtime

ARG GIT_SHA=unknown

LABEL org.opencontainers.image.title="ServiceFlow IL" \
      org.opencontainers.image.description="Phase 2 smoke-mode application image" \
      org.opencontainers.image.revision="${GIT_SHA}"

ENV APP_MODE=smoke \
    APP_ENV=production \
    APP_DEBUG=false \
    LOG_LEVEL=INFO \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --gid 10001 serviceflow \
    && useradd --uid 10001 --gid 10001 --no-create-home \
       --shell /usr/sbin/nologin serviceflow

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2).read()"]

CMD ["uvicorn", "serviceflow.main:app", "--host", "0.0.0.0", "--port", "8000"]
