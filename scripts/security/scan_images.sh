#!/usr/bin/env bash
set -euo pipefail

repository_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
tag=${1:-phase9}
output_dir=${2:-"${repository_root}/artifacts/supply-chain"}
source "${repository_root}/security/tool-images.env"

mkdir -p "${output_dir}"
output_dir=$(cd "${output_dir}" && pwd)
cache_volume=${FLEETPULSE_TRIVY_CACHE_VOLUME:-fleetpulse_trivy_cache}
images=(api worker outbox-relay agent assistant)

for name in "${images[@]}"; do
  image="fleetpulse-${name}:${tag}"
  docker image inspect "${image}" >/dev/null

  docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "${cache_volume}:/root/.cache/" \
    -v "${output_dir}:/output" \
    "${TRIVY_IMAGE}" image --skip-version-check --scanners vuln \
    --severity HIGH,CRITICAL --format json --output "/output/${name}.trivy.json" "${image}"

  docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "${output_dir}:/output" \
    "${SYFT_IMAGE}" scan "docker:${image}" \
    -o "cyclonedx-json=/output/${name}.cdx.json"
done

report_status=0
"${repository_root}/.venv/bin/python" "${repository_root}/tools/supply_chain_report.py" \
  --directory "${output_dir}" --output "${output_dir}/summary.json" || report_status=$?

(
  cd "${output_dir}"
  shasum -a 256 ./*.cdx.json ./*.trivy.json summary.json >checksums.sha256
)

exit "${report_status}"
