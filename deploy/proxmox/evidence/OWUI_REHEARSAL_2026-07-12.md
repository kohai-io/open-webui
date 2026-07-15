# OWUI Proxmox rehearsal evidence

Recorded on 2026-07-12 for the disposable Phase 9 OWUI rehearsal. This file
contains no credentials or resolved runtime environment values.

## Proxmox target

- Node: `pve2`
- Proxmox VE: `8.4.19`
- Kernel: `6.8.12-23-pve`
- Architecture: `x86_64`
- Approved disposable OWUI VMID: `105`
- Hostname: `owui-staging`
- Bridge: `vmbr0`
- Initial addressing: DHCP, followed by a UniFi DHCP reservation
- Revised root disk: `local-lvm`, 24 GiB
- Revised managed data volume: `local-lvm`, 16 GiB, mounted at
  `/srv/open-webui`
- Debian template present locally:
  `debian-13-standard_13.1-2_amd64.tar.zst`
- Proxmox firewall state at capture: disabled
- Rehearsal firewall decision: no additional firewall in the local homelab
- Caddy staging name: `owui-stage.theoldschool.house`
- LXC DNS resolvers: `10.100.1.21` and `10.100.1.22`
- Runtime secret file: root-owned `/etc/open-webui/runtime.env`, mode `0600`
- Off-LXC backup target: none selected for the initial bootstrap test
- Legacy rollback LXC: `106`; preserve it unchanged through rollback rehearsal
- Upstream-reference LXC: `118`; it is not the legacy routing rollback target

The final DHCP-reserved address, Caddy source address, model and OAuth
integration names, and runtime secret-reference inventory remain to be
recorded before the first OWUI deployment.

The lack of an off-LXC backup target and unrestricted local homelab ingress
make this an initial bootstrap-feasibility rehearsal. They do not satisfy the
complete Phase 9 backup/restore or network-policy acceptance gates.

The first provisioning attempt created and validated LXC `105`, then stopped
safely during Docker repository setup because the guest could not resolve
Debian package hosts. No Docker package, deployment bundle, runtime secret, or
OWUI service was installed. The provisioner now configures the two recorded
homelab resolvers explicitly and checks DNS before invoking APT.

The operator subsequently deleted the incomplete LXC `105`. It contained no
application database, runtime secret, or accepted rehearsal evidence. Before
recreation, verify that VMID `105` and both former `vm-105-disk-*` logical
volumes are absent. Recreate only from the latest corrected bundle.

The recreated LXC had working network reachability and root-level DNS, but APT
could not resolve package hosts. The host provisioner's global mode `077`
umask was inherited by Proxmox guest setup, leaving the `/etc` directory mode
`0700`. Although `/etc/resolv.conf` itself was mode `0644`, APT's unprivileged
`_apt` downloader could not traverse `/etc` to read it. Resolution as root and
an APT update with `APT::Sandbox::User=root` both succeeded, confirming the
failure boundary. The provisioner now uses a normal system-file umask,
normalizes `/etc` to mode `0755`, verifies resolver readability and DNS as
`_apt`, and makes APT repository-update warnings fatal. Sensitive evidence
files remain explicitly mode `0600`.

After Docker installation succeeded, extraction of the pinned OWUI image
failed with `no space left on device` under `/var/lib/docker` on the 8 GiB
root filesystem. No OWUI service or application data was created. The
provisioner incorrectly treated every image-pull failure as a possible
authentication failure and prompted for a registry login before retrying the
same disk-full pull. That fallback has been removed: image-pull failures now
stop without changing authentication state so the reported cause can be
addressed directly. The operator approved recreating the disposable LXC with
a 24 GiB root disk and 16 GiB managed data volume. This preserves the same 40
GiB total allocation while keeping replaceable Docker layers separate from
OWUI application data.

