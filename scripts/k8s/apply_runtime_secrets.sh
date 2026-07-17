#!/usr/bin/env bash
set -euo pipefail

: "${FLEETPULSE_AGENT_TOKEN:?set FLEETPULSE_AGENT_TOKEN}"
: "${FLEETPULSE_POSTGRES_PASSWORD:?set FLEETPULSE_POSTGRES_PASSWORD}"

if [[ ! ${FLEETPULSE_POSTGRES_PASSWORD} =~ ^[A-Za-z0-9._~-]+$ ]]; then
  echo "FLEETPULSE_POSTGRES_PASSWORD must use URI-safe characters: A-Z a-z 0-9 . _ ~ -" >&2
  exit 2
fi

repository_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
context=${KUBE_CONTEXT:-kind-fleetpulse}
tls_directory="${repository_root}/certs/generated"

if [[ ! -f "${tls_directory}/server.crt" || ! -f "${tls_directory}/server.key" || ! -f "${tls_directory}/ca.crt" ]]; then
  "${repository_root}/scripts/generate_local_tls.sh"
fi

kubectl --context "${context}" apply -f "${repository_root}/deploy/kubernetes/base/namespace.yaml"
kubectl --context "${context}" -n fleetpulse create secret generic fleetpulse-runtime \
  --from-literal="agent-token=${FLEETPULSE_AGENT_TOKEN}" \
  --from-literal="postgres-password=${FLEETPULSE_POSTGRES_PASSWORD}" \
  --from-literal="database-url=postgresql+asyncpg://fleetpulse:${FLEETPULSE_POSTGRES_PASSWORD}@postgres:5432/fleetpulse" \
  --dry-run=client -o yaml | kubectl --context "${context}" apply -f -
kubectl --context "${context}" -n fleetpulse create secret generic fleetpulse-tls \
  --from-file="tls.crt=${tls_directory}/server.crt" \
  --from-file="tls.key=${tls_directory}/server.key" \
  --from-file="ca.crt=${tls_directory}/ca.crt" \
  --dry-run=client -o yaml | kubectl --context "${context}" apply -f -

