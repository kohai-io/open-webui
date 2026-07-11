# Proxmox disposable-LXC rehearsal checklist

Record evidence without secret values. Keep proxy traffic in maintenance mode
until the public-origin smoke tests pass.

## Host inputs

- [ ] Record Proxmox node and version.
- [ ] Record both LXC IDs, hostnames, OS template digest, and unprivileged state.
- [ ] Record CPU, RAM, root disk, managed data volume, and backup target.
- [ ] Record bridge, VLAN, internal addresses, firewall rules, and proxy source.
- [ ] Record public staging names, certificate owner, private registry, and
      secret-store owner.

## Artifact evidence

- [ ] Confirm the OWUI checkout is clean at full commit `6dca01731...`.
- [ ] Confirm the Studio checkout is clean at full commit `bf7dd04...`.
- [ ] Record build commands, builder, architecture, build arguments, and base
      image digests.
- [ ] Record the two private registry manifest digests.
- [ ] Confirm both manifests use `registry/repository@sha256:<digest>`.
- [ ] Confirm OWUI and Studio run as the recorded non-root identities.

## Empty bootstrap

- [ ] Take a pre-install Proxmox backup of each empty LXC.
- [ ] Confirm both data directories are empty and independent.
- [ ] Render runtime environments from the secret store with mode 0400 or 0600.
- [ ] Run the first digest deployment for OWUI.
- [ ] Record OWUI migration head and `/health` result.
- [ ] Create the first administrator through the supported interface.
- [ ] Configure representative users, groups, providers, models, files,
      Knowledge, Automations, Skills, OAuth, and MCP from scratch.
- [ ] Run the first digest deployment for Studio.
- [ ] Record Studio migration `0007_flow_audit.sql`, `studio_flow_audit`, and
      `/studio/health` result.
- [ ] Copy local release backups to the selected backup target.

## Proxy and identity

- [ ] Route `/studio/*` to Studio before the catch-all OWUI route.
- [ ] Verify `/studio` redirects to `/studio/`.
- [ ] Verify direct page loads, assets, request IDs, secure cookies, and OIDC
      callback URLs through the public origin.
- [ ] Verify OWUI WebSocket or Socket.IO upgrades.
- [ ] Verify Flow SSE remains unbuffered and reconnects.
- [ ] Verify representative upload size and timeout behaviour.
- [ ] Verify shared login, logout, expiry, disabled-account denial, and two-user
      resource isolation.

## Product acceptance

- [ ] Verify Welcome with the feature flag enabled and disabled.
- [ ] Verify model grants, chat streaming, file attachment, Knowledge,
      Automations, Skills, OAuth, MCP, and administrator denial boundaries.
- [ ] Verify Studio Media list, preview, download, pagination, and cross-user
      hidden responses.
- [ ] Verify Flow create, edit, position persistence, versioning, execution,
      live progress, output, history, cancellation, deletion, and audit history.
- [ ] Test the intended staging model's MCP tool-name behaviour before proposing
      a resolver patch.

## Update rehearsal

- [ ] Publish a second OWUI digest from an approved no-op or documented change.
- [ ] Enter maintenance mode and update OWUI by digest.
- [ ] Record image-pull time, stopped-service backup time, migration time,
      health time, and total interruption.
- [ ] Confirm Studio remains healthy while OWUI updates and reports the expected
      upstream-unavailable state during the interruption.
- [ ] Publish a second Studio digest from an approved no-op or documented change.
- [ ] Confirm no Flow is queued, running, or awaiting cancellation.
- [ ] Update Studio with `--confirm-studio-idle` and record timings.
- [ ] Confirm OWUI remains available while Studio updates.

## Worker recovery

- [ ] Run a Flow to a deterministic checkpoint and stop Studio.
- [ ] Start the same Studio digest and verify checkpoint recovery.
- [ ] Rehearse an interrupted Model dispatch and verify
      `model_result_unknown` without a second dispatch.
- [ ] Verify audit and execution history after recovery.

## Rollback rehearsal

- [ ] Reject or break a disposable OWUI candidate, confirm the updater stops it,
      and run checksum-verified OWUI rollback.
- [ ] Confirm the previous OWUI digest and paired data pass public smoke tests.
- [ ] Reject or break a disposable Studio candidate and run Studio rollback.
- [ ] Confirm the previous Studio digest, paired database, Flow history, and
      audit rows pass public smoke tests.
- [ ] Confirm each rollback preserves candidate data under its failed-data path.
- [ ] Restore both LXCs from the off-LXC Proxmox backup and verify managed-volume
      inclusion.
- [ ] Switch staging proxy routes to the untouched legacy deployment and record
      the interruption without copying new data back.

## Repeatability

- [ ] Destroy only the disposable staging data and LXCs.
- [ ] Repeat the empty bootstrap from the recorded artifacts and configuration
      names.
- [ ] Compare timings and resolve unexplained differences.
- [ ] Attach the final evidence to Phase 9 without recording secret values.
