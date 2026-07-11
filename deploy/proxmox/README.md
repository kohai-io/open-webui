# Proxmox deployment bundle

This bundle deploys Open WebUI and Studio as separate pinned OCI services in
the LXCs defined by `docs/proxmox-staging-deployment-contract.md`.

The bundle does not create LXCs, configure the reverse proxy, build images, or
publish images. An operator performs those actions after selecting the
Proxmox host, storage, network, registry, and secret store.

## Safety properties

- The update command accepts an OCI manifest digest and rejects floating tags.
- Each service has its own manifest, runtime environment, data directory,
  systemd unit, release records, and rollback path.
- The commands never render a resolved Compose configuration or print the
  runtime environment.
- An update stops the service before archiving SQLite-backed data.
- Studio updates require confirmation that no Flow is queued, running, or
  awaiting cancellation.
- A failed candidate stops before the operator chooses rollback.
- Rollback verifies the archive checksum and preserves candidate data under a
  timestamped path.

The rollback command replaces the active data directory. It requires
`--confirm-restore-data` and accepts release records only from the service's
fixed backup root.

## Files

| File                     | Purpose                                                            |
| ------------------------ | ------------------------------------------------------------------ |
| `owui.compose.yaml`      | OWUI service, port 8080, and `/srv/open-webui/data` mount          |
| `studio.compose.yaml`    | Studio service, port 3000, and `/srv/open-webui-studio/data` mount |
| `*-runtime-env.names`    | Variable-name and sensitivity inventories with no values           |
| `systemd/*.service`      | Boot integration for each Compose project                          |
| `validate-deployment.sh` | Boot-time digest, file, ownership, and permission validation       |
| `install-or-update.sh`   | Digest-only first install and update with stopped-service backup   |
| `health-check.sh`        | Local service health check                                         |
| `rollback.sh`            | Checksum-verified image and data rollback                          |
| `REHEARSAL_CHECKLIST.md` | Evidence checklist for disposable staging LXCs                     |

## Build and publication boundary

Build from clean private Gitea checkouts at these commits:

| Image  | Repository                                                    | Commit                                       |
| ------ | ------------------------------------------------------------- | -------------------------------------------- |
| OWUI   | `https://git.theoldschool.house/robert/open-webui`            | `6dca01731` on `rebaseline/upstream-v0.10.2` |
| Studio | `https://git.theoldschool.house/robert/open-webui-studio.git` | `bf7dd04` on `codex/flows-foundation`        |

Build OWUI with a recorded non-root UID and GID. Build Studio from its existing
Dockerfile, which runs as `studio`. Add OCI labels for the full source revision
and source repository.

Push images only after explicit publication approval. Record the registry
manifest digest after the push, and use that digest for deployment. A local
image ID or mutable tag does not satisfy the contract.

## LXC prerequisites

Install these packages or equivalent host tools inside each disposable LXC:

- Docker Engine with the Compose v2 plugin;
- `curl`, GNU `tar`, `coreutils`, and `util-linux`;
- CA certificates for the private registry and service endpoints.

Configure the minimum LXC nesting and keyring features required by the OCI
runtime. Keep each LXC unprivileged. Use Proxmox firewall rules to admit the
application port from the reverse proxy and the administration network.

The operator must authenticate the OCI runtime to the private registry
without placing registry credentials in this repository or the service
runtime environment.

## Install the bundle

Install only the service-specific manifest and unit in each LXC.

For OWUI:

```text
/etc/open-webui/compose.yaml
/etc/open-webui/runtime.env
/etc/systemd/system/open-webui-compose.service
/srv/open-webui/data
```

For Studio:

```text
/etc/open-webui-studio/compose.yaml
/etc/open-webui-studio/runtime.env
/etc/systemd/system/open-webui-studio-compose.service
/srv/open-webui-studio/data
```

