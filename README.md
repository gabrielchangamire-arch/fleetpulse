# FleetPulse

FleetPulse is a local-first Linux fleet reliability and incident-response platform. It is designed to demonstrate production engineering practices through reproducible implementation and measured evidence, not unverified scale claims.

## Project status

Phase 0 (repository isolation and engineering foundations) is in progress. Runtime services are intentionally introduced one verified phase at a time; see [ROADMAP.md](ROADMAP.md).

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

Later phases will add `make compose-up`, `make kind-up`, `make k3d-up`, load-test, and recovery-drill targets.

## Architecture

The system design and network boundaries are documented in [docs/architecture/system.md](docs/architecture/system.md). Security assumptions are in [docs/security/threat-model.md](docs/security/threat-model.md).

