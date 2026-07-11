# Handoff: Phase 9 Proxmox rehearsal ready

Date: 2026-07-12

## Current outcome

Phase 7 Flows and Phase 8's minimal OWUI patch gate are complete. The user
finished the authenticated Flow canvas confidence check, and the OWUI and
Studio feature branches are published.

Phase 9 now has a selected staging topology, a deployment contract, and a
version-controlled deployment bundle. The next operator should test the
bundle in disposable Proxmox LXCs. No Proxmox resource, image publication,
proxy change, or production deployment has occurred.

## Source state

### Planning and deployment repository

- Worktree: `C:\Users\Robert\dev\AI\open-webui\open-webui`
- Branch: `main`
- Published base before this handoff: `90abaa923`
- The commit containing this document adds the Phase 8 audit, reconciles the
  plan and feature ledger, records the Flow UI confidence check, and adds the
  Phase 9 Proxmox contract and deployment bundle.
- This new planning commit remains local until the user gives fresh approval
  to push it to the configured private Gitea origin.

### Maintained Open WebUI

- Worktree: `C:\tmp\owui-v0102-baseline`
- Branch: `rebaseline/upstream-v0.10.2`
- Commit: `6dca01731e6d38aca8b2b7094e409c306ce78936`
- Upstream base: `v0.10.2` at
  `ecd48e2f718220a6400ecf49eafd4867a38feb10`
- State at handoff: clean and synchronized with
  `origin/rebaseline/upstream-v0.10.2`
- Retained patch: the disabled-by-default native Welcome UI island documented
  in branch `PATCHES.md` and `docs/phase-8-minimal-owui-patch-audit.md`

### Studio

- Worktree: `C:\tmp\open-webui-studio-flows`
- Branch: `codex/flows-foundation`
- Commit: `bf7dd04aca6a96aaaae13c4cbb21a3d464660af2`
- State at handoff: clean and synchronized with
  `origin/codex/flows-foundation`
- This commit includes the editable Svelte Flow canvas, durable execution,
  owner-scoped APIs and SSE, fixed-column audit history, and the automated
  Phase 7 lifecycle gate.

## Completed product gates

### Phase 7

- 130 Studio server tests pass.
- Svelte check reports no errors or warnings.
- Full ESLint and production build pass.
- Flow definitions, versions, executions, checkpoints, credential leases,
  events, and audit data remain Studio-owned.
- The user confirmed node and edge editing, incident-edge cleanup, settings
  persistence, position reload, live execution progress, output, and history.
- Deferred node types remain outside the admitted contract.

### Phase 8

- The maintained OWUI branch contains one feature: the native Welcome UI
  island behind `ENABLE_WELCOME_PAGE`.
- The retained diff adds no database domain, background job, package change,
  static branding asset, Pi Gateway surface, or MCP/OAuth patch.
- The user parked Pi Gateway. Keep it in the immutable legacy reference.
- The MCP unique-suffix resolver stays conditional on a staging reproduction.
- `docs/phase-8-minimal-owui-patch-audit.md` records the gate evidence.

## Local test deployment

The local containers were checked on 2026-07-12 without reading their
environments:

| Service | Container                | Image                                | Address                         | State               |
| ------- | ------------------------ | ------------------------------------ | ------------------------------- | ------------------- |
| OWUI    | `owui-v0102-studio-test` | `open-webui-local:v0102-welcome-nav` | `http://localhost:8080/`        | running and healthy |
| Studio  | `owui-studio-media-test` | `open-webui-studio:flows-ui-local`   | `http://localhost:5173/studio/` | running and healthy |

Keep the existing local data volumes and rollback containers unchanged unless
the user asks for a new local deployment operation. Do not print or copy
container environment values.

## Proxmox staging decision

Use two unprivileged Debian 13 LXCs:

| LXC              | Initial resources         | Service                                            | Data boundary                                                          |
| ---------------- | ------------------------- | -------------------------------------------------- | ---------------------------------------------------------------------- |
| `owui-staging`   | 4 vCPU, 8 GiB RAM, 50 GiB | OWUI on port 8080                                  | `/srv/open-webui/data` on a Proxmox-managed local block volume         |
| `studio-staging` | 2 vCPU, 4 GiB RAM, 20 GiB | Studio and its in-process Flow worker on port 3000 | `/srv/open-webui-studio/data` on a separate managed local block volume |

