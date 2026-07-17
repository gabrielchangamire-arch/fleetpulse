# Phase 6 verification summary

Phase 6 is complete. The committed k6 harness ran two controlled local A/B experiments with
three repetitions per configuration and retained the raw artifacts needed to audit every
claim. The Git commit under test was `2e59244f72f16c403e17a434268bc5e149eb892d`.
The metadata marks the worktree dirty because earlier untracked smoke evidence and the active
output directory existed during recording; the benchmark implementation itself had already
been committed at that SHA.

## Exit criteria

- Cache enabled and disabled were tested with the same constant arrival rate, two API
  replicas, one seeded fleet-state record, and no active workers.
- One and four workers were tested against independently created queues of approximately 500
  accepted telemetry batches. Consumption was paused until PostgreSQL outbox publication was
  complete, so initial queue depth matched the accepted-event count.
- All 12 k6 trials completed with zero HTTP errors.
- Every worker trial ended with accepted events equal to processed events and Redis pending
  plus lag equal to zero.
- Throughput, p50/p95/p99 latency, errors, CPU, memory, queue backlog, and cache hit rate are
  present in per-run and aggregate evidence.
- Detection and recovery time are not inferred from load results; they remain Phase 7 exit
  evidence.

## Measured local results

The following are medians across three repetitions on the host described in `metadata.json`.
They are local measurements, not production capacity claims.

| Comparison | Measured outcome |
| --- | --- |
| Cache enabled | 100.00 req/s, p50 2.94 ms, p95 4.04 ms, p99 4.50 ms, 0 errors, 99.95% hit rate |
| Cache disabled | 100.03 req/s, p50 2.73 ms, p95 4.20 ms, p99 4.70 ms, 0 errors |
| One worker | 501-event median backlog, 11.037 s drain, 45.39 events/s, 118.93 MiB max worker memory |
| Four workers | 500-event median backlog, 4.698 s drain, 106.65 events/s, 471.90 MiB max worker memory |

At this tested rate and one-record working set, caching reduced p95 by 3.9%, aggregate API
peak CPU by 30.4%, and PostgreSQL peak CPU by 64.5%. Because throughput was an imposed arrival
rate, the result demonstrates lower resource demand and slightly lower tail latency at 100
req/s; it does not establish maximum read capacity.

Four workers produced 2.35 times the one-worker processing rate and reduced queue-drain time by
57.4%. Aggregate worker memory was 3.97 times the one-worker measurement. The result supports
independent worker scaling for this workload while showing its memory cost; it does not assume
linear scaling beyond the tested four-worker configuration.

## Projected planning values

The capacity plan applies 30% operating headroom to the measured median queue-drain rates.
These are projections, not measurements:

- one worker: 31.77 events/s, 2,745,256 events/day, or 1,906 agents at a 60-second interval;
- four workers: 74.65 events/s, 6,449,930 events/day, or 4,479 agents at a 60-second interval.

Those translations assume the same payload, local machine, database behavior, and reporting
interval. They are planning examples rather than validated fleet sizes.

## Evidence map and limitations

- `capacity-plan.md` contains the aggregate measured tables, resource envelope, formulas, and
  interpretation limits.
- `aggregate.json` and `results.json` contain machine-readable medians and individual results.
- `raw/*/k6-samples.jsonl.gz` and `raw/*/k6-summary.json` preserve request-level and summary
  metrics.
- `raw/*/resources.jsonl` preserves Docker CPU and memory samples.
- `raw/workers-*/queue.jsonl` preserves pending, lag, backlog, and processed counts during
  drain.
- `verification.txt` records quality gates and artifact completeness.

Docker Desktop virtualization, a one-record cache working set, and the absence of a saturation
curve limit generalization. The risk register keeps saturation characterization open. Earlier
failed smoke attempts are retained separately with their causes and fixes, rather than folded
into the successful measurement population.
