# Handoff: Phase 9 OWUI and Studio Proxmox staging live

Date: 2026-07-12

## Current outcome

Both Phase 9 staging services are live on `pve2` as separate unprivileged
Debian 13 LXCs using exact immutable OCI digests and independent managed data
volumes.

- Open WebUI runs in LXC `105` at `10.100.1.103:8080`.
- Studio runs in LXC `107` at `10.100.1.128:3000`.
- Caddy serves both from `https://owui-stage.theoldschool.house`.
- `/studio` redirects to `/studio/`; `/studio/*` routes to Studio before the
  OWUI catch-all.
- Keycloak realm `homelab` provides shared login. Separate confidential clients
  are used for OWUI and Studio.
- OWUI first-admin/signup closure, LiteLLM discovery, authenticated chat,
  reboot persistence, and local/public health pass.
- Studio image publication, guarded LXC provisioning, database bootstrap,
  migration/audit-table proof, systemd/local/LAN/public health, Keycloak login,
  OWUI token exchange, core pages, and the first Flow CRUD/execution baseline
  pass.

Do not call Phase 9 complete. Backup/restore is parked; update/rollback,
cancellation, worker recovery, isolation, performance, and final legacy route
rollback remain open.

## Repository state

### Planning and deployment repository

- Worktree: `C:\Users\Robert\dev\AI\open-webui\open-webui`
- Branch: `main`
- HEAD: `ef8d79904 feat: add proxmox staging deployment bundle`
- HEAD remains one commit ahead of `origin/main` and unpushed.
- Phase 9 documentation, provisioners, evidence, Portainer evaluation, and
  transfer archives remain uncommitted/untracked as shown by `git status`.
- Preserve every existing change, including the formatting-only plan change
  that predated this rehearsal.
- Do not commit or push unless explicitly requested.

Current transfer artifacts:

- OWUI: `owui-proxmox-bundle-ef8d79904-20260712-r5.tar.gz`, SHA-256
  `5ec9e01ab6b17f035de6a194f5931a1455cf4ad44f086b7a7ee060350536c841`.
- Studio: `studio-proxmox-bundle-ef8d79904-20260712-r3.tar.gz`, SHA-256
  `e81b411c4e7514d7e09d7385af5d9f96199b71dd0f93941d989889b8cfec7f5a`.

Earlier OWUI archives and Studio `r1`/`r2` are obsolete. Studio `r2` contains
the feature-validation defect found during the first LXC creation attempt.

### Maintained Open WebUI

- Worktree: `C:\tmp\owui-v0102-baseline`
- Branch: `rebaseline/upstream-v0.10.2`
- Commit: `6dca01731e6d38aca8b2b7094e409c306ce78936`
- Upstream base: `v0.10.2` at
  `ecd48e2f718220a6400ecf49eafd4867a38feb10`
- Retained feature: disabled-by-default native Welcome UI island

### Studio

- Worktree: `C:\tmp\open-webui-studio-flows`
- State: clean detached checkout
- Exact published commit: `bf7dd04aca6a96aaaae13c4cbb21a3d464660af2`
- The broken worktree was replaced by a fresh exact-commit clone. The former
  directory is retained at `C:\tmp\open-webui-studio-flows-broken-20260712`.
- Zero-warning static checks and all 130 server tests across 25 files passed.
- Local production build and non-root `/studio/health` smoke passed.

Do not inspect or print resolved environments from local or Proxmox
containers.

## Immutable artifacts

### OWUI

- Source revision: `6dca01731e6d38aca8b2b7094e409c306ce78936`
- Deployment reference:
  `git.theoldschool.house/robert/open-webui@sha256:012e5f80e9aaf508c5831fde9440a78fea3b7ff2f4b2a8ca451758e904e696c9`
- Linux/amd64 manifest:
  `sha256:8943412db6b612dd8cbc5f5784d170a9a2e3e3ac91709998af5e46db80a138a3`
- Attestation manifest:
  `sha256:18cd47313e962eaae3383a5a1dc46a8b500bdbbddb3a2b3c219d1026b0a2f057`
- Runtime identity: `1000:1000`

### Studio

- Source revision: `bf7dd04aca6a96aaaae13c4cbb21a3d464660af2`
- Publication received fresh explicit approval.
- Deployment reference:
  `git.theoldschool.house/robert/open-webui-studio@sha256:9bbb5752adb54718df8cc00aaef746aed8629d4be558f1af34e586ccf4612462`
- Linux/amd64 manifest:
  `sha256:fba9290f49fe922d338b9987a5df95f9e1943a16631eda053c3f45ac2efef949`
- Attestation manifest:
  `sha256:7601e72eb04c5ede95fb4db9a2a32152eb56de03e9a2a0321e34a470a2c19165`
- Configured user: `studio`; numeric runtime identity `100:101`
- Image-owned `/app/data`: `100:101`, mode `0755`

No further repository or image push is authorized by either prior approval.

## Proxmox topology

### Host

- Node: `pve2`
- Proxmox VE: `8.4.19`
- Kernel: `6.8.12-23-pve`
- Caddy source/host: `10.100.1.20`
- DNS resolvers: `10.100.1.21`, `10.100.1.22`
- Bridge: `vmbr0`

