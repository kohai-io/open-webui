#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

usage() {
  printf 'Usage: %s <owui|studio> <release-record-directory> --confirm-restore-data\n' "$0"
}

[[ $# -eq 3 ]] || {
  usage >&2
  exit 2
}

service="$1"
requested_release="$2"
confirmation="$3"

[[ ${confirmation} == "--confirm-restore-data" ]] || die "missing --confirm-restore-data"
load_service "${service}"
require_root
for command_name in curl docker flock mktemp realpath sha256sum stat systemctl tar; do
  require_command "${command_name}"
done
validate_layout

exec 9>"${LOCK_FILE}"
flock -n 9 || die "another ${SERVICE_NAME} deployment operation is running"

release_base="$(realpath -e "${BACKUP_ROOT}/releases")"
release_dir="$(realpath -e -- "${requested_release}")"
case "${release_dir}" in
  "${release_base}"/*) ;;
  *) die "release record must be under ${release_base}" ;;
esac

archive="${release_dir}/data.tar.gz"
previous_image_file="${release_dir}/previous-image"
[[ -f ${archive} && -f ${archive}.sha256 && -f ${previous_image_file} ]] ||
  die "release record is incomplete"

previous_image="$(<"${previous_image_file}")"
[[ -n ${previous_image} ]] || die "this release record has no previous image"
validate_image_digest "${previous_image}"
verify_checksum "${archive}"

info "Pulling the recorded rollback digest for ${SERVICE_NAME}"
docker pull "${previous_image}"

timestamp="$(date -u +'%Y%m%dT%H%M%SZ')"
failed_data="${DATA_PARENT}/failed-data-${timestamp}"
data_uid="$(stat -c '%u' "${DATA_DIR}")"
data_gid="$(stat -c '%g' "${DATA_DIR}")"
data_mode="$(stat -c '%a' "${DATA_DIR}")"

info "Stopping ${SERVICE_NAME} and preserving candidate data"
stop_service
mv -- "${DATA_DIR}" "${failed_data}"
mkdir -p "${DATA_DIR}"
chown "${data_uid}:${data_gid}" "${DATA_DIR}"
chmod "${data_mode}" "${DATA_DIR}"
tar --acls --xattrs --numeric-owner -C "${DATA_DIR}" -xzpf "${archive}"

write_deployment_env "${previous_image}"
start_service
if ! wait_for_health 60 2; then
  stop_service
  die "rollback image failed health checks; restored data remains at ${DATA_DIR}, candidate data remains at ${failed_data}"
fi

printf '%s\n' "${timestamp}" >"${release_dir}/rolled-back-at"
printf '%s\n' "${failed_data}" >"${release_dir}/failed-data-path"
chmod 0600 "${release_dir}/rolled-back-at" "${release_dir}/failed-data-path"
info "Rollback passed health checks"
info "Candidate data preserved at ${failed_data}"