The replacement LXC completed the reviewed provisioner through the
runtime-environment stop gate. Docker Engine and Compose were installed, the
pinned OWUI image was pulled and checked, and the deployment bundle and
managed data directory were prepared. The provisioner stopped without
creating runtime secrets, starting OWUI, or changing Caddy or DNS. Its
non-secret host evidence record is
`/root/owui-provision-105-20260712T145547Z.evidence`. Compose, systemd startup,
local health, proxy routing, backup/restore, and rollback remain unproved.

After recreation, LXC `105` received DHCP address `10.100.1.103/24` with MAC
`BC:24:11:B0:A4:9C`; that address persisted across an LXC reboot. UniFi still
showed `10.100.1.146`, which had been associated with the earlier disposable
LXC instance and its different MAC. Treat the reserved address as unresolved
until UniFi's reservation is bound to the replacement MAC and the selected
address is observed from inside the LXC after renewal.

The replacement LXC address is `10.100.1.103/24`. From the Caddy host,
`ip -4 route get 10.100.1.103` selected source address `10.100.1.20`; use that
single address for `FORWARDED_ALLOW_IPS`. The public staging name remains
`owui-stage.theoldschool.house`.

The first digest deployment completed successfully at release record
`/var/backups/open-webui-deploy/releases/20260712T150852Z.8lqGqJ`. Early local
health probes received connection resets while OWUI initialized; continued
polling subsequently passed. The independent service health command passed,
`systemctl is-active open-webui-compose.service` returned `active`, and
`http://127.0.0.1:8080/health` returned `{"status":true}`. The unit was then
enabled for boot. No runtime environment values were captured. Caddy/DNS,
authenticated application behavior, provider behavior, reboot persistence,
backup/restore, update, and rollback remain to be proved.

The operator subsequently confirmed that the Caddy/DNS path was working and
that the deployed OWUI UI displayed the expected welcome page at the staging
site. This proves delivery of the maintained welcome-page build through the
selected reverse-proxy route. No browser session data or credentials were
captured. Provider behavior, explicit post-reboot service evidence,
backup/restore, update, and rollback remain separate gates unless recorded
below.

## OWUI source and build

- Source repository: `https://git.theoldschool.house/robert/open-webui`
- Branch: `rebaseline/upstream-v0.10.2`
- Revision: `6dca01731e6d38aca8b2b7094e409c306ce78936`
- Source state at build: clean and synchronized with its configured upstream
- Builder: Docker Desktop `desktop-linux`
- Docker Engine: `29.6.1`
- Buildx: `0.35.0-desktop.2`
- Target platform: `linux/amd64`
- Runtime UID/GID: `1000:1000`
- Build hash: full source revision
- Build timestamp: `2026-07-12T09:39:14.750831056Z`
- Base image: `node:22-alpine3.20@sha256:2289fb1fba0f4633b08ec47b94a89c7e20b829fc5679f9b7b298eaa2f1ed8b7e`
- Base image: `python:3.11-slim-bookworm@sha256:f5cf0344c9886ff24d34797578d5d7dd6e8911ae0fe5962bb55d0f89603ec361`
- Dockerfile frontend:
  `docker/dockerfile:1@sha256:87999aa3d42bdc6bea60565083ee17e86d1f3339802f543c0d03998580f9cb89`

The image carries these OCI labels:

- `org.opencontainers.image.source=https://git.theoldschool.house/robert/open-webui`
- `org.opencontainers.image.revision=6dca01731e6d38aca8b2b7094e409c306ce78936`

## Published artifact

- Published tag:
  `git.theoldschool.house/robert/open-webui:6dca01731e6d38aca8b2b7094e409c306ce78936`
- Deployment reference:
  `git.theoldschool.house/robert/open-webui@sha256:012e5f80e9aaf508c5831fde9440a78fea3b7ff2f4b2a8ca451758e904e696c9`
- OCI index digest:
  `sha256:012e5f80e9aaf508c5831fde9440a78fea3b7ff2f4b2a8ca451758e904e696c9`
- Linux amd64 manifest digest:
  `sha256:8943412db6b612dd8cbc5f5784d170a9a2e3e3ac91709998af5e46db80a138a3`
