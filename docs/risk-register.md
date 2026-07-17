# FleetPulse risk register

This register tracks engineering risks and the evidence required to close them. A target, projection, or installed configuration is not treated as measured proof.

| Risk | Impact | Current mitigation | Closure evidence | Status |
| --- | --- | --- | --- | --- |
| Local results are presented as production scale | Misleading portfolio claims and bad capacity decisions | Every report labels measured, projected, and target values | Phase 6 capacity report with raw machine/workload metadata | Open |
| Default local CNI does not enforce NetworkPolicy | Manifested boundaries may not be runtime firewall boundaries | Default-deny and explicit flows are versioned; Compose uses measured internal networks | Denied-flow tests on Calico or Cilium | Open |
| Concurrent API starts race schema migrations | Failed cold starts or partial schema state | PostgreSQL advisory lock held by a dedicated migration connection | Zero-restart clean kind and k3d cold starts | Mitigated |
| Local cluster deletion destroys test state | Lost local evidence or confusion about durability | Evidence is exported to Git; PostgreSQL/Redis use PVCs only within cluster lifetime | Recovery drill and backup/restore runbook | Open |
| Runtime credentials leak into Git or logs | Unauthorized local access and unsafe examples | Kustomize renders references only; ignored TLS; runtime Secret creation; placeholder examples | CI secret scan and clean-history audit | Mitigated, continuous |
| Redis outage blocks fleet processing | Queue backlog and stale cache | Durable PostgreSQL outbox, Redis persistence, reclaim, retries, and DLQ | Timed Redis failure/recovery drill | Open |
| Alerting looks correct but detects too slowly | SLO violation without timely response | Five-second scrape/evaluation locally and explicit detection SLO | Phase 7 threshold-to-firing measurements | Open |
| AI output is trusted as operational truth | Unsafe or unsupported remediation | AI remains optional, read-only, cited, redacted, and non-executing | Golden-set accuracy/abstention tests and approval-path audit | Open |
| Local host resources mask saturation | Unreliable throughput projections | Kubernetes limits plus required CPU/memory/backlog measurements | Repeated Phase 6 saturation runs | Open |
| Upstream image or dependency drift | Non-reproducible builds or supply-chain exposure | Version bounds and pinned runtime image tags | Image digest pinning, SBOM, and vulnerability scan in Phase 9 | Open |

The register is reviewed at each phase gate and updated when evidence changes a risk's status.
