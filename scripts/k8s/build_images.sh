#!/usr/bin/env bash
set -euo pipefail

repository_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
tag=${1:-phase5}

docker build -f "${repository_root}/services/api/Dockerfile" -t "fleetpulse-api:${tag}" "${repository_root}"
docker build -f "${repository_root}/services/worker/Dockerfile" -t "fleetpulse-worker:${tag}" "${repository_root}"
docker build -f "${repository_root}/services/outbox_relay/Dockerfile" -t "fleetpulse-outbox-relay:${tag}" "${repository_root}"
docker build -f "${repository_root}/agent/Dockerfile" -t "fleetpulse-agent:${tag}" "${repository_root}"

