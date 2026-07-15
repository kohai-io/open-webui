# Studio LXC preparation runbook

This runbook prepares the Phase 9 Studio LXC on `pve2`. It stops before
creating `/etc/open-webui-studio/runtime.env`, starting Studio, changing OWUI
OAuth configuration, or changing Caddy. Run the Proxmox commands as `root` on
`pve2` and the guest commands as `root` inside LXC `107`.

Do not print registry credentials, OIDC client secrets, session keys, tokens,
cookies, or resolved runtime environments. Do not run the Proxmox Community
Scripts installer. Keep LXC `105`, legacy LXC `106`, and reference LXC `118`
unchanged.

## Recorded inputs

- Node: `pve2`, Proxmox VE `8.4.19`
- VMID: `107` (operator confirmed available)
- Hostname: `studio-staging`
- Template: `local:vztmpl/debian-13-standard_13.1-2_amd64.tar.zst`
- CPU and memory: 2 vCPU, 4096 MiB RAM, 512 MiB swap
- Root disk: `local-lvm`, 12 GiB
- Managed data volume: `local-lvm`, 8 GiB at `/srv/open-webui-studio`
- Network: DHCP on `vmbr0`, followed by a UniFi DHCP reservation
- Reserved address: `10.100.1.128/24`, observed again after LXC reboot
- MAC: `BC:24:11:76:5A:C5`
- DNS resolvers: `10.100.1.21` and `10.100.1.22`
- Caddy source: `10.100.1.20`
- Public origin: `https://owui-stage.theoldschool.house`
- OWUI internal address: `http://10.100.1.103:8080`
- Identity provider: existing Keycloak realm `homelab`
- Keycloak issuer: `https://auth.theoldschool.house/realms/homelab`
- Dedicated Studio client ID: `studio-staging`
- Published Studio image:
  `git.theoldschool.house/robert/open-webui-studio@sha256:9bbb5752adb54718df8cc00aaef746aed8629d4be558f1af34e586ccf4612462`
- Linux/amd64 manifest:
  `sha256:fba9290f49fe922d338b9987a5df95f9e1943a16631eda053c3f45ac2efef949`
- Container UID/GID: `100:101`

The operator reported that `local-lvm` capacity was reviewed and accepted
before this allocation. The complete backup/restore gate remains open until a
named off-LXC target is selected and restored successfully.

## Preferred scripted path

The reviewed host-side provisioner automates sections 1 through 6 and stops at
the same gate before runtime secrets, Studio startup, OWUI OAuth, or Caddy:

```bash
chmod 0555 /root/studio-proxmox-bundle/provision-studio-lxc.sh
/root/studio-proxmox-bundle/provision-studio-lxc.sh --check-only
/root/studio-proxmox-bundle/provision-studio-lxc.sh --confirm-create
```

The creation command requires the operator to type `CREATE-107`. If a later
stage fails after the LXC exists, inspect the reported stage and VMID, resolve
the cause, and resume with:

```bash
/root/studio-proxmox-bundle/provision-studio-lxc.sh --resume-existing
```

Resume validates the existing hostname, resources, storage, network,
unprivileged state, required features, backup inclusion, and absence of device
passthrough. It never deletes or recreates the guest. If the immutable image
pull needs authentication, run `docker login git.theoldschool.house`
interactively inside LXC `107`, then resume; never put a credential on the
command line.

The remaining sections are the manual audit trail and fallback procedure.

## 1. Read-only preflight on pve2

Run each command separately:

```bash
pveversion
pct list
pveam list local
pvesm status --content rootdir
free -h
```

Confirm VMID `107` is absent, the Debian 13 template and `local-lvm` are
available, and the accepted capacity observation still holds. Stop if VMID
`107` exists or capacity has materially changed.

## 2. Create the stopped unprivileged LXC

