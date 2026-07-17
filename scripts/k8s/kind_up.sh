#!/usr/bin/env bash
set -euo pipefail

repository_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "${repository_root}"

if ! kind get clusters | grep -qx fleetpulse; then
  kind create cluster --config deploy/kubernetes/overlays/kind/cluster.yaml --wait 120s
fi

for image in fleetpulse-api:phase5 fleetpulse-worker:phase5 fleetpulse-outbox-relay:phase5 fleetpulse-agent:phase5; do
  kind load docker-image --name fleetpulse "${image}"
done

KUBE_CONTEXT=kind-fleetpulse ./scripts/k8s/apply_runtime_secrets.sh
kubectl --context kind-fleetpulse apply -k deploy/kubernetes/overlays/kind
for workload in deployment/api deployment/worker deployment/outbox-relay deployment/nginx deployment/prometheus deployment/alertmanager deployment/grafana statefulset/postgres statefulset/redis daemonset/agent; do
  kubectl --context kind-fleetpulse -n fleetpulse rollout status "${workload}" --timeout=240s
done
