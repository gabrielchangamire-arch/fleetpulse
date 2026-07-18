# FleetPulse service-level objectives

These are engineering targets, not measured production claims. FleetPulse is a local-first demonstration system; measurements are preserved under `evidence/` and labeled with their environment.

## Availability

- **SLI:** proportion of API requests that do not return a 5xx response.
- **SLO:** 99.9% over a rolling 30-day window.
- **Error budget:** 43.2 minutes per 30 days.
- **Initial alert:** five-minute availability below 99.9% for two minutes. This intentionally simple rule is a local validation rule; multi-window burn-rate alerts are a later hardening step.

## Ingestion latency

- **SLI:** server-side duration from receipt of `POST /v1/telemetry/batches` through the durable PostgreSQL commit.
- **SLO:** p99 below 500 ms over a rolling 30-day window.
- **Exclusion:** agent collection and network transit are measured separately and are not hidden inside this server-side SLI.

## Alert detection

- **SLI:** elapsed time from a threshold-crossing telemetry observation to the incident becoming queryable and its alert entering the firing state.
- **SLO:** p95 below 60 seconds over controlled drills.
- **Measurement:** Phase 7 drills preserve acceptance time, incident visibility, Prometheus firing time, and environment metadata. Five controlled threshold trials provide a preliminary local nearest-rank p95. This does not establish a production rolling-window SLO.

## Metric interpretation

- `fleetpulse_http_requests_total` and `fleetpulse_http_request_duration_seconds` support the availability and ingestion SLIs.
- `fleetpulse_queue_pending` tracks Redis Stream pending plus lag for the worker group.
- `fleetpulse_cache_requests_total` supports cache hit-rate comparisons.
- `fleetpulse_worker_events_total` and `fleetpulse_outbox_published_total` expose the asynchronous processing path.
- `fleetpulse_incident_last_seen_timestamp_seconds` and
  `fleetpulse_outbox_last_failure_timestamp_seconds` drive bounded recent-event drill alerts.

Labels are deliberately bounded. Agent IDs, batch IDs, request IDs, paths supplied by callers, and exception text are never Prometheus labels.
