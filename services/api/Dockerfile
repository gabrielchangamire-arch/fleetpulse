FROM python:3.13-slim@sha256:bf44cdfcb76cd3b41e879bc058fc37ec5872002ccfde7fcb765e218cde0cd79c AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN groupadd --system fleetpulse && useradd --system --gid fleetpulse --home /app fleetpulse

COPY pyproject.toml README.md requirements.lock alembic.ini ./
COPY src ./src
COPY migrations ./migrations
RUN python -m pip install --require-hashes -r requirements.lock \
    && python -m pip install --no-deps .

USER fleetpulse
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn fleetpulse.api.app:create_app --factory --host 0.0.0.0 --port 8000 --no-access-log"]
