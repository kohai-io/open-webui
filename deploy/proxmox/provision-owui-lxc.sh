#!/usr/bin/env bash
set -Eeuo pipefail

# Proxmox guest setup creates files inside the new LXC while inheriting this
# process umask. Keep normal system-file permissions here; sensitive evidence
# files are created explicitly as mode 0600 below.
umask 022

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

VMID=105
CT_HOSTNAME="owui-staging"
TEMPLATE="local:vztmpl/debian-13-standard_13.1-2_amd64.tar.zst"
ROOT_STORAGE="local-lvm"
ROOT_SIZE_GIB=24
DATA_STORAGE="local-lvm"
DATA_SIZE_GIB=16
BRIDGE="vmbr0"
NAMESERVERS="10.100.1.21 10.100.1.22"
MEMORY_MIB=8192
SWAP_MIB=1024
CORES=4
IMAGE_REF="git.theoldschool.house/robert/open-webui@sha256:012e5f80e9aaf508c5831fde9440a78fea3b7ff2f4b2a8ca451758e904e696c9"
BUNDLE_DIR="${SCRIPT_DIR}"

CONFIRM_CREATE=false
RESUME_EXISTING=false
CHECK_ONLY=false
STAGE="initialization"
EVIDENCE_FILE=""

usage() {
  cat <<'EOF'
Usage: provision-owui-lxc.sh [options]

Creates and prepares a stopped-from-clean-state OWUI LXC on a Proxmox host.
The script installs Docker, pulls the approved image digest, and installs the
reviewed deployment bundle. It does not create runtime.env, start OWUI, change
Caddy/DNS, stop another guest, or delete anything.

Options:
  --vmid ID                 Proxmox VMID (default: 105)
  --hostname NAME           LXC hostname (default: owui-staging)
  --template VOLUME         Proxmox template volume
  --root-storage NAME       Root-disk storage (default: local-lvm)
  --root-size-gib N         Root-disk size (default: 24)
  --data-storage NAME       Managed data storage (default: local-lvm)
  --data-size-gib N         Managed data size (default: 16)
  --bridge NAME             Proxmox bridge (default: vmbr0)
  --nameservers "IP IP"     Space-separated DNS servers
  --memory-mib N            LXC memory limit (default: 8192)
  --swap-mib N              LXC swap limit (default: 1024)
  --cores N                 LXC vCPU count (default: 4)
  --image REF               Required registry/repository@sha256:digest
  --bundle-dir PATH         Reviewed deploy/proxmox directory
  --check-only              Run host/input preflight without creating anything
  --confirm-create          Permit creation after an interactive VMID prompt
  --resume-existing         Resume only after validating an existing VMID
  -h, --help                Show this help

First run:
  ./provision-owui-lxc.sh --check-only
  ./provision-owui-lxc.sh --confirm-create

After a partial failure:
  ./provision-owui-lxc.sh --resume-existing
EOF
}

info() {
  printf '[owui-provision] %s\n' "$*"
}

warn() {
  printf '[owui-provision] WARNING: %s\n' "$*" >&2
}

die() {
  printf '[owui-provision] ERROR: %s\n' "$*" >&2
  exit 1
}

record() {
  [[ -n ${EVIDENCE_FILE} ]] || return 0
  printf '%s\n' "$*" >>"${EVIDENCE_FILE}"
}

on_error() {
  local exit_code=$?
  printf '[owui-provision] ERROR: failed during stage "%s" at line %s (exit %s).\n' \
    "${STAGE}" "${BASH_LINENO[0]:-unknown}" "${exit_code}" >&2
  printf '[owui-provision] No automatic cleanup was attempted. Inspect VMID %s before resuming.\n' \
    "${VMID}" >&2
  record "result=failed"
  record "failed_stage=${STAGE}"
  exit "${exit_code}"
}

trap on_error ERR

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

require_positive_integer() {
  local name=$1
  local value=$2
  [[ ${value} =~ ^[1-9][0-9]*$ ]] || die "${name} must be a positive integer"
}

require_nonnegative_integer() {
  local name=$1
  local value=$2
  [[ ${value} =~ ^[0-9]+$ ]] || die "${name} must be a non-negative integer"
}