- Provenance attestation manifest:
  `sha256:18cd47313e962eaae3383a5a1dc46a8b500bdbbddb3a2b3c219d1026b0a2f057`
- Local image size: `1782010295` bytes

The push output and an independent `docker buildx imagetools inspect` both
reported the same OCI index digest. Deployment must use the digest reference,
not the tag.

## Local validation

- Configured runtime identity: `1000:1000`
- `/app/backend/data` ownership: `1000:1000`
- `/app/backend/data` mode: `0755`
- Disposable empty-data container reached Docker health `healthy`
- `GET /health` returned HTTP 200 with `{"status":true}`
- The disposable smoke container was stopped and automatically removed
- The source worktree remained clean after the build

## Evidence not yet established

The image has not yet been pulled or run on Proxmox. Compose v2, systemd,
registry trust inside the LXC, managed-volume ownership, backup, restore,
update, rollback, Caddy routing, public-origin health, and acceptance checks
remain pending. Do not use this build record as evidence that those checks
pass.

## Continuation evidence, 2026-07-12

This section supersedes the earlier point-in-time statement immediately above
where later evidence is recorded. It contains no user identity, prompt,
response, credential, cookie, token, or resolved runtime environment value.

### Public OWUI acceptance flags

- `GET https://owui-stage.theoldschool.house/health` returned HTTP `200`.
- The public `/api/config` response reported version `0.10.2`, application
  status true, authentication enabled, login form enabled, and public signup
  disabled.
- The public response omitted the `onboarding` property. In v0.10.2 that
  property is emitted only when the unauthenticated request observes zero
  users. The supported first signup assigns the first user the administrator
  role and immediately persists `ENABLE_SIGNUP=false`.
- Result: first-administrator creation **pass by supported-path inference**;
  automatic public-signup closure **pass**.
- LiteLLM model discovery and one authenticated chat remain **open**. No
  authenticated session, identity, model list, prompt, or response was
  inspected or recorded.

The operator subsequently reported LiteLLM models were visible and one
authenticated OWUI chat completed successfully. No model name, prompt,
response, identity, credential, cookie, or token was recorded.

Result: LiteLLM model discovery and one authenticated chat **pass by operator
report**. Together with the previously recorded first administrator, automatic
signup closure, reboot persistence, systemd state, and public/local health,
the initial OWUI acceptance gates requested for this continuation pass.

### Proxmox access and operator-verified host checks

- Homelab DNS resolved `pve2.theoldschool.house` to `10.100.1.20`.
- The workstation had no trusted SSH host-key entry for that address. An
  unauthenticated key scan reported ED25519 fingerprint
  `SHA256:X17bOqc3nLcK1ZtC38BjZSZybBDdC7Jw/2eh5x6HWig`.
- Host-key checking was not bypassed and the key was not added. The fingerprint
  was not needed after the operator elected to perform the host checks directly.
- The operator subsequently reported manual verification of the `local-lvm`
  thin-pool capacity review, LXC `105` configuration, `mp0` backup inclusion,
  successful LXC reboot persistence, enabled and active OWUI systemd service
  after reboot, and passing guest-local health.
- Result: host-capacity review, managed-volume backup flag, LXC reboot
  persistence, post-reboot systemd state, and guest-local health **pass by
  operator report**. Public health independently returned HTTP `200`.
- Available Proxmox backup targets were reviewed manually, but no specific
  off-LXC target, backup artifact, or restore result was recorded. The
  backup/restore acceptance gate therefore remains **open**.

### Controlled OWUI backup, update, and rollback rehearsal

The rehearsal is prepared but has not been executed. Use this order:

1. Verify and trust the Proxmox SSH host key through a trusted channel.
2. Record `local-lvm` data and metadata usage and the effective
   `thin_pool_autoextend_threshold` and `thin_pool_autoextend_percent`. Do not
   allocate Studio storage until capacity is accepted.
