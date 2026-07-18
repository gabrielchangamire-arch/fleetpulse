#!/usr/bin/env bash
set -euo pipefail

repository_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
python_bin=${FLEETPULSE_CLEAN_PYTHON:-}
output_dir=${FLEETPULSE_CLEAN_OUTPUT_DIR:-"${repository_root}/artifacts/clean-clone"}
temporary_root=$(mktemp -d "${TMPDIR:-/tmp}/fleetpulse-clean.XXXXXX")
clone_root="${temporary_root}/fleetpulse"
compose_project=fleetpulse-phase9-clean
compose_started=false

if [[ -z "${python_bin}" ]]; then
  for candidate in python3.13 python3.12; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      python_bin=${candidate}
      break
    fi
  done
fi
if [[ -z "${python_bin}" ]]; then
  echo "Python 3.12 or 3.13 is required for the clean-clone gate" >&2
  exit 2
fi

cleanup() {
  if [[ "${compose_started}" == true && -d "${clone_root}" ]]; then
    (
      cd "${clone_root}"
      FLEETPULSE_AGENT_TOKEN=clean-clone-placeholder \
      FLEETPULSE_POSTGRES_PASSWORD=clean-clone-placeholder \
      COMPOSE_PROJECT_NAME="${compose_project}" docker compose down -v --remove-orphans
    ) || true
  fi
  case "${temporary_root}" in
    "${TMPDIR:-/tmp}"/fleetpulse-clean.*) rm -rf -- "${temporary_root}" ;;
    *) echo "refusing to remove unexpected temporary path: ${temporary_root}" >&2 ;;
  esac
}
trap cleanup EXIT

git clone --quiet --no-local "${repository_root}" "${clone_root}"
cd "${clone_root}"

make PYTHON="${python_bin}" bootstrap
make verify
.venv/bin/python -m pip install pip-audit==2.10.1
.venv/bin/python -m pip_audit --require-hashes -r requirements.lock
./scripts/security/static_gate.sh
./scripts/security/build_images.sh phase9-clean
./scripts/security/scan_images.sh phase9-clean "${output_dir}"

./scripts/generate_local_tls.sh
compose_started=true
FLEETPULSE_AGENT_TOKEN=clean-clone-placeholder \
FLEETPULSE_POSTGRES_PASSWORD=clean-clone-placeholder \
COMPOSE_PROJECT_NAME="${compose_project}" docker compose up -d --build --wait
FLEETPULSE_AGENT_TOKEN=clean-clone-placeholder .venv/bin/python \
  scripts/phase1_smoke.py --token clean-clone-placeholder
FLEETPULSE_AGENT_TOKEN=clean-clone-placeholder .venv/bin/python \
  scripts/phase2_smoke.py --token clean-clone-placeholder

echo "Clean-clone CI-equivalent gate passed at $(git rev-parse HEAD)"
