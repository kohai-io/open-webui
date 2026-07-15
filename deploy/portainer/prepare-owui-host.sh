#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

DATA_PATH="/srv/stacks/owui-staging/data"
BIND_ADDRESS=""
HOST_PORT=""
MINIMUM_FREE_GIB=32
CONFIRM=false
CHECK_ONLY=false

usage() {
  cat <<'EOF'
Usage: prepare-owui-host.sh --bind-address ADDRESS --host-port PORT [options]

Validates a Docker Standalone host for the OWUI Portainer stack and creates
only the dedicated bind-mount directory. It does not deploy a stack, inspect
container environments, log in to a registry, stop a container, or delete
anything.

Required:
  --bind-address ADDRESS   Address on Docker VM 113 that Caddy can reach
  --host-port PORT         Unused host TCP port to publish OWUI

Options:
  --data-path PATH         Default: /srv/stacks/owui-staging/data
  --minimum-free-gib N     Default: 32
  --check-only             Validate without creating the data directory
  --confirm                Allow creation of the data directory
  -h, --help               Show this help
EOF
}

info() {
  printf '[owui-portainer-prep] %s\n' "$*"
}

die() {
  printf '[owui-portainer-prep] ERROR: %s\n' "$*" >&2
  exit 1
}

while (($# > 0)); do
  case "$1" in
  --bind-address)
    [[ $# -ge 2 ]] || die "--bind-address requires a value"
    BIND_ADDRESS=$2
    shift 2
    ;;
  --host-port)
    [[ $# -ge 2 ]] || die "--host-port requires a value"
    HOST_PORT=$2
    shift 2
    ;;
  --data-path)
    [[ $# -ge 2 ]] || die "--data-path requires a value"
    DATA_PATH=$2
    shift 2
    ;;
  --minimum-free-gib)
    [[ $# -ge 2 ]] || die "--minimum-free-gib requires a value"
    MINIMUM_FREE_GIB=$2
    shift 2
    ;;
  --check-only)
    CHECK_ONLY=true
    shift
    ;;
  --confirm)
    CONFIRM=true
    shift
    ;;
  -h | --help)
    usage
    exit 0
    ;;
  *)
    die "unknown option: $1"
    ;;
  esac
done

[[ ${EUID} -eq 0 ]] || die "run as root on Docker VM 113"
[[ -n ${BIND_ADDRESS} ]] || die "--bind-address is required"
[[ ${BIND_ADDRESS} =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || die "bind address must be IPv4"
IFS='.' read -r ip1 ip2 ip3 ip4 <<<"${BIND_ADDRESS}"
for octet in "${ip1}" "${ip2}" "${ip3}" "${ip4}"; do
  ((octet >= 0 && octet <= 255)) || die "invalid bind address"
done
[[ ${HOST_PORT} =~ ^[1-9][0-9]*$ ]] && ((HOST_PORT <= 65535)) || die "invalid host port"
[[ ${MINIMUM_FREE_GIB} =~ ^[1-9][0-9]*$ ]] || die "minimum free space must be positive"
[[ ${DATA_PATH} == /* ]] || die "data path must be absolute"

for command_name in docker curl findmnt df stat ss install awk grep ip; do
  command -v "${command_name}" >/dev/null 2>&1 || die "required command not found: ${command_name}"
done

docker info >/dev/null 2>&1 || die "Docker Engine is unavailable"
docker_arch="$(docker info --format '{{.Architecture}}')"
docker_os="$(docker info --format '{{.OSType}}')"
swarm_state="$(docker info --format '{{.Swarm.LocalNodeState}}')"
[[ ${docker_arch} == "x86_64" || ${docker_arch} == "amd64" ]] || die "Docker architecture is not amd64"
[[ ${docker_os} == "linux" ]] || die "Docker host is not Linux"
[[ ${swarm_state} == "inactive" ]] || die "this bundle requires Portainer Docker Standalone, not Swarm"

docker network inspect infra >/dev/null 2>&1 || die "required external Docker network does not exist: infra"
infra_network="$(docker network inspect --format '{{.Driver}}/{{.Scope}}' infra)"

ip -brief address 2>/dev/null | awk '{print $3}' | tr ' ' '\n' | grep -Eq "^${BIND_ADDRESS}/" ||
  die "bind address is not configured on this host"

if ss -H -lnt | awk '{print $4}' | grep -Eq "(^|:|\])${HOST_PORT}$"; then
  die "TCP port ${HOST_PORT} is already listening"
fi

if [[ -e ${DATA_PATH} ]]; then
  [[ -d ${DATA_PATH} && ! -L ${DATA_PATH} ]] || die "data path exists but is not a real directory"
fi

probe_path=${DATA_PATH}
while [[ ! -e ${probe_path} ]]; do
  probe_path=$(dirname -- "${probe_path}")
done

read -r filesystem_type filesystem_source filesystem_target < <(
  findmnt -n -o FSTYPE,SOURCE,TARGET -T "${probe_path}"
)
case "${filesystem_type}" in
nfs | nfs4 | cifs | smb3 | fuse.sshfs)
  die "data path resolves to unsupported live SQLite filesystem: ${filesystem_type}"
  ;;
esac

available_kib="$(df -Pk "${probe_path}" | awk 'NR == 2 {print $4}')"
required_kib=$((MINIMUM_FREE_GIB * 1024 * 1024))
[[ ${available_kib} =~ ^[0-9]+$ ]] || die "could not determine free space"
((available_kib >= required_kib)) || die "less than ${MINIMUM_FREE_GIB} GiB is free for the data path"

registry_status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
  https://git.theoldschool.house/v2/)"
[[ ${registry_status} == "401" || ${registry_status} == "200" ]] ||
  die "Gitea registry check returned HTTP ${registry_status}"

info "Docker: ${docker_os}/${docker_arch}, Swarm ${swarm_state}"
info "external network: infra (${infra_network})"
info "bind: ${BIND_ADDRESS}:${HOST_PORT} (currently unused)"
info "data filesystem: ${filesystem_type} on ${filesystem_source} mounted at ${filesystem_target}"
info "data path: ${DATA_PATH}"
info "Gitea registry API: HTTP ${registry_status}"

if ${CHECK_ONLY}; then
  info "check-only completed; no state was changed"
  exit 0
fi

${CONFIRM} || die "directory creation requires --confirm"

if [[ ! -e ${DATA_PATH} ]]; then
  install -d -o 1000 -g 1000 -m 0750 "${DATA_PATH}"
else
  data_identity="$(stat -c '%u:%g:%a' "${DATA_PATH}")"
  [[ ${data_identity} == "1000:1000:750" ]] ||
    die "existing data directory must already be owned 1000:1000 with mode 0750"
fi

data_identity="$(stat -c '%u:%g:%a' "${DATA_PATH}")"
[[ ${data_identity} == "1000:1000:750" ]] || die "data-directory identity validation failed"

info "host preparation completed"
info "next: add the Gitea registry and deploy owui-stack.compose.yaml in Portainer"
