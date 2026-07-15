#!/usr/bin/env bash
set -Eeuo pipefail

# Proxmox guest setup inherits this process umask. Keep normal system-file
# permissions; the evidence file is explicitly created as mode 0600.
umask 022

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

VMID=107
CT_HOSTNAME="studio-staging"
TEMPLATE="local:vztmpl/debian-13-standard_13.1-2_amd64.tar.zst"
ROOT_STORAGE="local-lvm"
ROOT_SIZE_GIB=12
DATA_STORAGE="local-lvm"
DATA_SIZE_GIB=8
BRIDGE="vmbr0"
NAMESERVERS="10.100.1.21 10.100.1.22"
MEMORY_MIB=4096
SWAP_MIB=512
CORES=2
IMAGE_REF="git.theoldschool.house/robert/open-webui-studio@sha256:9bbb5752adb54718df8cc00aaef746aed8629d4be558f1af34e586ccf4612462"
BUNDLE_DIR="${SCRIPT_DIR}"

CHECK_ONLY=false
CONFIRM_CREATE=false
RESUME_EXISTING=false
STAGE="initialization"
EVIDENCE_FILE=""

usage() {
  cat <<'EOF'
Usage: provision-studio-lxc.sh [options]

Creates and prepares the recorded Studio LXC on a Proxmox host. The script
installs Docker, pulls the approved image digest, and installs the reviewed
deployment bundle. It does not create runtime.env, start Studio, change OWUI
OAuth, change Caddy/DNS, stop another guest, or delete anything.

Options:
  --check-only              Validate host, inputs, capacity, and VMID availability
  --confirm-create          Permit creation after typing CREATE-107
  --resume-existing         Resume only after validating an existing VMID 107
  --bundle-dir PATH         Reviewed deploy/proxmox directory
  -h, --help                Show this help

First run:
  ./provision-studio-lxc.sh --check-only
  ./provision-studio-lxc.sh --confirm-create

After a partial failure:
  ./provision-studio-lxc.sh --resume-existing

If the immutable pull reports an authorization failure, run an interactive
docker login inside LXC 107, then use --resume-existing. Never put a registry
credential on the command line.
EOF
}

info() { printf '[studio-provision] %s\n' "$*"; }
warn() { printf '[studio-provision] WARNING: %s\n' "$*" >&2; }
die() { printf '[studio-provision] ERROR: %s\n' "$*" >&2; exit 1; }
record() { [[ -z ${EVIDENCE_FILE} ]] || printf '%s\n' "$*" >>"${EVIDENCE_FILE}"; }

on_error() {
  local exit_code=$?
  printf '[studio-provision] ERROR: failed during stage "%s" at line %s (exit %s).\n' \
    "${STAGE}" "${BASH_LINENO[0]:-unknown}" "${exit_code}" >&2
  printf '[studio-provision] No automatic cleanup was attempted. Inspect VMID %s before resuming.\n' \
    "${VMID}" >&2
  record "result=failed"
  record "failed_stage=${STAGE}"
  exit "${exit_code}"
}
trap on_error ERR

