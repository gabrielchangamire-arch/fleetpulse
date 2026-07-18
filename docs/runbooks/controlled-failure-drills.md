# Controlled failure and recovery drills

## Purpose and boundaries

This runbook exercises API outage detection, threshold-incident detection, and durable Redis
outage recovery. The runner creates a unique Compose project, ephemeral credentials, and
temporary volumes. It never targets a shared Compose project, Kubernetes, or cloud resources.

## Prerequisites

- Docker Desktop or Docker Engine with Compose
- Python 3.11 or later and the bootstrapped `.venv`
- loopback ports 8443, 9090, and 9093 available

## Execute

Validate orchestration with one threshold trial:

```bash
make reliability-smoke
```

Run the Phase 7 evidence set with five threshold trials:

```bash
make reliability-drills
```

The runner generates local TLS, builds application images, and writes a timestamped directory
under `evidence/runs/`. Cleanup removes only the run-specific Compose project and volumes.

## Observe

During a manual reproduction, inspect named alerts and service state:

```bash
curl -s http://localhost:9090/api/v1/alerts
docker compose ps
docker compose logs --tail=100 api worker outbox-relay redis
```

Evidence meanings:

- `timeline.jsonl`: timestamped injections, alert transitions, and recovery completions;
- `results.json`: normalized detection/recovery durations and exact durability assertions;
- `compose-ps.txt` and `compose-logs.txt`: final runtime state and structured service logs;
- `final-alerts.json`: Prometheus alert state at evidence capture;
- `metadata.json`: Git SHA, host, Docker version, intervals, and isolation identifier.

## Abort and recover

The runner cleans up in a `finally` path. If the process itself is terminated, obtain the exact
project name from `metadata.json`, `timeline.jsonl`, or `docker compose ls`, validate that it
starts with `fleetpulse-p7-`, then run:

```bash
docker compose -p fleetpulse-p7-REPLACE_ME down --volumes
```

Never use an empty project name or remove broad Docker volumes. Preserve the failed evidence
directory and add a failure note before rerunning.

## Success criteria

- API target alert fires and clears, and TLS readiness returns.
- Every high-CPU batch produces a queryable incident and a firing alert below the target.
- The Redis-outage batch exists in PostgreSQL while Redis is stopped.
- After Redis starts, that exact outbox event is published and processed once.
- The final Compose state contains no unexpected restart loop or dead-lettered drill event.
