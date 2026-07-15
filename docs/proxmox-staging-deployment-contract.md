# Proxmox staging deployment contract

Recorded on 2026-07-11 for Phase 9 of the Open WebUI v0.10.2 rebaseline.

> Evaluation note, 2026-07-12: a Portainer-managed stack on existing Docker VM
> `113` was considered after the first LXC preparation interruption, but was
> not adopted. See `docs/phase-9-portainer-topology-amendment.md`. The selected
> separate-LXC design below remains active; do not treat partially prepared LXC
> `105` as a completed OWUI rehearsal.

This contract selects the staging topology and deployment boundaries. An
operator must still select the Proxmox node, container IDs, storage pool,
network addresses, DNS names, private image registry, and reverse-proxy host
before provisioning.

## Reference script

The Proxmox Community Scripts project provides an
[Open WebUI LXC wrapper](https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/openwebui.sh)
and a separate
[Open WebUI install payload](https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/install/openwebui-install.sh).
The wrapper defaults to an unprivileged Debian 13 LXC with 4 vCPU, 8 GiB RAM,
and 50 GiB storage. It also supports optional GPU passthrough.

Use those defaults as sizing and Proxmox setup references. Do not execute,
source, vendor, or fork the scripts for this deployment. They fetch mutable
helpers from `main`, install the current `open-webui[all]` package, run the
service as root inside the LXC, and update by force-installing the current
package. That lifecycle cannot reproduce the pinned OWUI and Studio builds or
their rollback boundaries.

## Selected topology

Provision two unprivileged Debian 13 LXCs on the selected Proxmox staging
node. Keep the existing identity provider and model endpoints outside these
LXCs.

| LXC              | Initial resources         | Service                                            | Internal port | Persistent storage                                                     |
| ---------------- | ------------------------- | -------------------------------------------------- | ------------: | ---------------------------------------------------------------------- |
| `owui-staging`   | 4 vCPU, 8 GiB RAM, 50 GiB | Pinned OWUI OCI image                              |          8080 | Proxmox-managed local block volume mounted at `/srv/open-webui`        |
| `studio-staging` | 2 vCPU, 4 GiB RAM, 20 GiB | Pinned Studio OCI image and in-process Flow worker |          3000 | Proxmox-managed local block volume mounted at `/srv/open-webui-studio` |

Treat these figures as starting allocations. Record CPU, memory, disk,
storage-pool, and mount-point choices before provisioning. Increase Studio
resources if Flow concurrency or Media traffic reaches the recorded limits.

For the disposable OWUI bootstrap rehearsal, the operator approved a smaller
40 GiB total allocation split into a 24 GiB root disk for Debian and Docker
images and a separate 16 GiB managed application-data volume. The first 8 GiB
root and 32 GiB data split could not extract the pinned OWUI image. This
rehearsal exception does not change the 50 GiB staging starting allocation
above.

Use local block-backed storage for both SQLite data directories. Do not place
SQLite files on NFS, SMB, or another filesystem with unverified locking and
durability behaviour. Configure each Proxmox mount point so `vzdump` includes
it, then prove that inclusion with a restore rehearsal.

### Container runtime

Run the pinned OCI image inside each LXC with a declarative Compose-compatible
manifest and systemd-managed runtime startup. A nested OCI runtime requires
the minimum Proxmox LXC nesting and keyring features supported by the selected
host. Do not add device passthrough or privileged mode unless a documented
acceptance test requires it.

Use a small VM instead of an LXC if the selected Proxmox kernel cannot run the
OCI runtime without broad privileges. Keep the two-service and two-storage
boundary unchanged.

Do not install Ollama in either LXC during the first rehearsal. Configure
OWUI to use the selected external model endpoints. A future local inference
service needs its own resource, network, upgrade, and rollback contract.

## Immutable artifacts

Build and promote two images:

| Artifact | Source                                       | Build requirements                                                                   |
| -------- | -------------------------------------------- | ------------------------------------------------------------------------------------ |
| OWUI     | `rebaseline/upstream-v0.10.2` at `6dca01731` | Build from the repository Dockerfile with a recorded non-root UID/GID and build hash |
| Studio   | `codex/flows-foundation` at `bf7dd04`        | Build from the repository Dockerfile, which pins Node 22.17.0 and runs as `studio`   |

For each image, record:

- source repository, branch, and full commit SHA;
- build command and non-secret build arguments;
- image repository, immutable tag, and manifest digest;
- build timestamp, builder identity, target architecture, and base-image digests;
- validation results associated with that digest.

