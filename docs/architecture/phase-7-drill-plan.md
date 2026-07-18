# Phase 7 controlled failure and recovery plan

Phase 7 validates detection and recovery on an isolated Docker Compose project. It does not
inject failures into Kubernetes, cloud infrastructure, or any repository outside FleetPulse.

## Scenarios

| Drill | Injection | Detection signal | Recovery signal |
| --- | --- | --- | --- |
| API outage | Stop the API container while Nginx and Prometheus remain active | `FleetPulseAPITargetDown` enters `firing` | TLS readiness returns HTTP 200 and the alert clears |
| Threshold incident | Submit five unique high-CPU telemetry batches | Incident becomes queryable and `FleetPulseIncidentDetected` fires | Alert clears after its bounded recent-event window |
| Redis outage | Stop Redis, then durably ingest a telemetry batch | Relay failure metric causes `FleetPulseOutboxFailure` | Redis restarts, the outbox row publishes, and the exact event is recorded as processed |

## Measurement definitions

- **Detection time:** monotonic elapsed seconds from completed failure injection or accepted
  threshold telemetry to the named Prometheus alert entering `firing`.
- **Incident visibility:** elapsed seconds from accepted threshold telemetry to the matching
  incident becoming queryable through the API.
- **Repair recovery:** elapsed seconds from the recovery command to restored readiness or exact
  event processing.
- **Total impact:** elapsed seconds from failure injection to restored service or processing.

Wall-clock UTC timestamps provide an audit trail; monotonic clocks provide duration values.

## Acceptance criteria

- Every drill runs in a unique Compose project with ephemeral credentials and temporary volumes.
- The API outage is detected, restored, and its alert clears.
- Five threshold incidents are both queryable and alerted; the nearest-rank p95 end-to-end
  detection time is below the 60-second target.
- Telemetry accepted during the Redis outage remains in PostgreSQL, publishes after Redis
  returns, and is processed exactly once.
- Raw event timelines, Prometheus alert snapshots, service state, logs, metadata, results,
  runbooks, and a blameless postmortem are preserved.
- Detection targets are not presented as production SLO attainment.

## Safety controls

- Only containers labeled with the run-specific Compose project are controlled.
- The runner never deletes shared volumes; it deletes only the unique drill project's volumes.
- PostgreSQL, Redis, Prometheus, and Alertmanager retain their existing loopback/private network
  boundaries.
- Cleanup executes after success or failure.
