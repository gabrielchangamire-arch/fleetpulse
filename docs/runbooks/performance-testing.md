# Performance testing and capacity evidence

This runbook produces the Phase 6 cache and worker comparisons on a local Docker
Compose environment. It does not touch Kubernetes, cloud resources, or any repository
outside FleetPulse.

## Experimental controls

The suite uses a constant-arrival-rate workload and changes one variable at a time:

1. Fleet-state reads compare Redis cache enabled with disabled. The API remains at two
   replicas, one seeded fleet record is used, and workers are stopped during the read test.
2. Telemetry ingestion creates an identical Redis Stream backlog, pauses consumption, and
   compares the time taken by one and four workers to drain it. The API remains at two replicas.

The full suite runs three repetitions per configuration. Each repetition resets only the
FleetPulse PostgreSQL tables and Redis database, uses unique batch UUIDs, and retains:

- raw k6 time-series samples and k6 summaries;
- container CPU and memory samples by Compose service;
- Redis pending/lag samples during queue drain;
- workload, host, Docker, Git commit, and tool metadata;
- individual results, cross-run medians, and the capacity report.

## Run

Prerequisites are Docker Desktop (or Docker Engine), k6, Python 3.11 or newer, and the
bootstrapped project virtual environment.

```bash
make bootstrap
make performance-smoke
make performance-matrix
```

The smoke profile uses one short repetition to validate orchestration. The full profile uses
100 fleet reads per second for 20 seconds and 50 telemetry batches per second for 10 seconds.
Those rates are workload inputs, not capacity claims.

The runner creates a timestamped directory under `evidence/runs/`. It generates ephemeral
credentials in memory and never writes them to evidence. It shuts Compose down on success or
failure unless `--keep-running` is explicitly passed.

## Interpreting results

Use `capacity-plan.md` for measured medians and separately labeled projections. Consult each
`raw/*/result.json` before making a claim. A valid comparison requires:

- the expected repetition count for every configuration;
- zero or explicitly disclosed request errors;
- matching accepted-event and initial-backlog counts in worker tests;
- a drained queue with every accepted event recorded as processed;
- resource samples for the API, Nginx, PostgreSQL, Redis, and active workers.

The 30% headroom calculation is a planning projection derived from measured local drain rate.
It is not a production limit and must not be described as tested scale. Detection and recovery
times belong to Phase 7 and are not inferred from Phase 6.

## Failure handling

If a run fails, preserve its directory for diagnosis. Inspect `k6-console.txt`,
`resource-sampler-errors.txt`, container logs, and the last queue sample. Then shut down with:

```bash
docker compose down
```

Do not combine partial repetitions with a later run. Start a fresh timestamped evidence set so
the Git commit, environment, and comparison population remain unambiguous.
