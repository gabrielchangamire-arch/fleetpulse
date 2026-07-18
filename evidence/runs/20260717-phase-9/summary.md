# Phase 9 final CI and supply-chain evidence

Phase 9 is complete. The implementation commit under test was
`83ac5ebacfc2b68df17c92486a304e55f0c2599c`. The same commit passed the local clean-clone
CI-equivalent gate and clean kind/k3d runtime checks before this evidence-only update.

## Measured local results

| Check | Measured result |
| --- | --- |
| Full repository tests | 32/32 passed |
| Strict manifest validation | 42/42 resources valid for kind and 42/42 for k3d |
| Trivy configuration gate | 16 files scanned; 0 HIGH/CRITICAL misconfigurations |
| Python dependency audit | No known vulnerabilities in the hashed runtime lock |
| Repository secret scan | 23 commits scanned; no leaks found |
| Image evidence | 5 CycloneDX SBOMs and 5 full Trivy JSON reports |
| Image vulnerability policy | 0 fixable HIGH/CRITICAL findings |
| kind cold start | 13/13 pods ready; 0 restarts; both TLS smokes passed |
| k3d cold start | 13/13 pods ready; 0 restarts; both TLS smokes passed |
| Clean-clone stack | Every health check and both Compose TLS smokes passed |

## Acceptance criteria

- Python runtime and development dependencies are hash locked.
- Application bases, Compose/Kubernetes third-party runtimes, and security tools are digest pinned.
- GitHub Actions are commit pinned, default to read-only permissions, and have explicit timeouts.
- CI contains quality, dependency, secret, manifest, image/SBOM, and Compose smoke jobs.
- All Kubernetes containers use non-root execution, dropped capabilities, seccomp, immutable root
  filesystems, bounded resources, and dedicated writable volumes where required.
- A clean clone can install, test, audit, build, scan, start, smoke, and clean the local stack.
- Every portfolio claim in the catalog resolves to committed evidence and carries a limitation.

## Vulnerability interpretation

The five images share a digest-pinned Debian/Python base. Trivy reported 19 HIGH and 3 CRITICAL
inherited findings per image, with no upstream fixed version for any of them at measurement time.
Those repeated per-image counts must not be summed and presented as unique vulnerabilities.

The gate retains all findings and fails when a HIGH/CRITICAL item has an available fix. Therefore,
green means the current fixable-risk policy passed; it never means “zero vulnerabilities.” The
open inherited risk remains documented in the risk register and supply-chain runbook.

## Evidence map

- `metadata.json`: implementation SHA, host/runtime versions, tool digests, and commands.
- `verification.txt`: complete test, audit, clean-clone, Compose, kind, k3d, and boundary results.
- `supply-chain-summary.json`: per-image SBOM component and vulnerability counts.
- `checksums.sha256`: identifiers for the full ignored SBOM and Trivy report set.

## Claims and limitations

This completes the planned local-first repository scope. It demonstrates reproducible engineering
controls and measured single-host behavior; it does not claim production fleet scale, cloud
availability, or elimination of inherited vulnerabilities. Ongoing dependency/base refreshes and
repeated CI scans remain normal maintenance.
