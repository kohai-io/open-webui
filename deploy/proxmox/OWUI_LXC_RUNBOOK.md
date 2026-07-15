# Disposable OWUI LXC preparation runbook

This runbook prepares the Phase 9 OWUI LXC on `pve2`. It deliberately stops
before creating `/etc/open-webui/runtime.env`, starting OWUI, or changing
Caddy. Run the Proxmox commands as `root` on `pve2` and the guest commands as
`root` inside LXC `105`.

Do not print registry credentials, runtime environment values, tokens, or
cookies. Do not run the Proxmox Community Scripts installer.

## Preferred scripted path

The reviewed host-side provisioner automates sections 1 through 6 and stops
at the same gate before runtime secrets or application startup:

```bash
chmod 0555 /root/owui-proxmox-bundle/provision-owui-lxc.sh
/root/owui-proxmox-bundle/provision-owui-lxc.sh --check-only
/root/owui-proxmox-bundle/provision-owui-lxc.sh --confirm-create
```

The creation command requires the operator to type `CREATE-105`. If a later
stage fails after the LXC exists, inspect the failure and resume with:

```bash
/root/owui-proxmox-bundle/provision-owui-lxc.sh --resume-existing
```

Resume validates the existing LXC against the recorded hostname, resources,
storage, network, unprivileged state, required features, and absence of device
passthrough before continuing. It never deletes or recreates the LXC.

The remaining sections are the manual audit trail and fallback procedure.

## Recorded inputs

- VMID: `105`
- Hostname: `owui-staging`
- Template: `local:vztmpl/debian-13-standard_13.1-2_amd64.tar.zst`
- CPU and memory: 4 vCPU, 8192 MiB RAM, 1024 MiB swap
- Root disk: `local-lvm`, 24 GiB
- Managed data volume: `local-lvm`, 16 GiB at `/srv/open-webui`
- Network: DHCP on `vmbr0`, followed by a UniFi DHCP reservation
- Reserved address: `10.100.1.103/24`
- Caddy source/trusted proxy address: `10.100.1.20`
- DNS resolvers: `10.100.1.21` and `10.100.1.22`
- Public staging name: `owui-stage.theoldschool.house`
- Published OWUI image:
  `git.theoldschool.house/robert/open-webui@sha256:012e5f80e9aaf508c5831fde9440a78fea3b7ff2f4b2a8ca451758e904e696c9`
- Container UID/GID: `1000:1000`
- Legacy rollback LXC: `106`; do not modify it
- Upstream-reference LXC: `118`; retain it unless the operator gives fresh
  approval to stop it

## 1. Read-only preflight on pve2

Run each command separately and stop if VMID `105` already exists or the
recorded template/storage is unavailable:

```bash
pct list
pveam list local
pvesm status --content rootdir
free -h
```

Keep LXC `106` running and unchanged. The operator elected to retain LXC
`118`; do not stop it without fresh approval. If host memory remains
constrained, stop and obtain an explicit resource decision before creating or
starting LXC `105`.

## 2. Create the stopped unprivileged LXC

This creates a managed `mp0` volume and marks it for inclusion in a future
`vzdump` backup even though no off-LXC backup target is selected yet.

```bash
pct create 105 local:vztmpl/debian-13-standard_13.1-2_amd64.tar.zst \
  --hostname owui-staging \
  --arch amd64 \
  --ostype debian \
  --unprivileged 1 \
  --features nesting=1,keyctl=1 \
  --cores 4 \
  --memory 8192 \
  --swap 1024 \
  --rootfs local-lvm:24 \
  --mp0 local-lvm:16,mp=/srv/open-webui,backup=1 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp,type=veth \
  --nameserver '10.100.1.21 10.100.1.22' \
  --onboot 0 \
  --start 0 \
  --tags 'owui;phase9;staging'
```

Verify the configuration before starting it:

```bash
pct config 105
```

Required evidence in the output:

- `unprivileged: 1`
- `features: keyctl=1,nesting=1`
- `rootfs: local-lvm:vm-105-disk-0,size=24G`
- a separate `mp0` on `local-lvm` mounted at `/srv/open-webui`
- no GPU, TUN/TAP, device, or host-directory passthrough

## 3. Start and inspect the empty LXC

```bash
pct start 105
pct status 105
pct exec 105 -- hostnamectl --static
pct exec 105 -- cat /etc/os-release
pct exec 105 -- ip -brief address
pct exec 105 -- cat /etc/resolv.conf
pct exec 105 -- getent ahostsv4 deb.debian.org
pct exec 105 -- findmnt /srv/open-webui
pct exec 105 -- df -h / /srv/open-webui
```