Install `lib.sh`, `validate-deployment.sh`, `install-or-update.sh`,
`health-check.sh`, and `rollback.sh` together in a root-owned directory such
as `/usr/local/lib/owui-deploy`. Preserve their relative paths because each
command loads `lib.sh` from its own directory. Make the four commands
executable and keep `lib.sh` read-only.

Render `runtime.env` from the secret store. Use the corresponding
`*-runtime-env.names` file as the starting inventory. Set ownership to root
and mode to 0400 or 0600. Do not use the inventory file as an environment
file.

Create the data directory with the numeric UID and GID used inside the image.
For OWUI, use the UID/GID recorded at build time. For Studio, inspect the
approved image's `studio` account without starting the application, then set
the bind-mount ownership to that numeric identity.

Install the systemd unit, run `systemctl daemon-reload`, and enable it for
boot. The first deployment command creates `deployment.env` before starting
the unit. Every boot runs `validate-deployment.sh`, so a missing runtime file,
unsafe file permission, or floating image reference prevents service startup.

## First deployment

Enter proxy maintenance mode before starting either public route. Run the
command inside the matching LXC with the approved digest:

```text
/usr/local/lib/owui-deploy/install-or-update.sh owui registry/repository@sha256:<digest>
/usr/local/lib/owui-deploy/install-or-update.sh studio registry/repository@sha256:<digest>
```

The command creates a release record under:

```text
/var/backups/open-webui-deploy/releases/<UTC timestamp>.<suffix>
/var/backups/open-webui-studio-deploy/releases/<UTC timestamp>.<suffix>
```

The first release has no previous image and cannot use image rollback. Rebuild
the empty LXC or restore its pre-install Proxmox backup if the first deployment
fails.

Copy each successful data backup to the selected backup target before opening
proxy traffic. The local archive supports the rehearsal but does not replace
an off-LXC backup.

## Update

Build and publish the candidate before entering the maintenance window. Pulling
the image happens before service shutdown.

Update OWUI:

```text
/usr/local/lib/owui-deploy/install-or-update.sh owui registry/repository@sha256:<new-digest>
```

Update Studio after proving that no Flow is queued, running, or awaiting
cancellation:

```text
/usr/local/lib/owui-deploy/install-or-update.sh studio registry/repository@sha256:<new-digest> --confirm-studio-idle
```

The command stops only the selected service. It creates a checksum-protected
data archive and records the old and candidate digests. It starts the
candidate and waits up to two minutes for local health. A failed health check
stops the candidate and returns the exact release-record path required for
rollback.

Run the public-origin acceptance smoke tests before leaving maintenance mode.
Local health proves process readiness, not proxy, authentication, provider, or
permission behaviour.

## Rollback

Use the release-record directory printed by the failed or rejected update:

```text
/usr/local/lib/owui-deploy/rollback.sh owui /var/backups/open-webui-deploy/releases/<UTC timestamp>.<suffix> --confirm-restore-data
/usr/local/lib/owui-deploy/rollback.sh studio /var/backups/open-webui-studio-deploy/releases/<UTC timestamp>.<suffix> --confirm-restore-data
```

Rollback pulls the recorded previous digest, verifies the archive, stops the
service, moves candidate data aside, restores the paired data archive, and
starts the old image. It leaves the candidate data under
`/srv/<service>/failed-data-<UTC timestamp>` for diagnosis.

Keep proxy traffic in maintenance mode until local and public smoke tests pass.
If rollback also fails, leave the service stopped and restore the tested
Proxmox backup.

## Limitations

- The scripts do not manipulate Proxmox, DNS, certificates, firewall rules,
  reverse-proxy routes, or secret-store records.
- The Studio application has no administrative drain endpoint. The operator
  must prove that Flow execution is idle before confirming an update.
- The Flow worker runs inside the Studio image. The bundle can test worker
  recovery, but it cannot deploy a different worker image.
- The scripts create local backup archives. The operator must copy them to the
  selected backup system and test restoration there.
- The bundle does not inspect resolved environments because that could expose
  secrets.