```bash
pct create 107 local:vztmpl/debian-13-standard_13.1-2_amd64.tar.zst \
  --hostname studio-staging \
  --arch amd64 \
  --ostype debian \
  --unprivileged 1 \
  --features nesting=1,keyctl=1 \
  --cores 2 \
  --memory 4096 \
  --swap 512 \
  --rootfs local-lvm:12 \
  --mp0 local-lvm:8,mp=/srv/open-webui-studio,backup=1 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp,type=veth \
  --nameserver '10.100.1.21 10.100.1.22' \
  --onboot 0 \
  --start 0 \
  --tags 'studio;phase9;staging'
```

Verify before starting:

```bash
pct config 107
```

Required evidence:

- `unprivileged: 1`
- `features: keyctl=1,nesting=1`
- 2 cores, 4096 MiB RAM, and 512 MiB swap
- 12 GiB root disk on `local-lvm`
- separate 8 GiB `mp0` at `/srv/open-webui-studio` with `backup=1`
- DHCP on `vmbr0`
- no GPU, TUN/TAP, device, or host-directory passthrough

## 3. Start and inspect the empty LXC

```bash
pct start 107
pct status 107
pct exec 107 -- hostnamectl --static
pct exec 107 -- cat /etc/os-release
pct exec 107 -- ip -brief address
pct exec 107 -- findmnt /srv/open-webui-studio
pct exec 107 -- df -h / /srv/open-webui-studio
```

Record the DHCP address and create a reservation for the observed MAC before
configuring Caddy. Do not treat the address as stable until the reservation is
active and the guest receives it again.

## 4. Install Docker Engine and Compose v2

The Debian `_apt` account must be able to traverse `/etc` and read the
resolver configuration. Normalize and verify that boundary first:

```bash
pct exec 107 -- chmod 0755 /etc
pct exec 107 -- chmod 0644 /etc/resolv.conf
pct exec 107 -- runuser -u _apt -- test -r /etc/resolv.conf
pct exec 107 -- runuser -u _apt -- getent ahostsv4 deb.debian.org
```

Enter the guest with `pct enter 107`. Install Docker from its signed Debian
repository; this downloads a signing key but does not execute a downloaded
installer script:

```bash
apt-get -o APT::Update::Error-Mode=any update
apt-get install -y ca-certificates curl coreutils gnupg tar util-linux
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
```

Create `/etc/apt/sources.list.d/docker.sources` with exactly:

```text
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: trixie
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
```

Then run:

```bash
apt-get -o APT::Update::Error-Mode=any update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
docker version
docker compose version
df -h /
```

Do not add an interactive user to the `docker` group.

## 5. Pull and validate the immutable Studio artifact

Verify registry TLS, then authenticate interactively without putting a
credential on the command line:

```bash
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' https://git.theoldschool.house/v2/
docker login git.theoldschool.house
docker pull git.theoldschool.house/robert/open-webui-studio@sha256:9bbb5752adb54718df8cc00aaef746aed8629d4be558f1af34e586ccf4612462
```

Inspect only non-secret identity fields:

```bash
docker image inspect --format '{{.Id}} {{.Architecture}} {{.Os}} {{.Config.User}}' \
  git.theoldschool.house/robert/open-webui-studio@sha256:9bbb5752adb54718df8cc00aaef746aed8629d4be558f1af34e586ccf4612462
docker run --rm --entrypoint sh \
  git.theoldschool.house/robert/open-webui-studio@sha256:9bbb5752adb54718df8cc00aaef746aed8629d4be558f1af34e586ccf4612462 \
  -c 'id -u; id -g; stat -c "%u:%g:%a" /app/data'
df -h /
```

Expected platform is `linux/amd64`, configured user is `studio`, and the
runtime UID/GID and `/app/data` ownership are `100:101`.

## 6. Install the reviewed deployment bundle

Copy the reviewed `deploy/proxmox` directory to
`/root/studio-proxmox-bundle` on `pve2`, then run:

