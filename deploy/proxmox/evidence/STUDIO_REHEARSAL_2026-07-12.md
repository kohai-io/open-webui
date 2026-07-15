# Studio Proxmox rehearsal evidence

Recorded on 2026-07-12 for Phase 9. This file contains no credentials, resolved
runtime environment values, tokens, cookies, user identities, prompts, model
outputs, or Flow inputs and outputs.

## Published artifact

- Source repository: `https://git.theoldschool.house/robert/open-webui-studio.git`
- Exact source revision:
  `bf7dd04aca6a96aaaae13c4cbb21a3d464660af2`
- Source state: clean detached checkout
- Builder: Docker Desktop `desktop-linux`, Docker Engine `29.6.1`
- Base image: `node:22.17.0-alpine` at
  `sha256:fc3e945f920b7e3000cd1af86c4ae406ec70c72f328b667baf0f3a8910d69eed`
- Target platform: `linux/amd64`
- Configured runtime user: `studio`; numeric UID/GID `100:101`
- `/app/data` ownership and mode: `100:101`, `0755`
- Static check: zero errors and zero warnings
- Server tests: 130 passed across 25 files
- Local health smoke: status `ok`, service `open-webui-studio`, version `0.0.1`
- Publication approval: fresh explicit operator approval received immediately
  before the push
- Published tag:
  `git.theoldschool.house/robert/open-webui-studio:bf7dd04aca6a96aaaae13c4cbb21a3d464660af2`
- Deployment reference:
  `git.theoldschool.house/robert/open-webui-studio@sha256:9bbb5752adb54718df8cc00aaef746aed8629d4be558f1af34e586ccf4612462`
- OCI index digest:
  `sha256:9bbb5752adb54718df8cc00aaef746aed8629d4be558f1af34e586ccf4612462`
- Linux/amd64 image manifest:
  `sha256:fba9290f49fe922d338b9987a5df95f9e1943a16631eda053c3f45ac2efef949`
- Provenance attestation manifest:
  `sha256:7601e72eb04c5ede95fb4db9a2a32152eb56de03e9a2a0321e34a470a2c19165`

The registry push and an independent manifest inspection reported the same OCI
index digest. Studio image publication passes. Deployment gates do not pass
from this artifact evidence alone.

## Selected staging inputs

- Node: `pve2`, Proxmox VE `8.4.19`
- VMID: `107`, confirmed available by the operator
- Hostname: `studio-staging`
- Guest: unprivileged Debian 13 LXC
- Features: `nesting=1,keyctl=1`; no device passthrough
- Resources: 2 vCPU, 4096 MiB RAM, 512 MiB swap
- Root disk: 12 GiB on `local-lvm`
- Managed data volume: 8 GiB on `local-lvm`, mounted at
  `/srv/open-webui-studio` with backup inclusion required
- Network: DHCP on `vmbr0`, followed by a reservation
- DNS resolvers: `10.100.1.21` and `10.100.1.22`
- Caddy source: `10.100.1.20`
- Public origin: `https://owui-stage.theoldschool.house`
- OWUI internal target: `http://10.100.1.103:8080`
- Identity provider: existing Keycloak realm `homelab`

The operator reported that `local-lvm` capacity was reviewed and accepted
before selecting the Studio allocation. A named off-LXC backup target and an
actual restore rehearsal remain required for backup/restore acceptance.

## Preparation state

- `deploy/proxmox/STUDIO_LXC_RUNBOOK.md` records the console-run preparation
  through a stop gate before runtime secrets, startup, OWUI OAuth changes, or
  Caddy routing.
- `deploy/proxmox/provision-studio-lxc.sh` provides guarded `--check-only`,
  interactive `CREATE-107`, and validated `--resume-existing` paths. Bash
  syntax validation passed. The script has not been executed on pve2.
- The existing Studio Compose manifest, systemd unit, digest-only deployment
  commands, health check, stopped-service backup, and checksum-verified
  rollback path were reviewed against the published image.
- `OWUI_PUBLIC_URL` was added to the value-free Studio runtime-name inventory
  because the published Studio code supports a distinct public OWUI URL while
  using the internal OWUI URL for server-to-server calls.
