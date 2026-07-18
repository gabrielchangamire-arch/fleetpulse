# Phase 7 failure detection and recovery evidence

Phase 7 is complete. The committed drill harness injected API and Redis outages and five unique
high-CPU threshold events in the isolated Compose project recorded by `metadata.json`. The
implementation commit under test was `4dd717dfc39b8dd795ab985d2ecf52cce81461cd`.
The worktree-dirty metadata reflects untracked smoke/evidence output present during recording;
the drill implementation itself had already been committed at that SHA.

## Measured local results

| Drill | Detection | Recovery | Integrity result |
| --- | ---: | ---: | --- |
| API outage | Alert firing in 19.440 s | Readiness restored 6.346 s after repair; 25.788 s total impact | Target alert cleared |
| Threshold incidents | Five-trial nearest-rank p95 end-to-end 5.224 s | Recent-event alerts cleared between trials | Five distinct queryable incidents |
| Redis outage | Relay-impact alert firing in 4.647 s | Exact event processed 2.965 s after repair; 7.706 s total impact | 1 durable row, 1 processed event, 0 unpublished, 0 dead letters |

The preliminary five-trial threshold p95 was below the 60-second local detection target. This
does not demonstrate a production rolling-window SLO or predict cloud behavior.

## Acceptance criteria

- The API alert fired, TLS readiness recovered, and the alert cleared.
- All five threshold batches produced queryable incidents and firing Prometheus alerts.
- Alert windows cleared between threshold trials, preventing overlapping measurements.
- Telemetry remained durable during the Redis outage.
- The exact retained outbox event published and processed once after Redis returned.
- No matching unpublished state or dead letters remained.
- Ephemeral credentials were excluded from evidence, and the run-specific project and volumes
  were removed.

## Evidence map

- `results.json`: normalized detection, recovery, percentile, and integrity results.
- `timeline.jsonl`: UTC injections, Prometheus alert payloads, transitions, and recoveries.
- `metadata.json`: Git SHA, Compose isolation ID, Docker/host details, and scrape intervals.
- `compose-ps.txt`: final service state before cleanup.
- `compose-logs.txt`: structured service logs, including the intentionally induced Redis errors.
- `final-alerts.json`: final Prometheus state.
- `verification.txt`: repository, rule, smoke, CI, and artifact checks.

## Findings and limitations

The transactional outbox behaved as designed and required no manual replay. The drill also
showed that workers currently reconnect through container restart behavior and that the relay
emits repeated tracebacks during an outage. Those observations are retained as open corrective
actions in the blameless Redis outage postmortem rather than hidden from the result.

Measurements use a single local machine, five-second Prometheus intervals, one API replica, one
worker, and a controlled single-event Redis backlog. They establish reproducible behavior for
this environment only.
