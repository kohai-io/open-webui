# Phase 9 OWUI Portainer topology evaluation

Recorded on 2026-07-12 after the first disposable OWUI LXC preparation
attempt.

Status: evaluated and not adopted.

## Evaluated alternative

The team considered running the first OWUI staging rehearsal as a
Portainer-managed stack on existing Docker VM `113` instead of installing a
second Docker Engine inside LXC `105`.

The application artifact does not change. Deploy:

`git.theoldschool.house/robert/open-webui@sha256:012e5f80e9aaf508c5831fde9440a78fea3b7ff2f4b2a8ca451758e904e696c9`

The image remains pinned, non-root, locally validated, and published from
source revision `6dca01731e6d38aca8b2b7094e409c306ce78936`.

## Evaluation

VM `113` already provides the homelab Docker Engine and Portainer control
plane. Reusing it avoids another nested Docker daemon and reduces memory and
operational overhead on `pve2`. The tradeoff is a shared Docker-host failure
and maintenance boundary.

The alternative was not selected. The operator preferred the familiar
service-level isolation of a dedicated unprivileged LXC, while the pinned OCI
image remains the already-built and tested release artifact. Phase 9 therefore
continues with Docker inside LXC `105`; OWUI reaches LiteLLM over the homelab
LAN rather than through Docker network `infra`.

## Preserved state

- Legacy rollback LXC `106` remains unchanged.
- Upstream-reference LXC `118` remains unchanged.
- LXC `105` was created as an unprivileged Debian 13 container with an 8 GiB
  root disk and 32 GiB managed data volume. It passed LXC configuration
  validation and then stopped during package setup because guest DNS was not
  configured. Docker, the deployment bundle, runtime secrets, and OWUI were
  not installed. The operator deleted this incomplete LXC before returning to
  the selected isolated-LXC topology. Its deletion lost no application data or
  accepted rehearsal evidence; recreation must use the corrected DNS-aware
  provisioner.

## Alternative boundaries retained for reference

- OWUI data uses a dedicated local bind-mount path on VM `113` and must not be
  placed on NFS, SMB, or CIFS while SQLite remains in that directory.
- The selected bind mount is `/srv/stacks/owui-staging/data` on VM `113`'s
  local ext4 root filesystem.
- The selected staging listener is `10.100.1.144:8080`.
- Portainer owns stack variables for the Portainer-managed topology.
- The image remains digest-pinned and runs as `1000:1000`.
- Caddy routes the staging name to a dedicated address and port on VM `113`.
- OWUI joins the existing external Docker network `infra` and uses the
  `litellm` service at `http://litellm:4000/v1` as its intended
  OpenAI-compatible model gateway.
- The legacy deployment remains the final routing rollback.
- The Studio placement decision is not changed by this OWUI-only amendment.

## Evidence captured during evaluation

VM `113` architecture, address, Docker Standalone state, storage filesystem
and capacity, published ports, and the `infra` network were recorded under
`deploy/portainer/evidence`. Those facts remain useful host context but are not
OWUI deployment evidence. LXC `105` must still pass Docker installation,
digest deployment, stopped-service backup, restore, data-paired rollback,
Caddy routing rollback, and public-origin acceptance.
