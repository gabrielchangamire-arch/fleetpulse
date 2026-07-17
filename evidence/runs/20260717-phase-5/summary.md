# Phase 5 verification summary

Result: **passed** on local kind and k3d environments at commit `f3aef45f5b5d8a07be7e3c55207141a0ee511770`.

## Verified outcomes

- Both Kustomize overlays rendered 42 resources and passed strict `kubeconform` validation plus the FleetPulse Kubernetes contract.
- Clean kind and k3d starts converged with 13/13 ready pods and zero application/init-container restarts.
- Two API replicas safely serialized concurrent Alembic upgrades with a PostgreSQL advisory lock.
- TLS ingress, agent authentication, PostgreSQL durability, and batch idempotency passed in both runtimes.
- Prometheus discovered each API and worker replica through headless services; every target was up.
- CPU/memory bounds, readiness/liveness probes, rolling strategies, PDBs, persistent volumes, ConfigMaps, runtime Secret references, and 12 NetworkPolicies are present.
- A normal API rolling restart served 40/40 health probes. A missing-image rollout failed while both old replicas stayed available, and `rollout undo` restored the good image.
- PostgreSQL, Redis, Prometheus, Alertmanager, and Grafana remained ClusterIP-only. Local host mappings listened on loopback and exposed only Nginx.

## Claim boundary and known limitation

These are functional local-cluster results, not production scale measurements. Performance, capacity, detection time, and recovery time remain Phase 6/7 work. NetworkPolicy objects were installed and validated, but the default kind/k3d CNIs are not claimed here to enforce every policy; enforcement must be tested with a policy-capable CNI before making a runtime firewall claim. The Compose internal-network and host-port audits remain the measured network-boundary evidence.

See `manifest-validation.txt`, `cluster-smoke.txt`, `rollout-rollback.txt`, and `metadata.json` for the preserved evidence.
