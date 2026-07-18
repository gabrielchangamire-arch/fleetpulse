# Supply-chain verification runbook

## Fast local checks

```bash
make verify
make security-static
```

The static gate runs actionlint, strict kubeconform validation for kind and k3d, the custom
FleetPulse Kubernetes/CI contracts, both Compose profile renders, the evidence-to-claim audit, and
Trivy's HIGH/CRITICAL configuration scan.

## Application images and SBOMs

```bash
make image-scan
```

This builds API, worker, outbox relay, agent, and optional assistant images. Syft writes a
CycloneDX JSON SBOM for each image. Trivy writes complete HIGH/CRITICAL JSON reports, then runs a
gating pass that fails if any such finding has an upstream fixed version. Output is written under
ignored `artifacts/supply-chain/` with SHA-256 checksums.

The summary distinguishes file components from package/application components. Counts across five
images are per-image totals and therefore include the common base image five times; they are not
unique-package counts.

## Clean-clone gate

```bash
make clean-clone
```

The script clones only committed files into a validated temporary directory, bootstraps from the
hashed lock, runs tests and all static/security gates, generates SBOMs, starts the default Compose
stack with ephemeral placeholders, and exercises Phase 1 and Phase 2 smoke tests. It removes only
its own Compose project, volumes, and validated temporary directory.

## Updating dependencies or image digests

1. Change bounded dependency declarations in `pyproject.toml`.
2. Run `make lock` and review both hashed lock files.
3. Resolve the intended multi-platform image digest and update every matching Compose/Kubernetes
   reference.
4. Run `make final-gate`, inspect all unfixed findings, and record the dated result.
5. Never add a scanner suppression merely to obtain a green check. Document the finding, affected
   image, fixed-version status, and decision.

GitHub uploads the complete supply-chain directory for each run with 30-day retention. Committed
Phase 9 evidence keeps the summaries, checksums, policies, and workflow URL; the full local SBOMs
remain build artifacts to avoid treating a dated dependency inventory as current indefinitely.

