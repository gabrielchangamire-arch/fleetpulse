# Local Kubernetes runbook

FleetPulse supports kind and k3d as local-first targets. Neither workflow contacts a cloud environment or exposes PostgreSQL, Redis, Prometheus, Alertmanager, or Grafana outside the cluster.

## Prerequisites

- Docker, `kubectl`, `kind` or `k3d`, and `kubeconform`
- generated local TLS from `make local-tls` (the startup scripts generate it if absent)
- an agent token and URI-safe PostgreSQL password in the shell environment

Use local values that contain no production credentials:

```bash
export FLEETPULSE_AGENT_TOKEN='replace-with-a-random-local-token'
export FLEETPULSE_POSTGRES_PASSWORD='replace-with-a-uri-safe-local-password'
```

The password must use only letters, digits, `.`, `_`, `~`, and `-` because it is embedded in the local async PostgreSQL URL. Runtime secrets are created directly in the cluster and are never rendered by Kustomize or committed.

## Validate and start

```bash
make k8s-validate
make kind-up
# or, when kind is stopped:
make k3d-up
```

Both local overlays bind Nginx to `127.0.0.1:8080` and `127.0.0.1:8443`. They cannot run concurrently on those ports.

Verify ingestion through TLS:

```bash
make phase1-smoke
```

Inspect private operator interfaces through temporary loopback port-forwards:

```bash
kubectl --context kind-fleetpulse -n fleetpulse port-forward service/prometheus 19090:9090
kubectl --context kind-fleetpulse -n fleetpulse port-forward service/grafana 13000:3000
```

## Rollout and rollback

Watch a normal rolling restart:

```bash
kubectl --context kind-fleetpulse -n fleetpulse rollout restart deployment/api
kubectl --context kind-fleetpulse -n fleetpulse rollout status deployment/api --timeout=120s
```

If a rollout fails, inspect it before undoing it:

```bash
kubectl --context kind-fleetpulse -n fleetpulse get pods
kubectl --context kind-fleetpulse -n fleetpulse describe deployment/api
kubectl --context kind-fleetpulse -n fleetpulse rollout history deployment/api
kubectl --context kind-fleetpulse -n fleetpulse rollout undo deployment/api
kubectl --context kind-fleetpulse -n fleetpulse rollout status deployment/api --timeout=120s
```

## Stop

Cluster deletion removes the local cluster and its volumes. It does not affect Compose volumes or any external project:

```bash
make kind-down
# or
make k3d-down
```

