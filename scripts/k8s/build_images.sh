#!/usr/bin/env bash
set -euo pipefail

repository_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
tag=${1:-phase5}

"${repository_root}/scripts/security/build_images.sh" "${tag}"
