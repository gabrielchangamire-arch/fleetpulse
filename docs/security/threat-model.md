# Threat model

## Protected assets

- Agent enrollment credentials and service secrets
- Fleet, incident, deployment, and telemetry records
- Host process and network metadata
- Operational evidence and audit history
- Integrity of human approval records

## Trust boundaries

- Agent to Nginx over TLS
- Edge proxy to private application network
- Application services to PostgreSQL and Redis
- Monitoring plane to application metrics
- Core API to the optional AI assistant/provider

## Principal threats and controls

| Threat | Planned controls |
| --- | --- |
| Forged or replayed telemetry | Agent identity, TLS, request limits, stable idempotency keys, uniqueness constraints |
| Secret leakage in process data or logs | No process command lines/environments by default, structured allowlists, centralized redaction tests |
| Lateral access to data stores | No public ports, private networks, least-privilege roles, Kubernetes NetworkPolicies |
| Queue poisoning or retry storm | Schema validation, capped retries with jitter, retry budget, DLQ, backlog alerts |
| Cache poisoning or stale authorization | Cache only non-secret derived reads, versioned keys, bounded TTL, source-of-truth checks |
| AI prompt injection or hallucination | Curated evidence, redaction, strict output schema, citations, abstention, accuracy tests, no tools |
| Unauthorized remediation | No execution endpoint; approval is auditable metadata only |
| Supply-chain compromise | Locked dependencies, dependency and image scanning, SBOMs, pinned CI actions |

Residual risks and test evidence are updated as each runtime phase is implemented.

