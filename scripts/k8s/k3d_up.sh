#!/usr/bin/env bash
set -euo pipefail

repository_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "${repository_root}"

if ! k3d cluster list --no-headers | awk '{print $1}' | grep -qx fleetpulse; then
  k3d cluster create --config deploy/kubernetes/overlays/k3d/cluster.yaml --wait
fi

k3d image import --cluster fleetpulse \
  fleetpulse-api:phase5 \
  fleetpulse-worker:phase5 \
  fleetpulse-outbox-relay:phase5 \
  fleetpulse-agent:phase5

KUBE_CONTEXT=k3d-fleetpulse ./scripts/k8s/apply_runtime_secrets.sh
kubectl --context k3d-fleetpulse apply -k deploy/kubernetes/overlays/k3d
for workload in deployment/api deployment/worker deployment/outbox-relay deployment/nginx deployment/prometheus deployment/alertmanager deployment/grafana statefulset/postgres statefulset/redis daemonset/agent; do
  kubectl --context k3d-fleetpulse -n fleetpulse rollout status "${workload}" --timeout=240s
done
