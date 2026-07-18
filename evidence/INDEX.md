# Evidence-to-claim index

These portfolio-safe bullets are generated from `evidence/claims.yaml`. Every bullet
links to committed evidence and states the boundary on what can be inferred.

## local_first_architecture

**Classification:** implemented

- Built FleetPulse, a local-first Linux reliability platform with psutil agents, FastAPI, PostgreSQL, Redis Streams, Nginx/TLS, Prometheus, Grafana, Alertmanager, Docker Compose, and reproducible kind/k3d deployments.

Evidence:

- [evidence/runs/20260717T080135Z-phase-1/summary.md](runs/20260717T080135Z-phase-1/summary.md)
- [evidence/runs/20260717T081555Z-phase-2/summary.md](runs/20260717T081555Z-phase-2/summary.md)
- [evidence/runs/20260717-phase-5/summary.md](runs/20260717-phase-5/summary.md)

Boundary: This describes implemented and locally exercised components; it makes no production-scale or cloud-availability claim.

## durable_failure_recovery

**Classification:** measured

- Implemented idempotent telemetry ingestion and a transactional PostgreSQL outbox feeding Redis Stream workers with reclaim, bounded retry, and dead-letter handling; a controlled Redis outage recovered one retained event with zero unpublished rows or dead letters.

Evidence:

- [evidence/runs/20260717T081555Z-phase-2/distributed-processing.txt](runs/20260717T081555Z-phase-2/distributed-processing.txt)
- [evidence/runs/20260717-phase-7/results.json](runs/20260717-phase-7/results.json)
- [evidence/runs/20260717-phase-7/summary.md](runs/20260717-phase-7/summary.md)

Boundary: The outage drill used one retained event on a single local machine and is not a production durability or availability measurement.

## cache_resource_comparison

**Classification:** measured

- Ran three-repetition k6 A/B tests at an imposed 100 requests/second; Redis caching produced a 99.95% hit rate and reduced measured p95 latency by 3.9%, API peak CPU by 30.4%, and PostgreSQL peak CPU by 64.5% for the tested one-record working set.

Evidence:

- [evidence/runs/20260717-phase-6/aggregate.json](runs/20260717-phase-6/aggregate.json)
- [evidence/runs/20260717-phase-6/summary.md](runs/20260717-phase-6/summary.md)
- [evidence/runs/20260717-phase-6/verification.txt](runs/20260717-phase-6/verification.txt)

Boundary: The request rate was imposed rather than a saturation result, and the one-record local working set cannot be generalized to production fleet cardinality.

## worker_scaling_comparison

**Classification:** measured

- Compared one versus four Redis Stream workers over three local repetitions: four workers increased median processing rate from 45.39 to 106.65 events/second and reduced a roughly 500-event queue drain from 11.037 to 4.698 seconds, while using 3.97 times aggregate memory.

Evidence:

- [evidence/runs/20260717-phase-6/aggregate.json](runs/20260717-phase-6/aggregate.json)
- [evidence/runs/20260717-phase-6/results.json](runs/20260717-phase-6/results.json)
- [evidence/runs/20260717-phase-6/summary.md](runs/20260717-phase-6/summary.md)

Boundary: These are Docker Desktop measurements for a fixed local workload and do not imply linear scaling beyond four workers.

## detection_and_recovery

**Classification:** measured

- Automated controlled reliability drills measured a five-trial p95 threshold-incident detection time of 5.224 seconds, API-outage alerting in 19.440 seconds, and Redis recovery in 2.965 seconds after repair.

Evidence:

- [evidence/runs/20260717-phase-7/results.json](runs/20260717-phase-7/results.json)
- [evidence/runs/20260717-phase-7/timeline.jsonl](runs/20260717-phase-7/timeline.jsonl)
- [evidence/runs/20260717-phase-7/summary.md](runs/20260717-phase-7/summary.md)

Boundary: Results use five-second local Prometheus intervals and controlled single-host failures; they are not a production rolling-window SLO.

## safe_incident_assistant

**Classification:** evaluated

- Built an optional read-only incident assistant with pre/post secret redaction, evidence-ID citations, fail-closed abstention, non-executing human approval receipts, and a five-case deterministic safety evaluation that passed all cases.

Evidence:

- [evidence/runs/20260717-phase-8/accuracy.json](runs/20260717-phase-8/accuracy.json)
- [evidence/runs/20260717-phase-8/container-smoke.json](runs/20260717-phase-8/container-smoke.json)
- [evidence/runs/20260717-phase-8/summary.md](runs/20260717-phase-8/summary.md)

Boundary: No live model call was measured; five deterministic cases validate the application safety contract, not general AI accuracy.

## immutable_supply_chain_gate

**Classification:** evaluated

- Hardened FleetPulse delivery with hash-locked Python dependencies, digest-pinned runtime and scanner images, commit-pinned GitHub Actions, strict manifest checks, image vulnerability policy, CycloneDX SBOMs, secret scanning, and a clean-clone CI-equivalent gate.

Evidence:

- [evidence/runs/20260717-phase-9/summary.md](runs/20260717-phase-9/summary.md)
- [evidence/runs/20260717-phase-9/verification.txt](runs/20260717-phase-9/verification.txt)
- [evidence/runs/20260717-phase-9/supply-chain-summary.json](runs/20260717-phase-9/supply-chain-summary.json)

Boundary: The local scan reported inherited unfixed base-image findings; a passing gate means no HIGH/CRITICAL finding had an available upstream fix, not that the images were vulnerability-free.
