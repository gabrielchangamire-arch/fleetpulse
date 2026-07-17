# Verified delivery roadmap

FleetPulse advances only after the current phase has a reproducible verification record. A phase report records the exact commands, results, environment, known limitations, and the Git commit under test.

Current status: Phases 0 through 6 are complete. Phase 7 is next.

| Phase | Scope | Exit evidence |
| --- | --- | --- |
| 0 | Isolated Git repository, architecture, ADRs, threat model, tooling, CI foundation | Repository contract, lint, type check, unit tests, source-repository isolation check |
| 1 | FastAPI ingestion, PostgreSQL migrations, psutil agent, durable idempotent batches, Compose vertical slice | Duplicate-batch tests, agent-to-database smoke test, persistence across restart |
| 2 | Transactional outbox, Redis Streams, scalable workers, fleet/incident/deployment state, retries and DLQ | Crash reclaim, poison-message DLQ, one-versus-many worker functional evidence |
| 3 | Nginx, local TLS, request correlation, DNS and socket diagnostics, caching, load balancing, network boundaries | Port exposure audit, TLS/DNS/HTTP checks, backend distribution, cache correctness |
| 4 | Prometheus, Grafana, Alertmanager, structured logs, SLO recording and burn-rate rules | Provisioned dashboards, synthetic alert, cross-service correlation trace |
| 5 | kind and k3d deployments, services, configuration, secret references, probes, limits, policies, rollout and rollback | Manifest validation, cluster smoke tests, failed rollout and rollback record |
| 6 | k6 performance matrix and evidence-based capacity model | Repeated cache on/off and one/four worker measurements with raw artifacts |
| 7 | Controlled failure/recovery drills, runbooks, and blameless postmortems | Detection/recovery measurements and exercised recovery steps |
| 8 | Optional read-only AI incident assistant and accuracy harness | Redaction, citation, abstention, golden-set accuracy, and no-execution-path tests |
| 9 | Complete CI hardening, image and manifest scanning, SBOMs, evidence index | Clean-clone CI-equivalent run and evidence-to-claim audit |

Targets and projections are not accepted as measurements. All performance comparisons use identical workloads and disclose machine and runtime conditions.