- The current OWUI bootstrap did not enable OAuth. Shared sign-in remains
  blocked until the same Keycloak realm and provider key are configured on
  OWUI and Studio without exposing their secrets.
- Current local transfer artifact:
  `studio-proxmox-bundle-ef8d79904-20260712-r3.tar.gz`, size `30,512` bytes,
  SHA-256
  `e81b411c4e7514d7e09d7385af5d9f96199b71dd0f93941d989889b8cfec7f5a`.
  The archive contains the guarded Studio provisioner, Studio runbook,
  Compose manifest, systemd unit, value-free runtime-name inventory, and
  reviewed deployment scripts. It has not been transferred to or executed on
  pve2. The earlier `r1` archive predates the provisioner, and `r2` contains
  the feature-validation defect found during the first creation attempt. Both
  are obsolete.

## Open gates

- Create and validate LXC `107` without changing LXCs `105`, `106`, or `118`.
- Record the reserved Studio address.
- Record the non-secret Keycloak issuer URL, dedicated client ID, callback,
  logout origin, and matching OWUI provider key.
- Create root-only runtime configuration without exposing its values.
- Run the first digest deployment and record migration `0007_flow_audit.sql`,
  `studio_flow_audit`, systemd state, and local health.
- Route `/studio` and `/studio/*` before the OWUI catch-all and prove public
  health, assets, cookies, request IDs, SSE, and identity behavior.
- Rehearse Flow worker recovery, backup, update, rollback, and off-LXC restore.

No Studio LXC, runtime configuration, service, database, Caddy route, backup,
restore, update, rollback, or Flow recovery gate is marked passed by this
preparation record.

## First provisioning attempt

- `--check-only` passed and confirmed VMID `107` was unused.
- The operator typed the required `CREATE-107` confirmation. Proxmox created
  the 12 GiB root and 8 GiB managed volumes and extracted the Debian 13
  template.
- Proxmox warned that thin-pool auto-extension protection is not enabled and
  that provisioned thin-volume sizes exceed the physical pool. This is the
  previously recorded host risk; it remains open even though the operator had
  reviewed and accepted current capacity for this allocation.
- The provisioner then stopped during its immediate configuration validation
  with `existing VMID lacks nesting=1`. It did not start the guest, install
  Docker, create runtime configuration, start Studio, or change OWUI/Caddy.
- The cause was a provisioner feature-list parsing defect, not a reported
  Proxmox creation failure. The validator now strips the `features:` prefix and
  whitespace into a separate value before checking `keyctl=1` and
  `nesting=1`, matching the proven OWUI validator.
- Do not delete or recreate VMID `107`. Inspect it and continue only with the
  corrected provisioner's validated `--resume-existing` path.

## Corrected provisioning resume

- The corrected provisioner validated and resumed existing VMID `107`; it did
  not recreate the guest or its volumes.
- Docker Engine and Docker Compose were installed. Reported Compose version:
  `v5.3.1`.
- The immutable Studio OCI index was pulled successfully and Docker reported
  digest
  `sha256:9bbb5752adb54718df8cc00aaef746aed8629d4be558f1af34e586ccf4612462`,
  matching the published and independently inspected digest.
- Image platform, configured `studio` user, numeric runtime identity, and
  `/app/data` ownership checks passed inside the provisioner.
- The reviewed Compose manifest, systemd unit, deployment validation, health,
  install/update, and rollback commands were installed. The managed data
  directory passed the recorded `100:101:750` ownership and mode check.
- The provisioner completed at the intended runtime and identity stop gate.
  Non-secret host evidence:
  `/root/studio-provision-107-20260712T155120Z.evidence`.
- Studio was not started. No runtime environment, Studio database, OWUI OAuth
  configuration, Caddy route, or DNS record was created or changed.

Result: guarded LXC creation/resume, Docker/Compose installation, immutable
digest pull, image identity, managed storage preparation, and deployment-bundle
installation **pass**. Address reservation, identity configuration, first
deployment, database migration, health, routing, and product gates remain
open.

## Provisional network identity

- LXC `107` network: DHCP on `vmbr0`
- Observed address: `10.100.1.128/24`
- MAC: `BC:24:11:76:5A:C5`
- Interface state: up