validate_hostname() {
  local value=$1
  local label
  local -a labels
  [[ ${#value} -le 253 ]] || return 1
  IFS='.' read -r -a labels <<<"${value}"
  ((${#labels[@]} > 0)) || return 1
  for label in "${labels[@]}"; do
    [[ ${#label} -ge 1 && ${#label} -le 63 ]] || return 1
    [[ ${label} =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ || ${label} =~ ^[a-z0-9]$ ]] || return 1
  done
}

validate_storage_name() {
  [[ $1 =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]
}

validate_bridge_name() {
  [[ $1 =~ ^[A-Za-z0-9][A-Za-z0-9._:-]*$ ]]
}

validate_image_digest() {
  [[ $1 =~ ^[^[:space:]@]+@sha256:[a-f0-9]{64}$ ]]
}

while (($# > 0)); do
  case "$1" in
  --vmid)
    [[ $# -ge 2 ]] || die "--vmid requires a value"
    VMID=$2
    shift 2
    ;;
  --hostname)
    [[ $# -ge 2 ]] || die "--hostname requires a value"
    CT_HOSTNAME=$2
    shift 2
    ;;
  --template)
    [[ $# -ge 2 ]] || die "--template requires a value"
    TEMPLATE=$2
    shift 2
    ;;
  --root-storage)
    [[ $# -ge 2 ]] || die "--root-storage requires a value"
    ROOT_STORAGE=$2
    shift 2
    ;;
  --root-size-gib)
    [[ $# -ge 2 ]] || die "--root-size-gib requires a value"
    ROOT_SIZE_GIB=$2
    shift 2
    ;;
  --data-storage)
    [[ $# -ge 2 ]] || die "--data-storage requires a value"
    DATA_STORAGE=$2
    shift 2
    ;;
  --data-size-gib)
    [[ $# -ge 2 ]] || die "--data-size-gib requires a value"
    DATA_SIZE_GIB=$2
    shift 2
    ;;
  --bridge)
    [[ $# -ge 2 ]] || die "--bridge requires a value"
    BRIDGE=$2
    shift 2
    ;;
  --nameservers)
    [[ $# -ge 2 ]] || die "--nameservers requires a value"
    NAMESERVERS=$2
    shift 2
    ;;
  --memory-mib)
    [[ $# -ge 2 ]] || die "--memory-mib requires a value"
    MEMORY_MIB=$2
    shift 2
    ;;
  --swap-mib)
    [[ $# -ge 2 ]] || die "--swap-mib requires a value"
    SWAP_MIB=$2
    shift 2
    ;;
  --cores)
    [[ $# -ge 2 ]] || die "--cores requires a value"
    CORES=$2
    shift 2
    ;;
  --image)
    [[ $# -ge 2 ]] || die "--image requires a value"
    IMAGE_REF=$2
    shift 2
    ;;
  --bundle-dir)
    [[ $# -ge 2 ]] || die "--bundle-dir requires a value"
    BUNDLE_DIR=$2
    shift 2
    ;;
  --check-only)
    CHECK_ONLY=true
    shift
    ;;
  --confirm-create)
    CONFIRM_CREATE=true
    shift
    ;;
  --resume-existing)
    RESUME_EXISTING=true
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

[[ ${EUID} -eq 0 ]] || die "run this script as root on the Proxmox host"

for command_name in pveversion pvesh pvesm pveam pct qm ip awk grep sed stat install date; do
  require_command "${command_name}"
done

pveversion >/dev/null 2>&1 || die "this host does not report a Proxmox VE version"

require_positive_integer "VMID" "${VMID}"
require_positive_integer "root size" "${ROOT_SIZE_GIB}"
require_positive_integer "data size" "${DATA_SIZE_GIB}"
require_positive_integer "memory" "${MEMORY_MIB}"
require_nonnegative_integer "swap" "${SWAP_MIB}"
require_positive_integer "cores" "${CORES}"
validate_hostname "${CT_HOSTNAME}" || die "invalid hostname: ${CT_HOSTNAME}"
validate_storage_name "${ROOT_STORAGE}" || die "invalid root storage name"
validate_storage_name "${DATA_STORAGE}" || die "invalid data storage name"
validate_bridge_name "${BRIDGE}" || die "invalid bridge name"
validate_image_digest "${IMAGE_REF}" || die "image must be registry/repository@sha256:<64 lowercase hex>"
[[ ${TEMPLATE} =~ ^[A-Za-z0-9._-]+:vztmpl/[A-Za-z0-9._+-]+$ ]] || die "invalid template volume"

read -r -a nameserver_list <<<"${NAMESERVERS}"
((${#nameserver_list[@]} > 0)) || die "at least one nameserver is required"
for nameserver in "${nameserver_list[@]}"; do
  [[ ${nameserver} =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || die "invalid nameserver address: ${nameserver}"
  IFS='.' read -r ns1 ns2 ns3 ns4 <<<"${nameserver}"
  for nameserver_octet in "${ns1}" "${ns2}" "${ns3}" "${ns4}"; do
    ((nameserver_octet >= 0 && nameserver_octet <= 255)) || die "invalid nameserver address: ${nameserver}"
  done
done

BUNDLE_DIR="$(cd -- "${BUNDLE_DIR}" && pwd)" || die "bundle directory not found"

required_bundle_files=(
  owui.compose.yaml
  systemd/open-webui-compose.service
  lib.sh
  validate-deployment.sh
  install-or-update.sh
  health-check.sh
  rollback.sh
)

for bundle_file in "${required_bundle_files[@]}"; do
  [[ -f ${BUNDLE_DIR}/${bundle_file} ]] || die "missing bundle file: ${bundle_file}"
  [[ ! -L ${BUNDLE_DIR}/${bundle_file} ]] || die "bundle file must not be a symlink: ${bundle_file}"
done

vmid_exists() {
  if pvesh get /cluster/resources --type vm --output-format json 2>/dev/null |
    grep -Eq "\"vmid\"[[:space:]]*:[[:space:]]*${VMID}([,}])"; then
    return 0
  fi
  [[ -f /etc/pve/lxc/${VMID}.conf || -f /etc/pve/qemu-server/${VMID}.conf ]]
}

storage_available_kib() {
  local storage=$1
  pvesm status --content rootdir |
    awk -v storage="${storage}" 'NR > 1 && $1 == storage && $3 == "active" {print $6; exit}'
}

require_storage_capacity() {
  local storage=$1
  local required_gib=$2
  local available_kib
  local required_kib=$((required_gib * 1024 * 1024))
  available_kib="$(storage_available_kib "${storage}")"
  [[ ${available_kib} =~ ^[0-9]+$ ]] || die "storage is unavailable or not rootdir-capable: ${storage}"
  ((available_kib >= required_kib)) ||
    die "storage ${storage} has insufficient reported free space for ${required_gib} GiB"
}

STAGE="host preflight"

template_storage=${TEMPLATE%%:*}
pveam list "${template_storage}" | awk 'NR > 1 {print $1}' | grep -Fxq -- "${TEMPLATE}" ||
  die "template is not present: ${TEMPLATE}"

ip link show dev "${BRIDGE}" >/dev/null 2>&1 || die "bridge does not exist: ${BRIDGE}"

if [[ ${ROOT_STORAGE} == "${DATA_STORAGE}" ]]; then
  require_storage_capacity "${ROOT_STORAGE}" "$((ROOT_SIZE_GIB + DATA_SIZE_GIB))"
else
  require_storage_capacity "${ROOT_STORAGE}" "${ROOT_SIZE_GIB}"
  require_storage_capacity "${DATA_STORAGE}" "${DATA_SIZE_GIB}"
fi

mem_available_kib="$(awk '/^MemAvailable:/ {print $2; exit}' /proc/meminfo)"
if [[ ${mem_available_kib} =~ ^[0-9]+$ ]] && ((mem_available_kib < MEMORY_MIB * 1024)); then
  warn "host MemAvailable is below the configured LXC memory limit; stop an approved nonessential guest before starting VMID ${VMID}"
fi

info "preflight inputs"
printf '  VMID: %s\n' "${VMID}"
printf '  hostname: %s\n' "${CT_HOSTNAME}"
printf '  template: %s\n' "${TEMPLATE}"
printf '  root: %s:%s GiB\n' "${ROOT_STORAGE}" "${ROOT_SIZE_GIB}"
printf '  data: %s:%s GiB at /srv/open-webui\n' "${DATA_STORAGE}" "${DATA_SIZE_GIB}"
printf '  bridge: %s (DHCP)\n' "${BRIDGE}"
printf '  nameservers: %s\n' "${NAMESERVERS}"
printf '  resources: %s cores, %s MiB memory, %s MiB swap\n' "${CORES}" "${MEMORY_MIB}" "${SWAP_MIB}"
printf '  image: %s\n' "${IMAGE_REF}"

if ${CHECK_ONLY}; then
  if vmid_exists; then
    warn "VMID ${VMID} already exists"
  else
    info "VMID ${VMID} is currently unused"
  fi
  info "check-only completed; no state was changed"
  exit 0
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_FILE="/root/owui-provision-${VMID}-${timestamp}.evidence"
install -o root -g root -m 0600 /dev/null "${EVIDENCE_FILE}"
record "service=owui"
record "vmid=${VMID}"
record "hostname=${CT_HOSTNAME}"
record "template=${TEMPLATE}"
record "root_storage=${ROOT_STORAGE}"
record "root_size_gib=${ROOT_SIZE_GIB}"
record "data_storage=${DATA_STORAGE}"
record "data_size_gib=${DATA_SIZE_GIB}"
record "bridge=${BRIDGE}"
record "nameservers=${NAMESERVERS}"
record "image=${IMAGE_REF}"
record "started_at=${timestamp}"

validate_existing_config() {
  local config
  local features_line
  local features_value
  config="$(pct config "${VMID}")"

  grep -Fxq "hostname: ${CT_HOSTNAME}" <<<"${config}" || die "existing VMID hostname does not match"
  grep -Fxq "unprivileged: 1" <<<"${config}" || die "existing VMID is not unprivileged"
  grep -Fxq "cores: ${CORES}" <<<"${config}" || die "existing VMID core count does not match"
  grep -Fxq "memory: ${MEMORY_MIB}" <<<"${config}" || die "existing VMID memory does not match"
  grep -Fxq "swap: ${SWAP_MIB}" <<<"${config}" || die "existing VMID swap does not match"
  features_line="$(grep -E '^features:' <<<"${config}")"
  features_value=${features_line#features:}
  features_value=${features_value// /}
  [[ ,${features_value}, == *,keyctl=1,* ]] || die "existing VMID lacks keyctl=1"
  [[ ,${features_value}, == *,nesting=1,* ]] || die "existing VMID lacks nesting=1"
  grep -E "^rootfs: ${ROOT_STORAGE}:.*size=${ROOT_SIZE_GIB}G(,|$)" <<<"${config}" >/dev/null ||
    die "existing VMID root disk does not match"
  grep -E "^mp0: ${DATA_STORAGE}:.*mp=/srv/open-webui(,|$).*size=${DATA_SIZE_GIB}G(,|$)|^mp0: ${DATA_STORAGE}:.*size=${DATA_SIZE_GIB}G(,|$).*mp=/srv/open-webui(,|$)" \
    <<<"${config}" >/dev/null || die "existing VMID managed data volume does not match"
  grep -E "^net0: .*bridge=${BRIDGE}(,|$).*ip=dhcp(,|$)|^net0: .*ip=dhcp(,|$).*bridge=${BRIDGE}(,|$)" \
    <<<"${config}" >/dev/null || die "existing VMID network does not match"
  grep -Fxq "nameserver: ${NAMESERVERS}" <<<"${config}" || die "existing VMID nameservers do not match"

  if grep -Eq '^(dev[0-9]+|lxc\.cgroup|lxc\.mount\.entry):' <<<"${config}"; then
    die "existing VMID contains unexpected device or host passthrough"
  fi
}

if ${RESUME_EXISTING}; then
  vmid_exists || die "--resume-existing requires VMID ${VMID} to exist"
  STAGE="existing LXC validation"
  validate_existing_config
  info "existing VMID ${VMID} matches the recorded infrastructure contract"
  record "creation=resumed"
else
  ${CONFIRM_CREATE} || die "creation requires --confirm-create"
  vmid_exists && die "VMID ${VMID} already exists; use --resume-existing only after inspecting it"
  [[ -t 0 ]] || die "creation confirmation requires an interactive terminal"
  printf 'Type CREATE-%s to create the LXC and allocate its two volumes: ' "${VMID}"
  read -r confirmation
  [[ ${confirmation} == "CREATE-${VMID}" ]] || die "creation confirmation did not match"

  STAGE="LXC creation"
  create_args=(
    create "${VMID}" "${TEMPLATE}"
    --hostname "${CT_HOSTNAME}"
    --arch amd64
    --ostype debian
    --unprivileged 1
    --features nesting=1,keyctl=1
    --cores "${CORES}"
    --memory "${MEMORY_MIB}"
    --swap "${SWAP_MIB}"
    --rootfs "${ROOT_STORAGE}:${ROOT_SIZE_GIB}"
    --mp0 "${DATA_STORAGE}:${DATA_SIZE_GIB},mp=/srv/open-webui,backup=1"
    --net0 "name=eth0,bridge=${BRIDGE},ip=dhcp,type=veth"
    --nameserver "${NAMESERVERS}"
    --onboot 0
    --start 0
    --tags 'owui;phase9;staging'
  )
  pct "${create_args[@]}"
  record "creation=created"

  STAGE="created LXC validation"
  validate_existing_config
  info "created VMID ${VMID} passed configuration validation"
fi

STAGE="LXC startup"
if [[ $(pct status "${VMID}" | awk '{print $2}') != "running" ]]; then
  pct start "${VMID}"
fi

guest_ready=false
for ((attempt = 1; attempt <= 30; attempt++)); do
  if pct exec "${VMID}" -- true >/dev/null 2>&1; then
    guest_ready=true
    break
  fi
  sleep 2
done
${guest_ready} || die "LXC did not become ready within 60 seconds"

if pct exec "${VMID}" -- systemctl is-active --quiet open-webui-compose.service 2>/dev/null; then
  die "OWUI deployment service is already active; use the in-guest update workflow instead"
fi

record "lxc_started=yes"
guest_os="$(pct exec "${VMID}" -- sh -c '. /etc/os-release; printf "%s-%s" "$ID" "$VERSION_ID"')"
record "guest_os=${guest_os}"

STAGE="Docker repository setup"
# Proxmox guest setup must leave /etc traversable by service accounts. An
# earlier rehearsal created it under a restrictive inherited umask, which let
# root resolve DNS while preventing APT's _apt sandbox account from reading
# /etc/resolv.conf.
pct exec "${VMID}" -- chmod 0755 /etc
pct exec "${VMID}" -- chmod 0644 /etc/resolv.conf
pct exec "${VMID}" -- runuser -u _apt -- test -r /etc/resolv.conf ||
  die "the guest _apt account cannot read /etc/resolv.conf"
pct exec "${VMID}" -- runuser -u _apt -- getent ahostsv4 deb.debian.org >/dev/null ||
  die "the guest _apt account cannot resolve deb.debian.org"
pct exec "${VMID}" -- getent ahostsv4 deb.debian.org >/dev/null ||
  die "guest DNS cannot resolve deb.debian.org; verify the configured nameservers before resuming"
pct exec "${VMID}" -- apt-get -o APT::Update::Error-Mode=any update
pct exec "${VMID}" -- apt-get install -y ca-certificates curl coreutils gnupg tar util-linux
pct exec "${VMID}" -- install -m 0755 -d /etc/apt/keyrings
pct exec "${VMID}" -- curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
pct exec "${VMID}" -- chmod a+r /etc/apt/keyrings/docker.asc
pct exec "${VMID}" -- bash -c "printf '%s\n' \
  'Types: deb' \
  'URIs: https://download.docker.com/linux/debian' \
  'Suites: trixie' \
  'Components: stable' \
  'Architectures: amd64' \
  'Signed-By: /etc/apt/keyrings/docker.asc' \
  > /etc/apt/sources.list.d/docker.sources"

STAGE="Docker installation"
pct exec "${VMID}" -- apt-get update
pct exec "${VMID}" -- apt-get install -y \
  docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
pct exec "${VMID}" -- systemctl enable --now docker
pct exec "${VMID}" -- docker version
pct exec "${VMID}" -- docker compose version

docker_packages="$(pct exec "${VMID}" -- dpkg-query -W -f='${Package}=${Version}\n' \
  docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin)"
while IFS= read -r package_line; do
  [[ -n ${package_line} ]] && record "docker_package=${package_line}"
done <<<"${docker_packages}"

root_available_kib="$(pct exec "${VMID}" -- df -Pk / | awk 'NR == 2 {print $4}')"
[[ ${root_available_kib} =~ ^[0-9]+$ ]] || die "could not determine guest root free space"
if ((root_available_kib < 3 * 1024 * 1024)); then
  die "less than 3 GiB remains on the guest root disk after Docker installation; expand rootfs before resuming"
fi
record "root_available_kib_before_pull=${root_available_kib}"

STAGE="registry trust validation"
registry_host=${IMAGE_REF%%/*}
registry_status="$(pct exec "${VMID}" -- curl --silent --show-error --output /dev/null \
  --write-out '%{http_code}' "https://${registry_host}/v2/")"
[[ ${registry_status} == "401" || ${registry_status} == "200" ]] ||
  die "registry trust/API check returned HTTP ${registry_status}"
record "registry_status=${registry_status}"

STAGE="immutable image pull"
pct exec "${VMID}" -- docker pull "${IMAGE_REF}" ||
  die "image pull failed; inspect the Docker error before changing registry authentication"

image_identity="$(pct exec "${VMID}" -- docker image inspect \
  --format '{{.Id}}|{{.Architecture}}|{{.Os}}|{{.Config.User}}' "${IMAGE_REF}")"
IFS='|' read -r image_id image_arch image_os image_user <<<"${image_identity}"
[[ ${image_arch} == "amd64" && ${image_os} == "linux" ]] || die "pulled image platform is not linux/amd64"
[[ ${image_user} == "1000:1000" ]] || die "pulled image user is not 1000:1000"
record "image_id=${image_id}"
record "image_platform=${image_os}/${image_arch}"
record "image_user=${image_user}"

STAGE="deployment bundle installation"
pct exec "${VMID}" -- install -d -o root -g root -m 0755 /etc/open-webui
pct exec "${VMID}" -- install -d -o root -g root -m 0755 /usr/local/lib/owui-deploy
pct exec "${VMID}" -- install -d -o 1000 -g 1000 -m 0750 /srv/open-webui/data

pct push "${VMID}" "${BUNDLE_DIR}/owui.compose.yaml" /etc/open-webui/compose.yaml
pct push "${VMID}" "${BUNDLE_DIR}/systemd/open-webui-compose.service" /etc/systemd/system/open-webui-compose.service
pct push "${VMID}" "${BUNDLE_DIR}/lib.sh" /usr/local/lib/owui-deploy/lib.sh
pct push "${VMID}" "${BUNDLE_DIR}/validate-deployment.sh" /usr/local/lib/owui-deploy/validate-deployment.sh
pct push "${VMID}" "${BUNDLE_DIR}/install-or-update.sh" /usr/local/lib/owui-deploy/install-or-update.sh
pct push "${VMID}" "${BUNDLE_DIR}/health-check.sh" /usr/local/lib/owui-deploy/health-check.sh
pct push "${VMID}" "${BUNDLE_DIR}/rollback.sh" /usr/local/lib/owui-deploy/rollback.sh

pct exec "${VMID}" -- chown root:root \
  /etc/open-webui/compose.yaml /etc/systemd/system/open-webui-compose.service
pct exec "${VMID}" -- chmod 0644 \
  /etc/open-webui/compose.yaml /etc/systemd/system/open-webui-compose.service
pct exec "${VMID}" -- chown -R root:root /usr/local/lib/owui-deploy
pct exec "${VMID}" -- chmod 0444 /usr/local/lib/owui-deploy/lib.sh
pct exec "${VMID}" -- chmod 0555 \
  /usr/local/lib/owui-deploy/validate-deployment.sh \
  /usr/local/lib/owui-deploy/install-or-update.sh \
  /usr/local/lib/owui-deploy/health-check.sh \
  /usr/local/lib/owui-deploy/rollback.sh
pct exec "${VMID}" -- systemctl daemon-reload

if pct exec "${VMID}" -- test -e /etc/open-webui/runtime.env; then
  warn "runtime.env already exists; it was not read, changed, or validated"
  record "runtime_env=preexisting"
else
  record "runtime_env=absent"
fi

data_identity="$(pct exec "${VMID}" -- stat -c '%u:%g:%a' /srv/open-webui/data)"
[[ ${data_identity} == "1000:1000:750" ]] || die "managed data-directory ownership or mode is incorrect"
record "data_identity=${data_identity}"
record "result=prepared"
record "completed_at=$(date -u +%Y%m%dT%H%M%SZ)"

STAGE="complete"
info "LXC ${VMID} is prepared through the runtime-environment stop gate"
info "non-secret evidence: ${EVIDENCE_FILE}"
info "next: record the reserved address and Caddy source, then create root-only runtime.env"
info "OWUI was not started and Caddy/DNS were not changed"
