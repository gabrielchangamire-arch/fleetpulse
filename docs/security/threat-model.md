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
| AI prompt injection or hallucination | Bounded untrusted evidence, pre/post redaction, strict output schema, citation allowlist, fail-closed abstention, deterministic accuracy tests, no tools |
| AI/provider availability becomes operational dependency | Disabled default profile, offline test provider, no core-service dependency, no database/Redis credential |
| Unauthorized remediation | No execution endpoint; generated proposals require explicit review; approval receipts state execution is unavailable |
| Supply-chain compromise | Hashed Python locks; commit-pinned actions; digest-pinned base, service, and scanner images; dependency/config/image scans; per-image CycloneDX SBOMs and checksums |

Residual risks and test evidence are updated as each runtime phase is implemented.
