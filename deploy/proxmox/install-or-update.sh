#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

usage() {
  printf 'Usage: %s <owui|studio> <registry/image@sha256:digest> [--confirm-studio-idle]\n' "$0"
}

[[ $# -ge 2 && $# -le 3 ]] || {
  usage >&2
  exit 2
}

service="$1"
candidate_image="$2"
confirmation="${3:-}"

load_service "${service}"
validate_image_digest "${candidate_image}"
require_root
for command_name in curl docker flock mktemp sha256sum stat systemctl tar; do
  require_command "${command_name}"
done
validate_layout

exec 9>"${LOCK_FILE}"
flock -n 9 || die "another ${SERVICE_NAME} deployment operation is running"

previous_image="$(read_current_image)"
if [[ -n ${previous_image} ]]; then
  validate_image_digest "${previous_image}"
  [[ ${candidate_image} != "${previous_image}" ]] || die "candidate image is already deployed"
fi

if [[ ${SERVICE_NAME} == "studio" && -n ${previous_image} ]]; then
  [[ ${confirmation} == "--confirm-studio-idle" ]] ||
    die "confirm that no Flow is queued, running, or awaiting cancellation with --confirm-studio-idle"
fi

info "Pulling approved image digest for ${SERVICE_NAME}"
docker pull "${candidate_image}"

timestamp="$(date -u +'%Y%m%dT%H%M%SZ')"
release_dir="$(mktemp -d "${BACKUP_ROOT}/releases/${timestamp}.XXXXXX")"
archive="${release_dir}/data.tar.gz"
chmod 0700 "${release_dir}"

info "Stopping ${SERVICE_NAME} for a consistent data backup"
stop_service

tar --acls --xattrs --numeric-owner -C "${DATA_DIR}" -czpf "${archive}" .
chmod 0600 "${archive}"
record_checksum "${archive}"
printf '%s\n' "${previous_image}" >"${release_dir}/previous-image"
printf '%s\n' "${candidate_image}" >"${release_dir}/candidate-image"
chmod 0600 "${release_dir}/previous-image" "${release_dir}/candidate-image"

write_deployment_env "${candidate_image}"

info "Starting ${SERVICE_NAME} with the approved digest"
start_service
if ! wait_for_health 60 2; then
  stop_service
  die "health check failed; candidate stopped. Restore with rollback.sh ${SERVICE_NAME} ${release_dir} --confirm-restore-data"
fi

printf '%s\n' "${timestamp}" >"${release_dir}/deployed-at"
chmod 0600 "${release_dir}/deployed-at"
info "Deployment passed health checks"
info "Release record: ${release_dir}"
