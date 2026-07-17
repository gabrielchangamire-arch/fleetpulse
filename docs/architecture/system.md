# System architecture

## Components

1. Linux agents collect CPU, memory, disk, process, socket, and network counters with `psutil`. They batch samples into a bounded local spool and use stable batch identifiers.
2. Nginx terminates local TLS, constrains requests, attaches correlation IDs, and load-balances FastAPI replicas.
3. FastAPI validates agent identity and payloads, atomically persists a telemetry batch, its idempotency record, and an outbox entry in PostgreSQL, then acknowledges the request.
4. An outbox relay publishes durable work to Redis Streams. Worker consumer groups scale independently and recover abandoned messages.
5. Workers update fleet summaries, evaluate incident conditions, and manage retry and dead-letter state through idempotent database transitions.
6. Redis also provides bounded cache-aside entries and narrow distributed coordination with ownership tokens and expirations.
7. Prometheus scrapes bounded-cardinality metrics. Grafana visualizes service and fleet health. Alertmanager routes locally testable alerts.
8. The optional assistant receives only evidence selected and redacted by the API. It returns cited analysis or abstains and cannot execute changes.

## Durable ingestion flow

```text
agent collection
  -> bounded local spool
  -> HTTPS batch with idempotency key
  -> Nginx
  -> FastAPI transaction
       telemetry batch + idempotency record + outbox event
  -> HTTP acknowledgement
  -> outbox relay
  -> Redis Stream consumer group
  -> idempotent worker transition
  -> incident/fleet state
```

Acknowledgement occurs only after the PostgreSQL transaction commits. Redis unavailability can delay processing but cannot erase acknowledged work. Replayed agent batches return the original outcome without creating duplicate telemetry.

## Failure behavior

- Agents use request deadlines and capped exponential backoff with full jitter. The spool is bounded by age and size, with explicit drop metrics when exhausted.
- APIs use database and Redis timeouts. Cache failure falls back to PostgreSQL where safe.
- The relay republishes unsent outbox rows and records publication attempts.
- Workers acknowledge only completed jobs. Pending jobs are reclaimed after a visibility timeout.
- Retryable jobs move through bounded attempts; permanent failures enter a dead-letter stream with error and correlation metadata.
- Processes stop accepting new work on termination, finish or safely release in-flight work, flush metrics/logs, and exit within the orchestrator grace period.

## Network boundaries

| Boundary | Protocol | Exposure |
| --- | --- | --- |
| Agent to Nginx | HTTPS/TCP | Only intended ingress |
| Nginx to API | HTTP/TCP on private network | Container/Kubernetes network only |
| API/workers to PostgreSQL | PostgreSQL/TCP | Private network only |
| API/relay/workers to Redis | RESP/TCP | Private network only |
| Prometheus scrapes | HTTP/TCP | Monitoring network only |
| Grafana to Prometheus | HTTP/TCP | Monitoring network only |

Local diagnostics will explicitly exercise DNS resolution, TCP connections, TLS negotiation, HTTP behavior, socket visibility, reverse proxying, caching, load balancing, and firewall-style NetworkPolicies.

## Initial SLO targets

| SLO | Target | Indicator |
| --- | --- | --- |
| API availability | 99.9% monthly | Successful eligible requests / eligible requests |
| Durable ingestion latency | 99% within 2 seconds | Server receipt through PostgreSQL commit |
| Telemetry freshness | 99% within 5 seconds | Collection through durable acceptance, with clock skew disclosed |
| Alert detection | 95% within 60 seconds | First threshold-crossing sample through durable incident creation |

These values are targets until evidence demonstrates otherwise.

