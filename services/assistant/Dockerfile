FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN groupadd --system fleetpulse && useradd --system --gid fleetpulse --home /app fleetpulse

COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install .

USER fleetpulse
EXPOSE 8081
CMD ["uvicorn", "fleetpulse.assistant.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8081", "--no-access-log"]
