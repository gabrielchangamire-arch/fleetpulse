# FleetPulse — Linux Fleet Reliability and Incident Response Platform

FleetPulse is a local-first Linux fleet reliability and incident-response platform. It is designed to demonstrate production engineering practices through reproducible implementation and measured evidence, not unverified scale claims.

## Project status

Phases 0 through 2 are complete and verified. FleetPulse now has durable agent ingestion plus Redis Stream relay/worker processing, fleet summaries, incident deduplication, deployment records, reclaim, bounded retries, and dead-letter handling. Runtime services are intentionally introduced one verified phase at a time; see [ROADMAP.md](ROADMAP.md).

## Verified today

- A Linux container agent collects bounded CPU, memory, disk, process, socket, and network telemetry with `psutil`.
- Batches survive agent restarts in a bounded SQLite spool and retry with capped exponential backoff and full jitter.
- FastAPI authenticates agents, propagates correlation IDs, and atomically commits telemetry, idempotency state, and an outbox event to PostgreSQL.
- Replaying a batch UUID creates no duplicate telemetry or outbox event.
- Compose starts healthy non-root agent/API containers and private PostgreSQL storage; only the API is bound to loopback during this phase.

Evidence: [Phase 1 verification](evidence/runs/20260717T080135Z-phase-1/summary.md).

Phase 2 evidence: [distributed processing verification](evidence/runs/20260717T081555Z-phase-2/summary.md).

## Non-negotiable boundaries

- This repository is independent from every Nemo or Oracle VM project.
- Docker Compose and a local kind or k3d cluster are the primary environments.
- Cloud deployment is optional and may never become a local-development prerequisite.
- PostgreSQL, Redis, Prometheus, and Grafana must not be publicly exposed.
- AI is optional, read-only, and unable to execute remediation.
- Results are labeled as measured, projected, or target values.
- Raw evidence supporting performance and reliability claims is preserved under `evidence/`.

## Planned developer workflow

The initial repository checks can be run with Python 3.11 or later:

```bash
make bootstrap
make verify
```

To start the Phase 1 Compose slice, copy `.env.example` to the ignored `.env`, replace both placeholders with random local values, and run:

```bash
make compose-up
make phase1-smoke
```

The API is temporarily bound to `127.0.0.1:8000` for Phase 1 verification. PostgreSQL has no host port. Nginx becomes the only application ingress in Phase 3. Later phases add `make kind-up`, `make k3d-up`, load-test, and recovery-drill targets.

## Architecture

The system design and network boundaries are documented in [docs/architecture/system.md](docs/architecture/system.md). Security assumptions are in [docs/security/threat-model.md](docs/security/threat-model.md).