The host warns that LVM thin-pool auto-extension protection is not enabled.
During Studio creation it also reported total provisioned thin volumes of
372 GiB exceeding the thin pool and only 16 GiB free in the volume group. The
operator reviewed and accepted capacity for the 20 GiB Studio allocation, but
the overcommit/auto-extension risk remains open. Do not allocate more storage
without a fresh capacity review.

### OWUI LXC 105

- Hostname: `owui-staging`
- Address/MAC: `10.100.1.103/24`, `BC:24:11:B0:A4:9C`
- Resources: 4 vCPU, 8192 MiB RAM, 1024 MiB swap
- Root: 24 GiB on `local-lvm`
- Managed data: 16 GiB on `local-lvm` at `/srv/open-webui`, `backup=1`
- Features: `nesting=1,keyctl=1`; no device passthrough
- Runtime file: `/etc/open-webui/runtime.env`, root-owned mode `0600`
- Service: `open-webui-compose.service`, active and enabled
- First release:
  `/var/backups/open-webui-deploy/releases/20260712T150852Z.8lqGqJ`
- Provisioning evidence:
  `/root/owui-provision-105-20260712T145547Z.evidence`

OWUI now has Keycloak OIDC and provider-token exchange enabled. Public OAuth
signup and merge-by-email are disabled. The existing administrator was linked
once using temporary merge-by-email, then the setting was returned to false.
No runtime value was recorded.

### Studio LXC 107

- Hostname: `studio-staging`
- Address/MAC: `10.100.1.128/24`, `BC:24:11:76:5A:C5`
- The UniFi reservation persisted across reboot.
- Resources: 2 vCPU, 4096 MiB RAM, 512 MiB swap
- Root: 12 GiB on `local-lvm`
- Managed data: 8 GiB on `local-lvm` at `/srv/open-webui-studio`, `backup=1`
- Features: `nesting=1,keyctl=1`; no device passthrough
- Runtime file: `/etc/open-webui-studio/runtime.env`, root-owned mode `0600`
- Data directory: `/srv/open-webui-studio/data`, `100:101`, mode `0750`
- Service: `open-webui-studio-compose.service`, active and enabled
- First release:
  `/var/backups/open-webui-studio-deploy/releases/20260712T161658Z.td2Vzx`
- Provisioning evidence:
  `/root/studio-provision-107-20260712T155120Z.evidence`
- Docker Compose reported version `v5.3.1`.

Post-deployment reboot proof: LXC running, Studio unit active/enabled, and
guest-local health passed. The requested post-reboot public curl output was not
separately captured, although authenticated public UI/Flow tests passed later.

Keep legacy LXC `106` unchanged as the final routing rollback. Keep reference
LXC `118` unless fresh approval is given to stop or archive it. Do not recreate
LXC `105` or `107`.

## Public routing and identity

Public origin: `https://owui-stage.theoldschool.house`

Caddy route order:

1. `/studio` redirects to `/studio/`.
2. `/studio/*` proxies to `10.100.1.128:3000`, preserving the prefix and using
   response flushing for Flow SSE.
3. The fallback proxies to OWUI at `10.100.1.103:8080`.

There is no separate Studio public hostname or DNS record. The operator
reported Caddy validation/reload, redirect, public Studio health, and unchanged
OWUI health passed.

Keycloak:

- Realm issuer: `https://auth.theoldschool.house/realms/homelab` (no trailing
  slash; discovery issuer comparison is exact).
- Studio client: `studio-staging`; callback
  `https://owui-stage.theoldschool.house/studio/auth/callback`.
- OWUI client: `owui-staging`; current callback
  `https://owui-stage.theoldschool.house/oauth/oidc/login/callback`; the legacy
  `/oauth/oidc/callback` alias is also allowed in Keycloak.
- Both clients are confidential, Authorization Code + PKCE `S256`, with
  direct grants, implicit flow, authorization services, and service accounts
  disabled.
- Studio logout is currently local; no Keycloak post-logout URI is needed for
  the Studio client.

Never record either client secret, session key, token, cookie, authorization
URL, code, state, or identity.

## Completed acceptance evidence

### OWUI

- Guarded creation, Docker/Compose, registry trust, immutable pull, non-root
  identity, managed data, bundle installation, and first deployment passed.
- Local and public health, systemd enablement, and LXC reboot persistence
  passed.
- First administrator creation and automatic public-signup closure passed.
- Retained Welcome page passed.
- LiteLLM model discovery and one authenticated chat passed by operator report.
- Keycloak login linked the existing administrator; OAuth signup and
  merge-by-email are now disabled; token exchange remains enabled.

No identity, model name, prompt, response, or secret was recorded.

### Studio

- Exact image publication, guarded LXC creation/resume, Docker/Compose,
  immutable pull, runtime identity, managed data, and bundle installation
  passed.
- Root-only runtime configuration and first digest deployment passed.
- Local, LAN, and public `/studio/health` passed.
- Migration `0007_flow_audit.sql`, table `studio_flow_audit`, and SQLite
  integrity `ok` passed through a read-only query.
