#!/usr/bin/env bash
set -euo pipefail

repository_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
source "${repository_root}/security/tool-images.env"
cd "${repository_root}"

docker run --rm -v "${repository_root}:/repo" -w /repo "${ACTIONLINT_IMAGE}"

for overlay in kind k3d; do
  kubectl kustomize "deploy/kubernetes/overlays/${overlay}" \
    | docker run --rm -i "${KUBECONFORM_IMAGE}" -strict -summary
done

"${repository_root}/.venv/bin/python" tools/kubernetes_contract.py
"${repository_root}/.venv/bin/python" tools/ci_contract.py
"${repository_root}/.venv/bin/python" tools/evidence_claims.py

FLEETPULSE_AGENT_TOKEN=static-placeholder \
FLEETPULSE_POSTGRES_PASSWORD=static-placeholder \
  docker compose config --quiet
FLEETPULSE_AGENT_TOKEN=static-placeholder \
FLEETPULSE_POSTGRES_PASSWORD=static-placeholder \
  docker compose --profile ai config --quiet

docker run --rm \
  -v "${repository_root}:/work" -w /work \
  -v fleetpulse_trivy_cache:/root/.cache/ \
  "${TRIVY_IMAGE}" config --skip-version-check --severity HIGH,CRITICAL \
  --exit-code 1 --skip-dirs evidence --skip-dirs .venv .