Record the DHCP lease and create the UniFi reservation before configuring
Caddy. Do not treat the address as stable until the reservation is active and
the LXC receives the reserved lease.

The root disk is sized to retain the operating system, Docker, and both an
active and candidate OWUI image during an update. Check free root space after
installing Docker and after pulling the image. Do not move replaceable Docker
layers into the managed application-data volume.

## 4. Install Docker Engine and Compose v2

Enter the LXC:

```bash
pct enter 105
```

Inside the LXC, use Docker's Debian repository. This downloads Docker's
repository signing key; it does not execute a downloaded script.

```bash
apt-get update
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
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
docker version
docker compose version
dpkg-query -W docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
df -h /
```

Do not add an interactive user to the `docker` group. Deployment commands and
the systemd unit run as root; membership in that group is root-equivalent.

## 5. Verify registry trust and pull the immutable artifact

Still inside the LXC, verify that TLS succeeds and the unauthenticated
registry request returns HTTP 401:

```bash
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' https://git.theoldschool.house/v2/
```

Authenticate interactively. Do not place the password or token on the command
line and do not copy Docker's credential file into the deployment bundle:

```bash
docker login git.theoldschool.house
```

Pull only the recorded digest and inspect non-secret identity fields:

```bash
docker pull git.theoldschool.house/robert/open-webui@sha256:012e5f80e9aaf508c5831fde9440a78fea3b7ff2f4b2a8ca451758e904e696c9
docker image inspect --format '{{.Id}} {{.Architecture}} {{.Os}} {{.Config.User}}' git.theoldschool.house/robert/open-webui@sha256:012e5f80e9aaf508c5831fde9440a78fea3b7ff2f4b2a8ca451758e904e696c9
df -h /
```

The configured user must be `1000:1000` and the platform must be
`linux/amd64`. Do not inspect the image or container environment.

## 6. Install the reviewed deployment bundle

Copy the reviewed `deploy/proxmox` directory from the planning workstation to
`/root/owui-proxmox-bundle` on `pve2`. Then run these commands on `pve2`:

```bash
pct exec 105 -- install -d -o root -g root -m 0755 /etc/open-webui
pct exec 105 -- install -d -o root -g root -m 0755 /usr/local/lib/owui-deploy
pct exec 105 -- install -d -o 1000 -g 1000 -m 0750 /srv/open-webui/data

pct push 105 /root/owui-proxmox-bundle/owui.compose.yaml /etc/open-webui/compose.yaml
pct push 105 /root/owui-proxmox-bundle/systemd/open-webui-compose.service /etc/systemd/system/open-webui-compose.service
pct push 105 /root/owui-proxmox-bundle/lib.sh /usr/local/lib/owui-deploy/lib.sh
pct push 105 /root/owui-proxmox-bundle/validate-deployment.sh /usr/local/lib/owui-deploy/validate-deployment.sh
pct push 105 /root/owui-proxmox-bundle/install-or-update.sh /usr/local/lib/owui-deploy/install-or-update.sh
pct push 105 /root/owui-proxmox-bundle/health-check.sh /usr/local/lib/owui-deploy/health-check.sh
pct push 105 /root/owui-proxmox-bundle/rollback.sh /usr/local/lib/owui-deploy/rollback.sh

pct exec 105 -- chown root:root /etc/open-webui/compose.yaml /etc/systemd/system/open-webui-compose.service
pct exec 105 -- chmod 0644 /etc/open-webui/compose.yaml /etc/systemd/system/open-webui-compose.service
pct exec 105 -- chown -R root:root /usr/local/lib/owui-deploy
pct exec 105 -- chmod 0444 /usr/local/lib/owui-deploy/lib.sh
pct exec 105 -- chmod 0555 /usr/local/lib/owui-deploy/validate-deployment.sh /usr/local/lib/owui-deploy/install-or-update.sh /usr/local/lib/owui-deploy/health-check.sh /usr/local/lib/owui-deploy/rollback.sh
pct exec 105 -- systemctl daemon-reload
```

Do not enable or start `open-webui-compose.service` yet.

## 7. Stop gate before first deployment

The following inputs remain required:

- the final DHCP-reserved LXC address;
- the Caddy host or source address for `FORWARDED_ALLOW_IPS`;
- intended model provider and model names;
- whether OAuth is enabled for this rehearsal;
- names of any MCP, file, or notification integrations;
- non-secret variable choices such as `ENABLE_WELCOME_PAGE`;
- generation and secure retention of `WEBUI_SECRET_KEY`.

After those names and choices are recorded, create
`/etc/open-webui/runtime.env` as `root:root` mode `0600` without printing it.
Only then run the digest deployment command from the reviewed bundle.

Do not configure Caddy or open proxy traffic until local health passes.
