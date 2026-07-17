# Phase 6 performance and capacity evidence

All numbers in the measured tables are local measurements from the recorded commit and
machine in `metadata.json`. They are not claims of production or cloud scale.

## Measured cache comparison

| Cache | Repetitions | Throughput (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | Hit rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| enabled | 1 | 10.31 | 3.74 | 4.47 | 4.65 | 0.0000 | 1.0000 |
| disabled | 1 | 10.00 | 4.82 | 6.00 | 6.61 | 0.0000 | 0.0000 |

## Measured worker comparison

| Workers | Repetitions | Accepted | Initial backlog | Drain (s) | Processing (events/s) | Ingest p95 (ms) | Errors |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | 31 | 31 | 1.678 | 18.47 | 12.63 | 0.0000 |
| 4 | 1 | 30 | 30 | 1.752 | 17.13 | 9.90 | 0.0000 |

## Evidence-based planning projections

The following values are projections, not measurements. They apply a 30% operating
headroom to the median measured queue-drain rate, then translate the result into daily
events and agents reporting once per minute. They assume this workload and local machine;
they do not assume linear scaling beyond a tested configuration.

| Tested workers | Projected planning rate (events/s) | Projected events/day | Projected 60s agents |
| ---: | ---: | ---: | ---: |
| 1 | 12.93 | 1117203 | 776 |
| 4 | 11.99 | 1035743 | 719 |

## Interpretation limits

- The constant-arrival workload proves behavior only at the tested rates; it is not a saturation test.
- Docker Desktop CPU and memory samples are local observations and include virtualization effects.
- Cache and worker axes are isolated experiments; the report does not infer a Cartesian interaction.
- Alert detection and incident recovery time are intentionally not measured here; Phase 7 owns those drills.
- Raw k6 samples, per-run summaries, resource samples, and queue samples are retained under `raw/`.
