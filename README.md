# FleetPulse — Linux Fleet Reliability and Incident Response Platform

FleetPulse is a local-first Linux fleet reliability and incident-response platform. It is designed to demonstrate production engineering practices through reproducible implementation and measured evidence, not unverified scale claims.

## Try the read-only incident demo

The assistant runs independently of the fleet infrastructure. Python 3.13 is the default for
reproducible local checks (Python 3.12+ is supported by the workflow):

```bash
make bootstrap
make verify
.venv/bin/uvicorn fleetpulse.assistant.app:create_app --factory --host 127.0.0.1 --port 8765
```

Open <http://127.0.0.1:8765>, select a synthetic development incident, inspect its evidence and
request analysis. The page labels **offline** versus **live** mode and puts claims next to exact
source excerpts. Offline mode echoes records; it does not diagnose incidents. No route can execute
remediation. To enable live mode, configure the backend environment as described in the
[evaluation guide](evaluations/incidents-v1/README.md), then set
`FLEETPULSE_ASSISTANT_PROVIDER=openai` before starting the server. Never put keys in browser code.

Architecture: bounded request → redaction → existing provider adapter → structured validation →
redaction → citation/excerpt validation → read-only response. Summaries are derived from cited
claims. Literal excerpt matches establish traceability, **not factual correctness**; semantic
support is graded separately. The versioned evaluation has 32 synthetic cases and a fixed
16/16 development/held-out split, plus opt-in live reporting and human grading of saved outputs.

See [reproducible current evidence](evidence/runs/20261007-assistant-v1/summary.md),
[grading and limitations](evaluations/incidents-v1/README.md), and the
[interview walkthrough](docs/architecture/assistant-walkthrough.md). Historical phase results below
are preserved; they are not claims that the new branch reran infrastructure or live-model tests.

## Project status

Phases 0 through 9 are complete and verified. FleetPulse has durable ingestion, Redis Stream workers, an Nginx/TLS edge with load balancing and cache-aside fleet reads, a provisioned Prometheus/Grafana/Alertmanager stack, reproducible kind/k3d deployments, repeated performance evidence, controlled failure/recovery drills, an optional read-only incident assistant with deterministic safety evaluation, and immutable CI/supply-chain gates. See [ROADMAP.md](ROADMAP.md).

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

Phase 9 evidence: [final CI and supply-chain verification](evidence/runs/20260717-phase-9/summary.md).

## Non-negotiable boundaries

- This repository is independent from every Nemo or Oracle VM project.
- Docker Compose and a local kind or k3d cluster are the primary environments.
- Cloud deployment is optional and may never become a local-development prerequisite.
- PostgreSQL, Redis, Prometheus, and Grafana must not be publicly exposed.
- AI is optional, read-only, and unable to execute remediation.
- Results are labeled as measured, projected, or target values.
- Raw evidence supporting performance and reliability claims is preserved under `evidence/`.

## Developer workflow

The repository checks require Python 3.12 or later:

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
