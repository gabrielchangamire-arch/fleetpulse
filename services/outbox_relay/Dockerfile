FROM python:3.13-slim@sha256:bf44cdfcb76cd3b41e879bc058fc37ec5872002ccfde7fcb765e218cde0cd79c AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN groupadd --system fleetpulse && useradd --system --gid fleetpulse --home /app fleetpulse
COPY pyproject.toml README.md requirements.lock ./
COPY src ./src
# Package installers are build-only; the runtime cannot install dependencies.
RUN python -m pip install --require-hashes -r requirements.lock \
    && python -m pip install --no-deps . \
    && python -m pip uninstall --yes pip \
    && rm -rf /usr/local/lib/python3.13/ensurepip
USER fleetpulse
CMD ["python", "-m", "fleetpulse.worker.relay"]
