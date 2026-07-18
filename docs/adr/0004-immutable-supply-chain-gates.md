# ADR 0004: Immutable supply-chain references and evidence-producing gates

- Status: Accepted
- Date: 2026-07-17

## Context

Mutable action tags, container tags, and unconstrained dependency resolution weaken reproducibility.
A scanner badge without retained output also cannot support a future portfolio or audit claim.

## Decision

GitHub Actions use exact commit SHAs. Runtime base and third-party service images, plus scanner
images, use human-readable tags followed by OCI manifest-list digests. Python runtime and
development dependencies are locked with package hashes.

CI renders and schema-validates both Kubernetes overlays, enforces FleetPulse-specific network and
secret-reference rules, runs a HIGH/CRITICAL infrastructure scan, builds all five application
images, generates CycloneDX JSON SBOMs, and retains SBOM, vulnerability, summary, and checksum
artifacts. A deterministic contract rejects mutable references.

The image gate reports every HIGH/CRITICAL result. It fails when a finding has an upstream fixed
version. Unfixed findings are not hidden: they remain in the Trivy JSON and summary, and require a
base-image refresh/re-scan when upstream publishes a fix. This policy avoids claiming a clean image
when the scanner still reports inherited risk.

## Consequences

Updates require deliberate digest, lock, and evidence changes. Multi-platform manifest digests
remain portable across supported local and GitHub runner architectures. Scanner databases change
over time, so a passing historical report is dated evidence rather than a permanent safety claim.

