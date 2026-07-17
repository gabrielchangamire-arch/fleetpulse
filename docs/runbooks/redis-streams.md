# Redis Streams worker runbook

## Inspect queue state

Redis is private and has no host port. Run diagnostics through the container:

```bash
docker compose exec redis redis-cli XINFO GROUPS fleetpulse:telemetry
docker compose exec redis redis-cli XPENDING fleetpulse:telemetry fleetpulse-workers
docker compose exec redis redis-cli XLEN fleetpulse:telemetry:dlq
```

## Scale workers

```bash
docker compose up -d --scale worker=3 worker --wait
```

Each replica receives a container-derived consumer name. Redis consumer groups divide new messages while `XAUTOCLAIM` recovers messages abandoned longer than the configured idle period.

## Dead-letter behavior

Messages that fail schema or supported-event validation remain pending for bounded retries. At the configured attempt limit, the worker copies the original fields and error type to `fleetpulse:telemetry:dlq`, records the failure in PostgreSQL `dead_letters`, and acknowledges the source message.

Never delete a DLQ entry before recording its disposition. Requeueing must create a new event ID or explicitly verify that the original event did not partially commit.

## Redis outage

The API continues committing telemetry and outbox rows while Redis is unavailable. The relay retries publication after Redis recovers. Monitor unpublished outbox age before declaring queue recovery complete.