The operator bound the observed MAC to `.128` in UniFi and rebooted LXC `107`.
After reboot, `eth0` was up at `10.100.1.128/24` and Docker was active.

Result: address reservation and guest reboot persistence **pass**. Use
`10.100.1.128:3000` as the eventual Caddy upstream only after local Studio
health passes.

## Selected identity inputs

- OIDC provider: Keycloak
- Realm: `homelab`
- Issuer URL: `https://auth.theoldschool.house/realms/homelab/`
- Dedicated Studio client ID: `studio-staging`
- Studio callback:
  `https://owui-stage.theoldschool.house/studio/auth/callback`
- Public origin: `https://owui-stage.theoldschool.house`
- Intended OWUI provider key: `oidc`

No client secret or session/encryption key is recorded. Studio requires a
32-byte base64-encoded `SESSION_ENCRYPTION_KEY`. OWUI token exchange remains
disabled until the separately reviewed OWUI identity change sets
`ENABLE_OAUTH_TOKEN_EXCHANGE=true`, configures the same provider, and links the
existing administrator to its Keycloak identity.

The operator created the dedicated Keycloak client with client authentication
and Authorization Code flow enabled, direct grants/implicit/service accounts
disabled, PKCE `S256`, exact callback
`https://owui-stage.theoldschool.house/studio/auth/callback`, and exact web
origin `https://owui-stage.theoldschool.house`. The current Studio logout is
local, so no Keycloak post-logout redirect was configured. The client secret
was not recorded.

## First Studio deployment

- Root-only `/etc/open-webui-studio/runtime.env` was created without displaying
  its values; reported ownership and mode: `root:root`, `0600`.
- The first deployment used the exact immutable reference
  `git.theoldschool.house/robert/open-webui-studio@sha256:9bbb5752adb54718df8cc00aaef746aed8629d4be558f1af34e586ccf4612462`.
- Docker confirmed the same digest and reported the local image up to date.
- The deployment stopped Studio for its consistent initial data archive, then
  started the pinned image. An early readiness probe received a connection
  reset; continued polling subsequently passed.
- Release record:
  `/var/backups/open-webui-studio-deploy/releases/20260712T161658Z.td2Vzx`.
- `open-webui-studio-compose.service` was enabled and returned `active`.
- The reviewed guest-local health command passed.
- LAN health at `http://10.100.1.128:3000/studio/health` returned only status
  `ok`, service `open-webui-studio`, and version `0.0.1`.

Result: root-only runtime configuration, first digest deployment, systemd
startup state, guest-local health, and LAN health **pass**. Migration/table
proof, OWUI OAuth/token exchange, Caddy routing, public health, authenticated
Studio behavior, Flow recovery, backup/restore, update, and rollback remain
open.

### Database bootstrap proof

A read-only query inside the running Studio container reported:

- migration `0007_flow_audit.sql` applied: true
- table `studio_flow_audit` present: true
- SQLite integrity check: `ok`

The first attempted read-only command was altered during console paste and
failed with an undefined JavaScript variable before querying. A single-line
replacement then produced the successful result above. Neither command wrote
to the database.

Result: fresh Studio database creation, required migration, audit-table
presence, and database integrity **pass**.

## Caddy path routing

After local and LAN Studio health passed, the operator replaced the OWUI-only
site handler with ordered same-origin routing:

1. `/studio` redirects to `/studio/`.
2. `/studio/*` proxies to `10.100.1.128:3000` without stripping the prefix and
   with response flushing for execution SSE.
3. The fallback proxies to OWUI at `10.100.1.103:8080`.

The operator reported all requested checks passed: Caddy configuration/reload,
the `/studio` redirect, public `/studio/health`, and the unchanged public OWUI
`/health` catch-all. No separate Studio hostname or DNS record was created.

Result: Caddy route ordering, same-origin Studio public health, and retained
OWUI catch-all health **pass by operator report**. Authenticated identity,
assets/cookies/request IDs, SSE reconnection, WebSockets, and product behavior
remain separate gates.

## OWUI Keycloak client preparation