require_command() { command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"; }

while (($# > 0)); do
  case "$1" in
    --check-only) CHECK_ONLY=true; shift ;;
    --confirm-create) CONFIRM_CREATE=true; shift ;;
    --resume-existing) RESUME_EXISTING=true; shift ;;
    --bundle-dir)
      [[ $# -ge 2 ]] || die "--bundle-dir requires a value"
      BUNDLE_DIR=$2
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
done

[[ ${EUID} -eq 0 ]] || die "run this script as root on the Proxmox host"
for command_name in pveversion pvesh pvesm pveam pct ip awk grep install date; do
  require_command "${command_name}"
done
pveversion >/dev/null 2>&1 || die "this host does not report a Proxmox VE version"
[[ ${IMAGE_REF} =~ ^[^[:space:]@]+@sha256:[a-f0-9]{64}$ ]] || die "invalid immutable image reference"

BUNDLE_DIR="$(cd -- "${BUNDLE_DIR}" && pwd)" || die "bundle directory not found"
required_bundle_files=(
  studio.compose.yaml
  systemd/open-webui-studio-compose.service
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
  pvesm status --content rootdir |
    awk -v storage="$1" 'NR > 1 && $1 == storage && $3 == "active" {print $6; exit}'
}

require_capacity() {
  local storage=$1 required_gib=$2 available_kib
  available_kib="$(storage_available_kib "${storage}")"
  [[ ${available_kib} =~ ^[0-9]+$ ]] || die "storage is unavailable or not rootdir-capable: ${storage}"
  ((available_kib >= required_gib * 1024 * 1024)) ||
    die "storage ${storage} has insufficient reported free space for ${required_gib} GiB"
}

validate_existing_config() {
  local config features features_value mp0 rootfs net0
  config="$(pct config "${VMID}")"
  grep -Fxq "hostname: ${CT_HOSTNAME}" <<<"${config}" || die "existing VMID hostname does not match"
  grep -Fxq "unprivileged: 1" <<<"${config}" || die "existing VMID is not unprivileged"
  grep -Fxq "cores: ${CORES}" <<<"${config}" || die "existing VMID core count does not match"
  grep -Fxq "memory: ${MEMORY_MIB}" <<<"${config}" || die "existing VMID memory does not match"
  grep -Fxq "swap: ${SWAP_MIB}" <<<"${config}" || die "existing VMID swap does not match"
  features="$(grep -E '^features:' <<<"${config}")"
  features_value=${features#features:}
  features_value=${features_value// /}
  [[ ,${features_value}, == *,keyctl=1,* ]] || die "existing VMID lacks keyctl=1"
  [[ ,${features_value}, == *,nesting=1,* ]] || die "existing VMID lacks nesting=1"
  rootfs="$(grep -E '^rootfs:' <<<"${config}")"
  [[ ${rootfs} == *"${ROOT_STORAGE}:"* && ${rootfs} == *"size=${ROOT_SIZE_GIB}G"* ]] ||
    die "existing VMID root disk does not match"
  mp0="$(grep -E '^mp0:' <<<"${config}")"
  [[ ${mp0} == *"${DATA_STORAGE}:"* && ${mp0} == *"mp=/srv/open-webui-studio"* &&
     ${mp0} == *"size=${DATA_SIZE_GIB}G"* && ${mp0} == *"backup=1"* ]] ||
    die "existing VMID managed data volume does not match"
  net0="$(grep -E '^net0:' <<<"${config}")"
  [[ ${net0} == *"bridge=${BRIDGE}"* && ${net0} == *"ip=dhcp"* ]] ||
    die "existing VMID network does not match"
  grep -Fxq "nameserver: ${NAMESERVERS}" <<<"${config}" || die "existing VMID nameservers do not match"
  if grep -Eq '^(dev[0-9]+|lxc\.cgroup|lxc\.mount\.entry):' <<<"${config}"; then
    die "existing VMID contains unexpected device or host passthrough"
  fi
}

STAGE="host preflight"
pveam list "${TEMPLATE%%:*}" | awk 'NR > 1 {print $1}' | grep -Fxq -- "${TEMPLATE}" ||
  die "template is not present: ${TEMPLATE}"
ip link show dev "${BRIDGE}" >/dev/null 2>&1 || die "bridge does not exist: ${BRIDGE}"
require_capacity "${ROOT_STORAGE}" "$((ROOT_SIZE_GIB + DATA_SIZE_GIB))"

info "preflight inputs"
printf '  VMID: %s\n  hostname: %s\n  template: %s\n' "${VMID}" "${CT_HOSTNAME}" "${TEMPLATE}"
printf '  root: %s:%s GiB\n  data: %s:%s GiB at /srv/open-webui-studio\n' \
  "${ROOT_STORAGE}" "${ROOT_SIZE_GIB}" "${DATA_STORAGE}" "${DATA_SIZE_GIB}"
printf '  bridge: %s (DHCP)\n  nameservers: %s\n' "${BRIDGE}" "${NAMESERVERS}"
printf '  resources: %s cores, %s MiB memory, %s MiB swap\n' "${CORES}" "${MEMORY_MIB}" "${SWAP_MIB}"
printf '  image: %s\n' "${IMAGE_REF}"

if ${CHECK_ONLY}; then
  vmid_exists && warn "VMID ${VMID} already exists" || info "VMID ${VMID} is currently unused"
  info "check-only completed; no state was changed"
  exit 0
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_FILE="/root/studio-provision-${VMID}-${timestamp}.evidence"
install -o root -g root -m 0600 /dev/null "${EVIDENCE_FILE}"
for item in \
  "service=studio" "vmid=${VMID}" "hostname=${CT_HOSTNAME}" "template=${TEMPLATE}" \
  "root_storage=${ROOT_STORAGE}" "root_size_gib=${ROOT_SIZE_GIB}" \
  "data_storage=${DATA_STORAGE}" "data_size_gib=${DATA_SIZE_GIB}" \
  "bridge=${BRIDGE}" "nameservers=${NAMESERVERS}" "image=${IMAGE_REF}" "started_at=${timestamp}"; do
  record "${item}"
done

if ${RESUME_EXISTING}; then
  vmid_exists || die "--resume-existing requires VMID ${VMID} to exist"
  STAGE="existing LXC validation"
  validate_existing_config
  record "creation=resumed"
else
  ${CONFIRM_CREATE} || die "creation requires --confirm-create"
  vmid_exists && die "VMID ${VMID} already exists; inspect it before using --resume-existing"
  [[ -t 0 ]] || die "creation confirmation requires an interactive terminal"
  printf 'Type CREATE-%s to create the LXC and allocate its two volumes: ' "${VMID}"
  read -r confirmation
  [[ ${confirmation} == "CREATE-${VMID}" ]] || die "creation confirmation did not match"
  STAGE="LXC creation"
  pct create "${VMID}" "${TEMPLATE}" \
    --hostname "${CT_HOSTNAME}" --arch amd64 --ostype debian --unprivileged 1 \
    --features nesting=1,keyctl=1 --cores "${CORES}" --memory "${MEMORY_MIB}" \
    --swap "${SWAP_MIB}" --rootfs "${ROOT_STORAGE}:${ROOT_SIZE_GIB}" \
    --mp0 "${DATA_STORAGE}:${DATA_SIZE_GIB},mp=/srv/open-webui-studio,backup=1" \
    --net0 "name=eth0,bridge=${BRIDGE},ip=dhcp,type=veth" --nameserver "${NAMESERVERS}" \
    --onboot 0 --start 0 --tags 'studio;phase9;staging'
  record "creation=created"
  STAGE="created LXC validation"
  validate_existing_config
fi

STAGE="LXC startup"
[[ $(pct status "${VMID}" | awk '{print $2}') == running ]] || pct start "${VMID}"
guest_ready=false
for ((attempt=1; attempt<=30; attempt++)); do
  if pct exec "${VMID}" -- true >/dev/null 2>&1; then guest_ready=true; break; fi
  sleep 2
done
${guest_ready} || die "LXC did not become ready within 60 seconds"
if pct exec "${VMID}" -- systemctl is-active --quiet open-webui-studio-compose.service 2>/dev/null; then
  die "Studio is already active; use the in-guest update workflow instead"
fi
record "lxc_started=yes"
record "guest_os=$(pct exec "${VMID}" -- sh -c '. /etc/os-release; printf "%s-%s" "$ID" "$VERSION_ID"')"

STAGE="Docker installation"
pct exec "${VMID}" -- chmod 0755 /etc
pct exec "${VMID}" -- chmod 0644 /etc/resolv.conf
pct exec "${VMID}" -- runuser -u _apt -- test -r /etc/resolv.conf || die "_apt cannot read resolv.conf"
pct exec "${VMID}" -- runuser -u _apt -- getent ahostsv4 deb.debian.org >/dev/null || die "_apt DNS failed"
pct exec "${VMID}" -- apt-get -o APT::Update::Error-Mode=any update
pct exec "${VMID}" -- apt-get install -y ca-certificates curl coreutils gnupg tar util-linux
pct exec "${VMID}" -- install -m 0755 -d /etc/apt/keyrings
pct exec "${VMID}" -- curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
pct exec "${VMID}" -- chmod a+r /etc/apt/keyrings/docker.asc
pct exec "${VMID}" -- bash -c "printf '%s\n' 'Types: deb' 'URIs: https://download.docker.com/linux/debian' 'Suites: trixie' 'Components: stable' 'Architectures: amd64' 'Signed-By: /etc/apt/keyrings/docker.asc' > /etc/apt/sources.list.d/docker.sources"
pct exec "${VMID}" -- apt-get -o APT::Update::Error-Mode=any update
pct exec "${VMID}" -- apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
pct exec "${VMID}" -- systemctl enable --now docker
pct exec "${VMID}" -- docker version
pct exec "${VMID}" -- docker compose version

root_available_kib="$(pct exec "${VMID}" -- df -Pk / | awk 'NR == 2 {print $4}')"
[[ ${root_available_kib} =~ ^[0-9]+$ ]] || die "could not determine guest root free space"
((root_available_kib >= 3 * 1024 * 1024)) || die "less than 3 GiB remains on guest root before pull"
record "root_available_kib_before_pull=${root_available_kib}"

STAGE="registry and immutable image validation"
registry_host=${IMAGE_REF%%/*}
registry_status="$(pct exec "${VMID}" -- curl --silent --show-error --output /dev/null --write-out '%{http_code}' "https://${registry_host}/v2/")"
[[ ${registry_status} == 401 || ${registry_status} == 200 ]] || die "registry API returned HTTP ${registry_status}"
record "registry_status=${registry_status}"
pct exec "${VMID}" -- docker pull "${IMAGE_REF}" ||
  die "image pull failed; if authorization is required, run an interactive docker login inside LXC ${VMID}, then resume"

image_identity="$(pct exec "${VMID}" -- docker image inspect --format '{{.Id}}|{{.Architecture}}|{{.Os}}|{{.Config.User}}' "${IMAGE_REF}")"
IFS='|' read -r image_id image_arch image_os image_user <<<"${image_identity}"
[[ ${image_arch} == amd64 && ${image_os} == linux ]] || die "pulled image platform is not linux/amd64"
[[ ${image_user} == studio ]] || die "pulled image user is not studio"
numeric_identity="$(pct exec "${VMID}" -- docker run --rm --entrypoint sh "${IMAGE_REF}" -c 'printf "%s:%s:%s" "$(id -u)" "$(id -g)" "$(stat -c %a /app/data)"')"
[[ ${numeric_identity} == 100:101:755 ]] || die "image runtime identity or /app/data mode does not match"
record "image_id=${image_id}"
record "image_platform=${image_os}/${image_arch}"
record "image_user=${image_user}"
record "image_numeric_identity=${numeric_identity}"

STAGE="deployment bundle installation"
pct exec "${VMID}" -- install -d -o root -g root -m 0755 /etc/open-webui-studio
pct exec "${VMID}" -- install -d -o root -g root -m 0755 /usr/local/lib/owui-deploy
pct exec "${VMID}" -- install -d -o 100 -g 101 -m 0750 /srv/open-webui-studio/data
pct push "${VMID}" "${BUNDLE_DIR}/studio.compose.yaml" /etc/open-webui-studio/compose.yaml
pct push "${VMID}" "${BUNDLE_DIR}/systemd/open-webui-studio-compose.service" /etc/systemd/system/open-webui-studio-compose.service
for script in lib.sh validate-deployment.sh install-or-update.sh health-check.sh rollback.sh; do
  pct push "${VMID}" "${BUNDLE_DIR}/${script}" "/usr/local/lib/owui-deploy/${script}"
done
pct exec "${VMID}" -- chown root:root /etc/open-webui-studio/compose.yaml /etc/systemd/system/open-webui-studio-compose.service
pct exec "${VMID}" -- chmod 0644 /etc/open-webui-studio/compose.yaml /etc/systemd/system/open-webui-studio-compose.service
pct exec "${VMID}" -- chown -R root:root /usr/local/lib/owui-deploy
pct exec "${VMID}" -- chmod 0444 /usr/local/lib/owui-deploy/lib.sh
pct exec "${VMID}" -- chmod 0555 /usr/local/lib/owui-deploy/validate-deployment.sh /usr/local/lib/owui-deploy/install-or-update.sh /usr/local/lib/owui-deploy/health-check.sh /usr/local/lib/owui-deploy/rollback.sh
pct exec "${VMID}" -- systemctl daemon-reload

if pct exec "${VMID}" -- test -e /etc/open-webui-studio/runtime.env; then
  warn "runtime.env already exists; it was not read, changed, or validated"
  record "runtime_env=preexisting"
else
  record "runtime_env=absent"
fi
data_identity="$(pct exec "${VMID}" -- stat -c '%u:%g:%a' /srv/open-webui-studio/data)"
[[ ${data_identity} == 100:101:750 ]] || die "managed data-directory ownership or mode is incorrect"
record "data_identity=${data_identity}"
record "result=prepared"
record "completed_at=$(date -u +%Y%m%dT%H%M%SZ)"

STAGE="complete"
info "LXC ${VMID} is prepared through the runtime and identity stop gate"
info "non-secret evidence: ${EVIDENCE_FILE}"
info "Studio was not started; runtime.env, OWUI OAuth, Caddy, and DNS were not changed"
