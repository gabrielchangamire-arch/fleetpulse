FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN groupadd --system fleetpulse && useradd --system --gid fleetpulse --home /app fleetpulse

COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY migrations ./migrations
RUN python -m pip install .

USER fleetpulse
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn fleetpulse.api.app:create_app --factory --host 0.0.0.0 --port 8000 --no-access-log"]