The existing reverse proxy will route `/studio/*` to Studio before routing the
remaining paths to OWUI. Keep the identity provider, model providers, and
legacy deployment outside the new LXCs.

The Proxmox Community Scripts Open WebUI installer informed the initial LXC
sizing. Do not execute or vendor it. It fetches mutable public scripts and
installs the current package, so it cannot reproduce the pinned Gitea builds.

Read `docs/proxmox-staging-deployment-contract.md` for the topology, proxy,
storage, backup, bootstrap, acceptance, and rollback rules.

## Deployment bundle

`deploy/proxmox` contains:

- separate OWUI and Studio Compose manifests;
- systemd unit templates with boot-time deployment validation; operators must
  install them as root-owned files;
- variable-name and sensitivity inventories with no values;
- `install-or-update.sh`, which accepts an explicit OCI manifest digest;
- a stopped-service data archive and release record for each update;
- `health-check.sh` for local readiness;
- `rollback.sh`, which verifies the archive checksum, restores the previous
  image/data pair, and preserves rejected candidate data;
- `REHEARSAL_CHECKLIST.md` for the two disposable LXCs.

The update command rejects floating tags, including `main` and `latest`.
Studio updates require `--confirm-studio-idle` after the operator proves that
no Flow is queued, running, or awaiting cancellation. Rollback requires
`--confirm-restore-data`.

The bundle does not create LXCs, configure DNS or the proxy, render secrets,
build images, or publish images.

## Validation completed

- `bash -n` passes for all deployment scripts.
- The digest validator accepts a 64-character lowercase SHA-256 reference and
  rejects a floating tag.
- Static checks found no recursive deletion, remote-script sourcing, `eval`,
  trace mode, resolved Compose output, or floating runtime image reference.
- Deployment shell files use LF line endings.
- New Markdown and YAML files pass Prettier parsing and formatting.
- `git diff --check` passes.
- Both local application containers report healthy.

The workstation has no Docker Compose v2 plugin or systemd runtime. Compose,
systemd, backup, restore, and rollback execution remain Proxmox rehearsal
work. Do not treat static validation as deployment evidence.

## Inputs required from the operator

Record these without secret values:

- Proxmox node and version;
- LXC IDs and hostnames;
- storage pool and managed volume names;
- bridge, VLAN, internal addresses, and firewall policy;
- public staging DNS names and reverse-proxy host;
- private OCI registry and its certificate trust path;
- secret-store owner and secret-reference names;
- intended OWUI model, OAuth, MCP, file, and notification integrations.

## Next task

Start with the disposable OWUI LXC:

1. Select and record the host inputs above.
2. Build the OWUI image from the clean Gitea checkout at `6dca01731` with a
   recorded non-root UID/GID.
3. Publish the image only after the user approves registry publication.
4. Record the registry manifest digest.
5. Provision the unprivileged Debian 13 OWUI LXC and its managed data volume.
6. Install the bundle files as described in `deploy/proxmox/README.md`.
7. Render `/etc/open-webui/runtime.env` from the secret store without printing
   it.
8. Run the first digest deployment and complete the OWUI sections of
   `deploy/proxmox/REHEARSAL_CHECKLIST.md`.

Proceed to the Studio LXC after OWUI passes local and public-origin checks.
Build Studio from `bf7dd04`, publish it with fresh approval, and repeat the
empty-data, update, worker-recovery, backup, and rollback checks.

## Boundaries

- Do not push a repository or publish an image without fresh approval.
- Do not print, copy, or commit environment values, tokens, cookies, or
  registry credentials.
- Do not import legacy users, chats, files, Knowledge, flows, schedules,
  preferences, OAuth state, or encryption keys.
- Do not share or mount OWUI storage in Studio.
- Do not use mutable image tags.
- Do not start an old image against a forward-migrated database unless that
  image/schema pair passed a rollback rehearsal.
- Do not restore Pi Gateway or deferred Flow node types during staging work.
- Keep the legacy deployment unchanged so proxy routing remains the final
  rollback path.
