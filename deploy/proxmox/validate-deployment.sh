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
require_root
require_command stat
validate_layout

current_image="$(read_current_image)"
[[ -n ${current_image} ]] || die "missing SERVICE_IMAGE in ${DEPLOYMENT_ENV}"
validate_image_digest "${current_image}"
info "${SERVICE_NAME} deployment inputs passed validation"