Deploy the digest form, such as `registry.example/image@sha256:...`. Do not
deploy `main`, `latest`, a branch-only tag, or a mutable version tag. Promotion
to a private registry requires explicit publication approval.

The OWUI image must run with a non-root UID/GID and own
`/app/backend/data`. Studio must retain its existing non-root `studio` user and
own `/app/data`. The runtime must fail startup rather than change data
ownership to an unexpected account.

## Deployment implementation

The version-controlled bundle under `deploy/proxmox` provides:

- separate OWUI and Studio Compose manifests;
- systemd boot units;
- value-free runtime environment inventories;
- digest-only install and update handling;
- stopped-service data backups and local health checks;
- checksum-verified rollback that preserves rejected candidate data;
- a disposable-LXC rehearsal checklist.

The bundle does not create Proxmox resources, publish images, configure the
reverse proxy, or render secrets. Read `deploy/proxmox/README.md` before the
first rehearsal.

## Persistent data boundary

Mount only the service data directory into each image:

| Service | Host path                     | Container path      | Contents                                                                                              |
| ------- | ----------------------------- | ------------------- | ----------------------------------------------------------------------------------------------------- |
| OWUI    | `/srv/open-webui/data`        | `/app/backend/data` | Fresh OWUI database, uploads, indexes, and application storage                                        |
| Studio  | `/srv/open-webui-studio/data` | `/app/data`         | Fresh Studio SQLite database, sessions, Flow definitions, versions, execution history, and audit rows |

Do not share either directory with the other service or with the legacy
deployment. Studio must access OWUI through authenticated APIs and must never
mount OWUI storage.

Start both directories empty. Run the designated application startup process
once and record the resulting migration heads. Do not copy users, OAuth state,
files, chats, knowledge, flows, schedules, preferences, or encryption keys
from the legacy deployment.

## Configuration and secrets

Create a service-specific configuration inventory that contains variable
names, owners, purpose, and secret-reference names. Do not record values in
Git, build logs, Proxmox notes, or this contract.

OWUI configuration must start from the v0.10.2 example and
`docs/v0.10.2-configuration-matrix.md`. Studio configuration must start from
its committed `.env.example`. At minimum, assign owners for:

- public origin and reverse-proxy trust;
- OIDC issuer, client, callback, logout, and session settings;
- OWUI provider and model endpoint configuration;
- OWUI and Studio session or encryption keys;
- Studio-to-OWUI URL and OAuth provider name;
- Flow worker identity, deadlines, heartbeat, and concurrency limits.

The deployment mechanism must inject secrets at runtime from the selected
secret store. Do not bake secrets into images or place secret values in a
Compose manifest. Restrict configuration and secret files to the service
administrator account.

## Network and reverse proxy

Give each LXC a stable internal address. Permit inbound application traffic
from the reverse proxy and the designated administration network. Block
direct public access to ports 8080 and 3000.

Configure TLS on the existing reverse proxy with this route order:

1. `/studio` redirects to `/studio/` when the trailing slash is absent.
2. `/studio/*` proxies to `studio-staging:3000` and preserves the `/studio`
   prefix.
3. All remaining paths proxy to `owui-staging:8080`.

Forward the original host and scheme, the client forwarding chain, and a
bounded request ID. Preserve `Authorization` and `Cookie`. Configure OWUI to
trust only the proxy address or subnet.

Disable response buffering for Studio execution SSE and set a timeout longer
than the maximum Flow run timeout. Configure OWUI WebSocket or Socket.IO
upgrade handling. Set explicit upload limits and request timeouts, then test a
representative large file without weakening global proxy limits.

Set exact CORS origins and public callback URLs. Do not use wildcard CORS.
The browser must receive secure, HTTP-only cookies over HTTPS, and OIDC must
return to the public `/studio/auth/callback` URL.

## Health and observability

Use these health endpoints:

| Service | Endpoint         | Expected response                               |
| ------- | ---------------- | ----------------------------------------------- |
| OWUI    | `/health`        | HTTP 200 and the v0.10.2 health payload         |
| Studio  | `/studio/health` | HTTP 200 with only status, service, and version |

Check each endpoint from inside its LXC, from the reverse proxy, and through
the public staging URL. A successful local check cannot replace the proxy
check.

Collect service state, restart count, CPU, memory, disk use, request latency,
HTTP error rate, OWUI provider failures, Studio worker claims, Flow execution
failures, and migration state. Logs may contain bounded request IDs and stable
error codes. They must not contain tokens, cookies, prompts, inputs, outputs,
checkpoint data, upstream response bodies, or secret values.

