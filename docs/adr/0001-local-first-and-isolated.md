# ADR 0001: Local-first and isolated operation

- Status: Accepted
- Date: 2026-07-17

## Context

FleetPulse must be independently reproducible without relying on an existing VM project or cloud account.

## Decision

Docker Compose and local kind/k3d clusters are the supported primary environments. The repository is physically and logically separate from existing Nemo/Oracle VM work. Cloud support, if added, lives in optional overlays with no dependency from local commands.

## Consequences

Local testing remains accessible and safe. Environment-specific performance limitations must be disclosed. Cloud-specific production characteristics cannot be claimed from local results.

