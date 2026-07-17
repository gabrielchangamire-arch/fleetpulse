# Phase 6 performance and capacity evidence

All numbers in the measured tables are local measurements from the recorded commit and
machine in `metadata.json`. They are not claims of production or cloud scale.

## Measured cache comparison

| Cache | Repetitions | Throughput (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | Hit rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| enabled | 3 | 100.00 | 2.94 | 4.04 | 4.50 | 0.0000 | 0.9995 |
| disabled | 3 | 100.03 | 2.73 | 4.20 | 4.70 | 0.0000 | 0.0000 |

## Measured worker comparison

| Workers | Repetitions | Accepted | Initial backlog | Drain (s) | Processing (events/s) | Ingest p95 (ms) | Errors |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 3 | 501 | 501 | 11.037 | 45.39 | 6.22 | 0.0000 |
| 4 | 3 | 500 | 500 | 4.698 | 106.65 | 6.16 | 0.0000 |

## Measured resource envelope

CPU is the maximum aggregate Docker CPU percentage for all containers of the service. Memory is the maximum aggregate resident allocation reported by Docker.

| Experiment | Configuration | API max CPU | API max memory (MiB) | Worker max CPU | Worker max memory (MiB) |
| --- | --- | ---: | ---: | ---: | ---: |
| cache | enabled | 20.06% | 130.75 | 0.00% | 0.00 |
| cache | disabled | 28.84% | 130.98 | 0.00% | 0.00 |
| workers | 1 | 40.45% | 260.77 | 77.83% | 118.93 |
| workers | 4 | 38.04% | 261.38 | 84.41% | 471.90 |

## Evidence-based planning projections

The following values are projections, not measurements. They apply a 30% operating
headroom to the median measured queue-drain rate, then translate the result into daily
events and agents reporting once per minute. They assume this workload and local machine;
they do not assume linear scaling beyond a tested configuration.

| Tested workers | Projected planning rate (events/s) | Projected events/day | Projected 60s agents |
| ---: | ---: | ---: | ---: |
| 1 | 31.77 | 2745256 | 1906 |
| 4 | 74.65 | 6449930 | 4479 |

## Interpretation limits

- The constant-arrival workload proves behavior only at the tested rates; it is not a saturation test.
- Docker Desktop CPU and memory samples are local observations and include virtualization effects.
- Cache and worker axes are isolated experiments; the report does not infer a Cartesian interaction.
- Alert detection and incident recovery time are intentionally not measured here; Phase 7 owns those drills.
- Raw k6 samples, per-run summaries, resource samples, and queue samples are retained under `raw/`.