3. Select an off-LXC Proxmox backup target with enough capacity and a recorded
   retention class. Confirm LXC `105` has `mp0` with `backup=1`.
4. Take a stopped or snapshot-mode `vzdump` of LXC `105` to that target and
   record the non-secret archive path, size, duration, checksum, and included
   volume list. A local release archive does not satisfy this step.
5. Build a documented no-op OWUI candidate from the approved maintained source
   and obtain fresh explicit approval before publishing it. Record the new,
   distinct immutable registry digest. Do not redeploy the current digest.
6. Enter proxy maintenance mode. Run the reviewed `install-or-update.sh` for
   the distinct candidate digest. Record pull, stopped-service archive,
   migration, health, and total interruption times; verify the archive
   checksum and public health.
7. Treat the healthy candidate as deliberately rejected for the rollback
   exercise. Record its release directory and verify it names the current
   deployed digest as `previous-image` without printing configuration.
8. Stop and obtain fresh explicit approval immediately before invoking
   `rollback.sh ... --confirm-restore-data`, because it replaces staging data.
9. After approval, run the checksum-verified rollback. Verify the previous
   digest and paired data, the preserved `failed-data-*` candidate directory,
   local health, public health, model discovery, and one authenticated chat.
10. A later restore rehearsal of the off-LXC `vzdump` must also receive fresh
    explicit approval before it overwrites staging. Only that successful,
    recorded restore can pass the backup/restore gate.

No update, rollback, or restore gate is marked passed by this preparation.

The operator later elected to park off-LXC backup and restore work. No backup
or restore command was run, and the acceptance gate remains open. Fresh
explicit approval is still required immediately before any restore that
overwrites staging data.

### Studio source and local artifact preparation

- The broken `C:\tmp\open-webui-studio-flows` worktree could not be repaired
  because its parent repository metadata was absent.
- A fresh clone was detached at exact published commit
  `bf7dd04aca6a96aaaae13c4cbb21a3d464660af2`. The checkout is clean.
- The previous broken directory is retained at
  `C:\tmp\open-webui-studio-flows-broken-20260712`.
- Pinned Node `22.17.0` static checks passed with zero errors and warnings.
- All `130` Studio server tests passed across `25` test files.
- The Docker build used `node:22.17.0-alpine` at base digest
  `sha256:fc3e945f920b7e3000cd1af86c4ae406ec70c72f328b667baf0f3a8910d69eed`.
- Local image ID/index:
  `sha256:9bbb5752adb54718df8cc00aaef746aed8629d4be558f1af34e586ccf4612462`;
  architecture `linux/amd64`; configured user `studio`; size `62,980,708`
  bytes; OCI revision label matches the full published commit.
- Local runtime smoke returned only status `ok`, service
  `open-webui-studio`, and version `0.0.1`. Runtime UID/GID was `100:101`; the
  image-owned `/app/data` was `100:101` mode `0755`. The smoke container was
  removed.
- After fresh explicit operator approval, the exact validated image was pushed
  as
  `git.theoldschool.house/robert/open-webui-studio:bf7dd04aca6a96aaaae13c4cbb21a3d464660af2`.
- The push and an independent registry inspection both reported OCI index
  digest
  `sha256:9bbb5752adb54718df8cc00aaef746aed8629d4be558f1af34e586ccf4612462`.
- The deployable immutable reference is
  `git.theoldschool.house/robert/open-webui-studio@sha256:9bbb5752adb54718df8cc00aaef746aed8629d4be558f1af34e586ccf4612462`.
- The `linux/amd64` image manifest is
  `sha256:fba9290f49fe922d338b9987a5df95f9e1943a16631eda053c3f45ac2efef949`.
  The provenance attestation manifest is
  `sha256:7601e72eb04c5ede95fb4db9a2a32152eb56de03e9a2a0321e34a470a2c19165`.
- Studio image publication **passes**. LXC provisioning, proxy routing,
  bootstrap, Flow recovery, backup, update, rollback, and restore gates remain
  **open**.
