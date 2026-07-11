#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

[[ $# -eq 1 ]] || {
  printf 'Usage: %s <owui|studio>\n' "$0" >&2
  exit 2
}

load_service "$1"
require_command curl

if wait_for_health 1 0; then
  info "${SERVICE_NAME} health check passed"
  exit 0
fi

die "${SERVICE_NAME} health check failed"
