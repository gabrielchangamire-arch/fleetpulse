# FleetPulse — Linux Fleet Reliability and Incident Response Platform

FleetPulse is a local-first Linux fleet reliability and incident-response platform. It is designed to demonstrate production engineering practices through reproducible implementation and measured evidence, not unverified scale claims.

## Project status

Phases 0 through 8 are complete and verified. FleetPulse now has durable ingestion, Redis Stream workers, an Nginx/TLS edge with load balancing and cache-aside fleet reads, a provisioned Prometheus/Grafana/Alertmanager stack, reproducible kind/k3d deployments, repeated performance evidence, controlled failure/recovery drills, and an optional read-only incident assistant with deterministic safety evaluation. Runtime services are intentionally introduced one verified phase at a time; see [ROADMAP.md](ROADMAP.md).

## Verified today

- A Linux container agent collects bounded CPU, memory, disk, process, socket, and network telemetry with `psutil`.
- Batches survive agent restarts in a bounded SQLite spool and retry with capped exponential backoff and full jitter.
- FastAPI authenticates agents, propagates correlation IDs, and atomically commits telemetry, idempotency state, and an outbox event to PostgreSQL.
- Replaying a batch UUID creates no duplicate telemetry or outbox event.
- Compose and local Kubernetes run non-root application containers with bounded resources, health probes, private state services, and loopback-only ingress.

Evidence: [Phase 1 verification](evidence/runs/20260717T080135Z-phase-1/summary.md).

Phase 2 evidence: [distributed processing verification](evidence/runs/20260717T081555Z-phase-2/summary.md).

Phase 3 evidence: [TLS edge and cache verification](evidence/runs/20260717-phase-3/summary.md).

Phase 4 evidence: [SLO observability verification](evidence/runs/20260717-phase-4/summary.md).

Phase 5 evidence: [local Kubernetes verification](evidence/runs/20260717-phase-5/summary.md).

Phase 6 evidence: [performance and capacity verification](evidence/runs/20260717-phase-6/summary.md).

Phase 7 evidence: [failure detection and recovery verification](evidence/runs/20260717-phase-7/summary.md).

Phase 8 evidence: [read-only assistant safety verification](evidence/runs/20260717-phase-8/summary.md).

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

Nginx is the only application ingress and terminates local TLS. PostgreSQL and Redis have no host ports; Prometheus, Grafana, and Alertmanager bind only to loopback in Compose and remain ClusterIP in Kubernetes.

For local Kubernetes, set non-production runtime credentials and use either supported runtime:

```bash
make k8s-validate
make kind-up
# or: make k3d-up
```

See the [local Kubernetes runbook](docs/runbooks/local-kubernetes.md) for startup, inspection,
rollback, and cleanup. Phase 7 adds controlled failure and recovery drills.

To validate or repeat the local performance suite, install k6 and run the smoke profile before
the three-repetition matrix:

```bash
make performance-smoke
make performance-matrix
```

See the [performance testing runbook](docs/runbooks/performance-testing.md). Workload rates are
inputs, not capacity claims; measured results and projections are labeled separately.

Controlled local failures can be reproduced with `make reliability-smoke` and
`make reliability-drills`; see the
[failure drill runbook](docs/runbooks/controlled-failure-drills.md).

The incident assistant is disabled by default and requires no model or network for its golden-set
evaluation. Run `make assistant-eval` or start only the offline optional service with
`make assistant-up`; see the [assistant runbook](docs/runbooks/assistant.md). Human approval records
a decision but cannot execute a remediation.

For the complete local CI-equivalent security gate, run `make final-gate`. `make clean-clone`
repeats the gate and Compose smoke tests from committed files only. See the
[supply-chain runbook](docs/runbooks/supply-chain.md) and the
[evidence-to-claim index](evidence/INDEX.md).

## Architecture

The system design and network boundaries are documented in [docs/architecture/system.md](docs/architecture/system.md). Security assumptions are in [docs/security/threat-model.md](docs/security/threat-model.md), and outstanding engineering risks are tracked in the [risk register](docs/risk-register.md).
