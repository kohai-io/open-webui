# OWUI VM 113 input evidence

Recorded on 2026-07-12 without inspecting container environments.

## Docker host

- Proxmox VMID: `113`
- Hostname: `docker`
- Address: `10.100.1.144/24`
- Architecture: `linux/amd64`
- Docker Engine: `28.3.3`
- Docker Compose: `2.39.1`
- containerd: `1.7.27`
- runc: `1.2.5`
- Swarm state: inactive; use Docker Standalone stacks
- Docker root: `/var/lib/docker`
- Docker storage driver: `overlay2`
- External model network: `infra`, local bridge

## Storage

- `/`, `/var/lib/docker`, and `/srv` resolve to `/dev/sda3`
- Filesystem: ext4
- Reported size: 99 GiB
- Reported used: 36 GiB
- Reported available: 59 GiB
- Selected OWUI bind mount: `/srv/stacks/owui-staging/data`
- Required ownership and mode: `1000:1000`, `0750`

The 32 GiB rehearsal figure is a free-space budget on the shared VM
filesystem, not a separately enforced volume quota.

## Network

- Existing listeners included ports 3000, 4000, 8000, 8001, 8931, 9099, and 9443.
- Selected unused listener: `10.100.1.144:8080`
- Public staging name: `owui-stage.theoldschool.house`
- LiteLLM is deployed on port 4000 and is intended to be reached over the
  external `infra` network as `http://litellm:4000/v1`.

## Existing control plane

- Portainer container: `portainer/portainer-ce:latest`
- Portainer publishes 8000 and 9443.

The pre-existing mutable Portainer tag is recorded as host context only. The
OWUI stack remains pinned to its OCI manifest digest and does not inherit that
tag policy.
