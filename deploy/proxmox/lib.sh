#!/usr/bin/env bash
set -Eeuo pipefail

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

info() {
  printf '%s\n' "$*"
}

require_root() {
  [[ ${EUID} -eq 0 ]] || die "run this command as root"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

load_service() {
  case "${1:-}" in
    owui)
      SERVICE_NAME="owui"
      ETC_DIR="/etc/open-webui"
      DATA_PARENT="/srv/open-webui"
      DATA_DIR="${DATA_PARENT}/data"
      BACKUP_ROOT="/var/backups/open-webui-deploy"
      UNIT_NAME="open-webui-compose.service"
      HEALTH_URL="http://127.0.0.1:8080/health"
      ;;
    studio)
      SERVICE_NAME="studio"
      ETC_DIR="/etc/open-webui-studio"
      DATA_PARENT="/srv/open-webui-studio"
      DATA_DIR="${DATA_PARENT}/data"
      BACKUP_ROOT="/var/backups/open-webui-studio-deploy"
      UNIT_NAME="open-webui-studio-compose.service"
      HEALTH_URL="http://127.0.0.1:3000/studio/health"
      ;;
    *)
      die "service must be 'owui' or 'studio'"
      ;;
  esac

  COMPOSE_FILE="${ETC_DIR}/compose.yaml"
  DEPLOYMENT_ENV="${ETC_DIR}/deployment.env"
  RUNTIME_ENV="${ETC_DIR}/runtime.env"
  LOCK_FILE="/run/lock/${SERVICE_NAME}-deploy.lock"
}

validate_image_digest() {
  local image="${1:-}"
  [[ ${image} =~ ^[^[:space:]]+@sha256:[0-9a-f]{64}$ ]] ||
    die "image must use registry/repository@sha256:<64 lowercase hex characters>"
}

validate_runtime_file() {
  [[ -f ${RUNTIME_ENV} ]] || die "missing runtime environment file: ${RUNTIME_ENV}"

  local mode
  mode="$(stat -c '%a' "${RUNTIME_ENV}")"
  case "${mode}" in
    400 | 600) ;;
    *) die "${RUNTIME_ENV} must have mode 0400 or 0600" ;;
  esac

  [[ $(stat -c '%u' "${RUNTIME_ENV}") -eq 0 ]] ||
    die "${RUNTIME_ENV} must be owned by root"
}

validate_control_file() {
  local path="$1"
  local mode
  [[ -f ${path} ]] || die "missing deployment control file: ${path}"
  [[ $(stat -c '%u' "${path}") -eq 0 ]] || die "${path} must be owned by root"
  mode="$(stat -c '%a' "${path}")"
  case "${mode}" in
    400 | 440 | 444 | 600 | 640 | 644) ;;
    *) die "${path} must not be writable by group or other users" ;;
  esac
}

validate_layout() {
  validate_control_file "${COMPOSE_FILE}"
  if [[ -f ${DEPLOYMENT_ENV} ]]; then
    validate_control_file "${DEPLOYMENT_ENV}"
  fi
  [[ -d ${DATA_DIR} ]] || die "missing data directory: ${DATA_DIR}"
  validate_runtime_file
  mkdir -p "${BACKUP_ROOT}/releases"
  chmod 0700 "${BACKUP_ROOT}" "${BACKUP_ROOT}/releases"
}

read_current_image() {
  [[ -f ${DEPLOYMENT_ENV} ]] || return 0
  sed -n 's/^SERVICE_IMAGE=//p' "${DEPLOYMENT_ENV}" | head -n 1
}

write_deployment_env() {
  local image="$1"
  local temporary
  validate_image_digest "${image}"
  temporary="$(mktemp "${ETC_DIR}/deployment.env.XXXXXX")"
  chmod 0600 "${temporary}"
  printf 'SERVICE_IMAGE=%s\n' "${image}" >"${temporary}"
  mv -f -- "${temporary}" "${DEPLOYMENT_ENV}"
}

wait_for_health() {
  local attempts="${1:-60}"
  local delay_seconds="${2:-2}"
  local attempt

  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if curl --fail --silent --show-error --max-time 5 "${HEALTH_URL}" >/dev/null; then
      return 0
    fi
    sleep "${delay_seconds}"
  done

  return 1
}

stop_service() {
  if systemctl is-active --quiet "${UNIT_NAME}"; then
    systemctl stop "${UNIT_NAME}"
  fi
}

start_service() {
  systemctl start "${UNIT_NAME}"
}

record_checksum() {
  local archive="$1"
  sha256sum "${archive}" >"${archive}.sha256"
  chmod 0600 "${archive}.sha256"
}

verify_checksum() {
  local archive="$1"
  (cd "$(dirname "${archive}")" && sha256sum --check "$(basename "${archive}").sha256")
}