- Caddy same-origin route and OWUI catch-all health passed.
- Keycloak Authorization Code + PKCE, OWUI provider-token exchange, Studio
  session creation, and first authenticated page load passed.
- Models/Agents visibility and Media/Flows entry pages passed by operator
  report.
- Disposable Flow creation/configuration, save, canvas persistence, edit,
  version advancement, live execution progress, completion output/history,
  audit history, and deletion passed by operator report.
- Post-deployment LXC/systemd/local-health reboot persistence passed.

No Flow name, definition, prompt, model, input, output, execution ID, audit
content, identity, credential, cookie, or token was recorded.

## Incidents and corrections

### OWUI

1. Restrictive inherited `umask` made `/etc` inaccessible to `_apt`; the OWUI
   provisioner now uses `umask 022`, normalizes resolver access, and makes APT
   failures fatal.
2. The original 8 GiB root could not extract the OWUI image. The accepted
   replacement is 24 GiB root plus 16 GiB managed data.
3. A disk-full pull was incorrectly treated as possible registry-auth failure;
   that fallback was removed.
4. Recreating disposable VMID `105` changed its MAC; `.103` with MAC suffix
   `a4:9c` is the accepted guest. Do not recreate it.

### Studio

1. The first `provision-studio-lxc.sh` creation made VMID `107` and both
   volumes, then stopped before guest startup because its feature-list parser
   falsely reported missing `nesting=1`. The corrected `r3` provisioner used
   validated `--resume-existing`; VMID `107` was not recreated.
2. The first database query was altered during console paste and failed before
   reading; a single-line read-only query then passed.
3. The initial Studio login returned HTTP 500 because
   `OIDC_ISSUER_URL` had a trailing slash while Keycloak discovery did not.
   Removing the slash fixed exact issuer matching.
4. Keycloak initially rejected the OWUI redirect URI. Allowing the current and
   legacy exact OWUI callback aliases resolved it.
5. The first hardening check found merge-by-email still enabled after account
   linking. It was immediately set false, OWUI restarted, and health passed.

## Parked and open work

Backup work is parked by operator decision. No `vzdump`, off-LXC copy, restore,
or overwrite was attempted. Local release records are not off-LXC backups.
Backup/restore acceptance remains open, and fresh explicit approval is required
immediately before any restore that overwrites staging data.

Next-session order:

1. Capture explicit post-reboot public health for Studio and OWUI if desired to
   remove the small evidence gap.
2. Run Flow cancellation. If work completes before cancellation can be
   selected, record `not tested` rather than pass.
3. Rehearse deterministic checkpoint recovery and the uncertain Model-call
   case. The latter must end as `model_result_unknown` without redispatch.
4. Run two-user isolation for Studio Media, Flow, execution events, and audit;
   verify hidden/denied behavior without recording identities or object IDs.
5. Complete Media preview/download/pagination and proxy cookie/request-ID/SSE
   reconnection checks.
6. Record concurrency, long-SSE, startup, disk-growth, and interruption timing.
7. Prepare distinct OWUI and Studio update candidates. Obtain fresh explicit
   approval before either image push. Do not redeploy the current digest.
8. Rehearse stopped-service archive, candidate health/rejection, and paired
   image/data rollback. Obtain fresh explicit approval immediately before each
   rollback or restore that overwrites staging data.
9. When backup work resumes, select a named off-LXC target and prove `mp0`
   inclusion through an actual restore rehearsal.
10. Rehearse final Caddy routing rollback to unchanged legacy LXC `106` without
    copying new data into legacy storage.

Still-open Phase 9 gates:

- Flow cancellation and worker recovery.
- Studio two-user isolation and detailed Media/proxy/performance acceptance.
- OWUI and Studio update plus paired image/data rollback.
- Named off-LXC backup and restore proof; currently parked.
- Resource timings and maintenance-window estimate.
- Final routing rollback to unchanged legacy LXC `106`.
- Repeat fresh-data bootstrap remains required by the full deployment contract
  unless scope is explicitly amended.

## Boundaries

- Do not inspect, print, copy, log, or commit resolved environment values,
  passwords, tokens, cookies, authorization URLs, codes, states, or registry
  credentials.
- Do not commit/push this repository or publish another image without fresh
  explicit approval.
- Do not use mutable image references such as `main` or `latest`.
- Do not run, source, vendor, or adapt the Proxmox Community Scripts installer.
- Do not import legacy users, chats, files, Knowledge, flows, schedules,
  preferences, OAuth state, or encryption keys.
- Do not share or mount OWUI storage in Studio.
- Do not restore an older image against forward-migrated data unless that exact
  image/data pair passed rollback rehearsal.
- Keep legacy LXC `106` unchanged and reference LXC `118` running unless fresh
  approval says otherwise.
- Do not recreate LXC `105` or `107`.
- Do not use the in-app browser unless explicitly requested.
- Do not claim backup, restore, update, rollback, cancellation, worker recovery,
  isolation, performance, or final routing rollback gates until rehearsed and
  recorded.
