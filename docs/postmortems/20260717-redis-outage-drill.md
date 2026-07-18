# Blameless postmortem: controlled Redis outage

## Status and impact

- **Date/environment:** 2026-07-17 local Docker Desktop Compose drill.
- **Status:** Recovered; no data loss and no unresolved drill state.
- **Impact:** Telemetry ingestion remained available, but outbox publication and asynchronous
  fleet processing paused while Redis was stopped.
- **Measured detection:** `FleetPulseOutboxFailure` fired in 4.647 seconds.
- **Measured recovery:** The exact event processed 2.965 seconds after Redis restart and 7.706
  seconds after failure injection.

These are local controlled measurements, not production recovery objectives.

## Timeline

- `00:05:46.504Z`: the drill runner completed the Redis stop operation.
- A unique telemetry batch was accepted and confirmed durable in PostgreSQL while Redis was
  unavailable.
- `00:05:51.244Z`: Prometheus exposed `FleetPulseOutboxFailure` as firing.
- Redis restart began after detection was recorded.
- The PostgreSQL outbox row published and its exact event ID appeared once in
  `processed_events`.
- `00:06:11.240Z`: the recent-failure alert had cleared and recovery evidence was finalized.

## What happened

Stopping Redis removed queue and cache connectivity. The FastAPI ingestion transaction did not
depend on Redis, so it committed the batch and outbox event to PostgreSQL. The relay reported
publication failures and exposed the alert timestamp. After Redis returned, the relay published
the retained event and a restarted worker processed it idempotently.

## Detection and response

The relay failure metric produced an actionable alert within one Prometheus scrape/evaluation
cycle. Recovery required only restoring Redis; no outbox replay command or database mutation was
needed. Validation was tied to the injected batch and outbox event rather than a global queue
count.

## Contributing conditions

- Redis is an asynchronous coordination dependency and an intentional single instance locally.
- The worker exits when Redis disappears and relies on the container restart policy to reconnect.
- The relay retries safely but logs a full traceback on each short poll, creating avoidable noise.

## What worked

- PostgreSQL ingestion and the transactional outbox preserved the accepted batch.
- Idempotent processing produced one processed-event row.
- The alert fired in 4.647 seconds and cleared after the bounded notification window.
- Recovery left zero unpublished matching rows and zero dead letters.
- Run-specific Compose isolation and cleanup prevented external impact.

## What did not work

- Worker reconnect behavior is delegated to container restarts instead of an explicit bounded
  backoff loop.
- Repeated relay tracebacks obscure the first failure and inflate logs during an outage.
- No direct Redis exporter exists; the current alert detects publication impact rather than the
  dependency state itself.

## Corrective actions

| Action | Evidence of completion | Priority | Status |
| --- | --- | --- | --- |
| Add bounded exponential backoff with jitter around worker Redis reconnects | Unit test plus repeated outage drill without restart loop | P1 | Open |
| Rate-limit repeated relay exception logging while preserving failure metrics | Log-volume assertion during outage drill | P1 | Open |
| Evaluate a private Redis exporter and dependency-down alert | Architecture decision and private-network manifest validation | P2 | Open |
| Repeat the drill after retry changes | New result tied to the implementation commit | P1 | Open |

The corrective actions improve retry behavior and signal quality; they do not assign individual
fault.
