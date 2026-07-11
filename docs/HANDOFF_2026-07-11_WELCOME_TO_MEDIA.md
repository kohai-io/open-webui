# Handoff: Welcome complete, Media next

Date: 2026-07-11

## Current outcome

The Open WebUI v0.10.2 rebaseline is running locally with the full native Welcome experience. Welcome remains an optional OWUI UI island because it composes OWUI-owned workspace models, functions/pipes, chat, files, tools, dictation, and voice mode. Studio does not own duplicate agent records.

The user manually verified:

- shared Keycloak sign-in between OWUI and Studio;
- authorised model and workspace-agent visibility;
- the restored full Welcome layout and controls;
- ordinary file attachment handoff after the v0.10.2 Files API hardening.

No legacy data migration is in scope; deployments start fresh.

## Source state

### Open WebUI planning repository

- Repository: `https://git.theoldschool.house/robert/open-webui`
- Branch: `main`
- Welcome/plan reconciliation commit: `7da316134` (the handoff note itself is the following commit)
- Plan: `docs/OWUI_V0102_REBASELINE_AND_STUDIO_PLAN.md`
- Welcome maintenance options: `docs/welcome-feature-maintenance-options.md`

### Clean v0.10.2 rebaseline

- Worktree: `C:\tmp\owui-v0102-baseline`
- Branch: `rebaseline/upstream-v0.10.2`
- Upstream baseline: `v0.10.2` at `ecd48e2f7`
- Welcome commits:
  - `559cd28f1` — feature flag and initial native catalogue;
  - `e9ca2fc11` — full legacy Welcome restoration adapted to v0.10.2;
  - `3ccdbe83c` — ordering/query tests, Files API handoff hardening, and `PATCHES.md`.
- Patch register: `PATCHES.md`

### Studio

- Repository: `https://git.theoldschool.house/robert/open-webui-studio.git`
- Branch: `main`
- Corrected OWUI-owned agent integration: `abb86cc`
- Studio-owned agent experiment reverted by `0d74d7f`.

### Functions and tools

- Repository: `https://git.theoldschool.house/robert/open-webui-functions-tools`
- v0.10.2 Files API compatibility revision: `196b1a4`
- Branch: `codex/v0102-file-api-compat`
- Prompt scheduler removed; upstream Automations/Calendar is used instead.

## Local runtime

- Active container: `owui-v0102-studio-test`
- Image: `open-webui-local:v0102-welcome-hardened`
- URL: `http://localhost:8080/`
- Volume: `owui-v0102-studio-test-data`
- Feature flag: `ENABLE_WELCOME_PAGE=True`
- Health was passing at handoff.

Stopped rollback containers were intentionally retained:

- `owui-v0102-full-backup`
- `owui-v0102-catalogue-backup`
- `owui-v0102-studio-test-backup`

Do not print or copy container environment values. OIDC secrets remain only in existing ignored/local configuration and container state.

The Keycloak test realm is `homelab`; local client names use the `-local` suffix. Okta remains the intended deployment provider but is not yet available for live conformance testing.

## Verification evidence

- Welcome classifier/order/query suite: four focused Vitest tests passing.
- Full OWUI Vite production build passing.
- Hardened Docker image built successfully.
- Container health endpoint and home page returned successfully.
- Manual UI verification completed by the user.

Do not use browser automation in the next session unless the user explicitly reverses this instruction; it repeatedly crashed the Codex desktop app. Prefer source tests, HTTP checks, Docker health/logs, and user-led manual UI verification.

## Open Welcome checks

- Two-user end-to-end proof with different group/model grants.
- Explicit permission-denied and upstream-unavailable presentation states.
- Mobile manual verification.
- Okta conformance when an Okta test application is available.

These checks do not block starting the Media contract review.

## Next slice: Phase 6 Media contract

Start with a read-only comparison; do not port the Media UI first.

1. Inventory the legacy Media page, services, metadata expectations, preview behavior, and timeline references.
2. Compare them with v0.10.2 Files API listing, pagination, content, download, deletion, processing status, metadata, and access-control behavior.
3. Review the already patched media-related pipe functions at revision `196b1a4`.
4. Define a minimal paginated, user-scoped Studio Media adapter contract.
5. Document only genuinely missing bridge endpoints; do not add direct OWUI database access.
6. Add adapter fixtures and permission tests before implementing Media UI.
7. Keep OWUI as file/permission owner. Studio will own timeline projects, tracks, clips, markers, and versions using opaque OWUI file IDs.