## Bootstrap rehearsal

Use the following order:

1. Record the Proxmox host version, node, LXC IDs, storage, network, and proxy
   target names.
2. Build, test, publish, and record both image digests.
3. Provision the empty LXCs and managed data volumes.
4. Install the OCI runtime and systemd startup units from reviewed,
   version-controlled deployment manifests.
5. Inject fresh staging configuration and secret references.
6. Start OWUI and record its migration head and health result.
7. Create the first administrator through the supported bootstrap interface.
8. Configure representative users, groups, models, agents, files, Knowledge,
   Automations, OAuth, and MCP from scratch.
9. Start Studio, record migration `0007_flow_audit.sql`, and verify
   `studio_flow_audit` in the Studio database.
10. Configure the reverse proxy and run the public-origin checks.

Repeat the empty-data bootstrap once after deleting only the disposable
staging data. Keep the first rehearsal evidence until the second run passes.

## Acceptance matrix

The staging gate needs recorded results for:

| Area        | Required proof                                                                                                                                                       |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Identity    | Shared OIDC login, logout, expiry, disabled-account denial, callback validation, and two-user separation                                                             |
| OWUI        | Welcome flag on/off, model grants, native chat and streaming, files, Knowledge, Automations, Skills, OAuth, MCP, and administrator boundaries                        |
| Studio      | Direct `/studio/` load, Welcome/Agents links, Media list/preview/download, Flow CRUD/versioning, canvas persistence, run progress, output, history, and cancellation |
| Proxy       | Direct page loads, static assets, cookies, request IDs, SSE reconnection, WebSockets, upload limits, and upstream-unavailable states                                 |
| Isolation   | Cross-user file, media, Flow, execution, event, and audit access returns the documented hidden or denied result                                                      |
| Performance | Representative media library, concurrent Flow limit, long SSE connection, upload size, startup time, and storage growth                                              |
| Failure     | OWUI stopped, Studio stopped, model endpoint unavailable, expired OIDC session, worker restart, and full disk warning                                                |

Use intended staging models to test MCP tool-name calls. Add no resolver patch
if the model emits registered names or the workflow succeeds. A reproduced
unprefixed-name failure must include exact, unique, ambiguous, and unknown-name
evidence before any patch proposal.

## Backup and rollback

### Backup points

Create named backup points before bootstrap completion and before each image
change:

- OWUI image digest, configuration-name inventory, and stopped-service data
  backup;
- Studio image digest, configuration-name inventory, and stopped-service data
  backup;
- Proxmox LXC configuration and managed-volume `vzdump` backup;
- reverse-proxy configuration revision.

Stop the affected service before taking a filesystem-level SQLite backup.
For Studio, confirm that no Flow execution is queued, running, or awaiting
cancellation before stopping the service. Record backup size, duration,
checksum, storage location, and retention class without recording secrets.

### Service rollback

Rehearse OWUI and Studio rollback as separate operations:

1. Remove the service from proxy traffic or enter the maintenance state.
2. Stop the affected service.
3. Preserve the failed data directory for diagnosis.
4. Restore the data backup paired with the previous image digest.
5. Start the previous digest and run its health and acceptance smoke tests.
6. Restore proxy traffic after the checks pass.

Do not start an older image against a database after forward-only migrations
unless that exact image and schema pair passed a rehearsal. Do not downgrade
or convert OWUI data.

The Flow worker ships inside the Studio image. Rehearse worker recovery by
stopping Studio after a deterministic checkpoint, starting the same digest,
and confirming checkpoint recovery. Rehearse the uncertain Model-call case
and confirm `model_result_unknown` without a repeated dispatch.

### Deployment rollback

Keep the legacy deployment and its storage unchanged. The final rollback path
switches reverse-proxy routing back to the legacy deployment. Do not import
new OWUI or Studio data into the legacy databases. Record the routing-change
time, DNS or certificate impact, health result, and user-visible interruption.

## Evidence record

Store these non-secret records beside the deployment configuration:

- Proxmox node and version;
- LXC IDs, hostnames, resource limits, storage volumes, and network names;
- image source SHAs, tags, and digests;
- configuration variable names and secret-reference names;
- migration heads and bootstrap timestamps;
- proxy revision and public URLs;
- health, acceptance, performance, backup, restore, and rollback results;
- operator and approval timestamps.

Do not mark Phase 9 complete from this contract. Phase 9 requires the two
fresh-data rehearsals, acceptance matrix, backup restore, service rollbacks,
and routing rollback on the selected Proxmox target.