The operator created a separate confidential Keycloak client `owui-staging` in
realm `homelab` with Authorization Code flow and PKCE `S256`. Its exact
callback is
`https://owui-stage.theoldschool.house/oauth/oidc/login/callback`, its exact
web origin is `https://owui-stage.theoldschool.house`, and its post-logout
redirect is the public OWUI root. Direct grants, implicit flow, authorization,
and service accounts are disabled. No client secret is recorded.

The planned account-linking sequence keeps OAuth signup disabled, temporarily
enables merge-by-email only to link the existing administrator after a
successful Keycloak login, then disables merge-by-email before testing Studio
token exchange. This identity gate has not yet passed.

### Studio issuer mismatch incident

The first Studio login attempt returned HTTP `500`. Bounded Studio logs showed
`ClientError: discovered metadata issuer does not match the expected issuer`.
Keycloak discovery advertises the realm issuer without a trailing slash, while
Studio had recorded the issuer with one. OIDC issuer comparison is exact. The
required correction is to change only `OIDC_ISSUER_URL` to
`https://auth.theoldschool.house/realms/homelab`, restart Studio, and retest.
No credential, token, cookie, authorization URL, or identity was recorded.

The operator applied the exact issuer without the trailing slash, restarted
Studio, and reported successful authenticated Studio access through Keycloak.
This proves Studio Authorization Code + PKCE callback completion, the existing
OWUI account link, OWUI provider-token exchange, Studio session creation, and
same-origin authenticated page delivery for the tested administrator. No
identity, token, cookie, or session value was recorded.

Result: first authenticated Studio login and OWUI token exchange **pass by
operator report**. Explicit confirmation that OAuth signup and temporary
merge-by-email are disabled remains required before the identity hardening gate
closes.

The first boolean-only hardening check reported OAuth signup disabled and token
exchange enabled, but merge-by-email still enabled. The operator then changed
only the named merge setting to false, restarted OWUI, and reported the repeat
check and OWUI health passed.

Result: OAuth signup disabled, one-time account linking complete,
merge-by-email disabled, token exchange enabled, and post-change OWUI health
**pass by operator report**. The tested administrator remains linked; no
identity or runtime value was recorded.

## Initial authenticated product baseline

The operator reported all requested pass/fail-only checks succeeded:

- models and agents visible in Studio;
- Media page loads;
- Flows page loads.

The same operator check also confirmed LiteLLM model discovery and one
authenticated chat in OWUI. No model names, prompts, outputs, user identities,
media identifiers, Flow data, credentials, cookies, or tokens were recorded.

Result: authenticated Studio catalogue/Agents, Media entry page, and Flows
entry page **pass by operator report**. Detailed Media behavior, Flow CRUD and
execution, isolation, SSE, cancellation, performance, and worker recovery
remain open.

### Flow CRUD and execution baseline

The operator reported all requested pass/fail-only Flow checks succeeded:

- disposable Flow creation and node configuration;
- save and canvas-position persistence after reload;
- edit and version-history advancement;
- execution with live progress;
- completion output and execution history;
- audit-history recording;
- deletion of the disposable Flow after verification.

No Flow name, definition, prompt, model, input, output, execution identifier,
audit content, user identity, credential, cookie, or token was recorded.

Result: Flow CRUD, canvas persistence, versioning, live progress, successful
execution, output/history, audit, and deletion **pass by operator report**.
Cancellation, isolation, deterministic checkpoint recovery, uncertain Model
dispatch recovery, and concurrency/performance remain open.

## Post-deployment reboot persistence

After the first deployment and product smoke, the operator rebooted LXC `107`.
Reported post-reboot results:

- LXC status: running
- `open-webui-studio-compose.service`: active
- systemd enablement: enabled
- reviewed guest-local Studio health: passed

Result: LXC, systemd, and guest-local Studio reboot persistence **pass**.
Post-reboot public Studio and OWUI health were requested but not included in
the reported output, so that final public portion remains pending.

## Parked backup work

The operator elected to park off-LXC backup selection and restore rehearsal.
No `vzdump`, backup copy, restore, or overwrite was attempted. The local
release records do not replace an off-LXC backup, and backup/restore acceptance
remains explicitly **open**. Fresh explicit approval is still required before
any restore that overwrites staging data.
