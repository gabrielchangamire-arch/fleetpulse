# FleetPulse risk register

This register tracks engineering risks and the evidence required to close them. A target, projection, or installed configuration is not treated as measured proof.

| Risk | Impact | Current mitigation | Closure evidence | Status |
| --- | --- | --- | --- | --- |
| Local results are presented as production scale | Misleading portfolio claims and bad capacity decisions | Every report labels measured, projected, and target values; Phase 6 retains raw machine/workload evidence | Continued claim-to-evidence review as new benchmarks are added | Mitigated, continuous |
| Default local CNI does not enforce NetworkPolicy | Manifested boundaries may not be runtime firewall boundaries | Default-deny and explicit flows are versioned; Compose uses measured internal networks | Denied-flow tests on Calico or Cilium | Open |
| Concurrent API starts race schema migrations | Failed cold starts or partial schema state | PostgreSQL advisory lock held by a dedicated migration connection | Zero-restart clean kind and k3d cold starts | Mitigated |
| Local cluster deletion destroys test state | Lost local evidence or confusion about durability | Evidence is exported to Git; PostgreSQL/Redis use PVCs only within cluster lifetime | Recovery drill and backup/restore runbook | Open |
| Runtime credentials leak into Git or logs | Unauthorized local access and unsafe examples | Kustomize renders references only; ignored TLS; runtime Secret creation; placeholder examples | CI secret scan and clean-history audit | Mitigated, continuous |
| Redis outage blocks fleet processing | Queue backlog and stale cache | Durable PostgreSQL outbox recovered the exact Phase 7 outage batch with no unpublished or dead-lettered state | Add bounded worker reconnect backoff and reduce repeated relay traceback noise found by the drill | Mitigated; hardening open |
| Alerting looks correct but detects too slowly | SLO violation without timely response | Five-second scrape/evaluation and measured Phase 7 API, incident, and outbox alerts | Continue repeated drills when rules or runtime topology change | Mitigated, continuous |
| AI output is trusted as operational truth | Unsafe or unsupported remediation | Optional isolated service redacts input/output, validates citations, fails closed, has no tools or execution route, and requires human review | Phase 8 five-case golden set, route audit, review-gate tests, and loopback-only container smoke | Mitigated; continuous live-model evaluation open |
| Local host resources mask saturation | Unreliable throughput projections | Phase 6 records Docker CPU, memory, latency, errors, and backlog and explicitly avoids calling fixed-rate trials saturation tests | Repeated saturation curve on a controlled host, not the Phase 6 fixed-rate comparison | Open |
| Upstream image or dependency drift | Non-reproducible builds or supply-chain exposure | Hashed dependency locks, digest-pinned images/scanners, commit-pinned actions, SBOM artifacts, and dated dependency/config/image gates | Re-run on each dependency/image update; track inherited unfixed CVEs until an upstream fixed version exists | Mitigated, continuous |
| Inherited base-image vulnerabilities lack upstream fixes | Known exposure cannot be removed by rebuilding the same base | Full Trivy reports retain all HIGH/CRITICAL findings; the gate fails any finding with a fixed version; image digest refresh is deliberate | Zero reported HIGH/CRITICAL findings, or documented upstream fixes followed by a clean rebuild | Open, externally constrained |

The register is reviewed at each phase gate and updated when evidence changes a risk's status.