```bash
pct exec 107 -- install -d -o root -g root -m 0755 /etc/open-webui-studio
pct exec 107 -- install -d -o root -g root -m 0755 /usr/local/lib/owui-deploy
pct exec 107 -- install -d -o 100 -g 101 -m 0750 /srv/open-webui-studio/data

pct push 107 /root/studio-proxmox-bundle/studio.compose.yaml /etc/open-webui-studio/compose.yaml
pct push 107 /root/studio-proxmox-bundle/systemd/open-webui-studio-compose.service /etc/systemd/system/open-webui-studio-compose.service
pct push 107 /root/studio-proxmox-bundle/lib.sh /usr/local/lib/owui-deploy/lib.sh
pct push 107 /root/studio-proxmox-bundle/validate-deployment.sh /usr/local/lib/owui-deploy/validate-deployment.sh
pct push 107 /root/studio-proxmox-bundle/install-or-update.sh /usr/local/lib/owui-deploy/install-or-update.sh
pct push 107 /root/studio-proxmox-bundle/health-check.sh /usr/local/lib/owui-deploy/health-check.sh
pct push 107 /root/studio-proxmox-bundle/rollback.sh /usr/local/lib/owui-deploy/rollback.sh

pct exec 107 -- chown root:root /etc/open-webui-studio/compose.yaml /etc/systemd/system/open-webui-studio-compose.service
pct exec 107 -- chmod 0644 /etc/open-webui-studio/compose.yaml /etc/systemd/system/open-webui-studio-compose.service
pct exec 107 -- chown -R root:root /usr/local/lib/owui-deploy
pct exec 107 -- chmod 0444 /usr/local/lib/owui-deploy/lib.sh
pct exec 107 -- chmod 0555 /usr/local/lib/owui-deploy/validate-deployment.sh /usr/local/lib/owui-deploy/install-or-update.sh /usr/local/lib/owui-deploy/health-check.sh /usr/local/lib/owui-deploy/rollback.sh
pct exec 107 -- systemctl daemon-reload
```

Do not enable or start `open-webui-studio-compose.service` yet.

## 7. Runtime and identity stop gate

Before creating `runtime.env`, record these non-secret choices:

- final reserved Studio address;
- exact Keycloak issuer URL for realm `homelab`;
- dedicated Studio Keycloak client ID;
- allowed redirect URI
  `https://owui-stage.theoldschool.house/studio/auth/callback`;
- allowed post-logout/public origin `https://owui-stage.theoldschool.house`;
- OWUI OAuth provider key used for provider-token exchange;
- Flow worker timing and concurrency choices;
- secret-store owner and references for the OIDC client secret, session secret,
  and session encryption key.

Use these initial non-secret runtime choices unless the identity owner records
an alternative:

```text
ORIGIN=https://owui-stage.theoldschool.house
OWUI_BASE_URL=http://10.100.1.103:8080
OWUI_PUBLIC_URL=https://owui-stage.theoldschool.house
OIDC_SCOPES=openid profile email
STUDIO_DATABASE_PATH=/app/data/studio.db
OWUI_OAUTH_PROVIDER=oidc
FLOW_WORKER_ENABLED=true
FLOW_WORKER_ID=studio-staging-1
FLOW_WORKER_POLL_MS=1000
FLOW_CLAIM_TTL_MS=30000
FLOW_HEARTBEAT_INTERVAL_MS=10000
FLOW_RUN_TIMEOUT_MS=600000
FLOW_NODE_TIMEOUT_MS=120000
FLOW_MAX_CONCURRENT=2
```

The current OWUI staging bootstrap did not enable OAuth. Shared Keycloak login
cannot pass until OWUI and Studio use the same realm and OWUI exposes the
provider-token exchange under the recorded provider key. Treat that OWUI
configuration change as a separate reviewed operation; do not inspect or copy
its existing runtime secrets.

Create the root-owned runtime file directly inside LXC `107`, mode `0600`,
without displaying it. Do not copy it into the bundle or evidence. Only after
the identity configuration and reserved address are recorded should the first
digest deployment run:

```text
/usr/local/lib/owui-deploy/install-or-update.sh studio git.theoldschool.house/robert/open-webui-studio@sha256:9bbb5752adb54718df8cc00aaef746aed8629d4be558f1af34e586ccf4612462
```

Keep Caddy unchanged until guest-local `/studio/health` passes. When routing is
enabled, place the exact `/studio` redirect and `/studio/*` handler before the
existing OWUI catch-all.
