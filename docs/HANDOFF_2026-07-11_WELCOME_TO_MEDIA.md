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
- Welcome/plan reconciliation commit: `7da316134`
- Original handoff commit: `3c0bc5eb4`; this document is maintained as Phase 6 progresses.
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
- Media adapter contract: `5b5bb4e` on `codex/media-adapter-contract`.
- Container native-dependency packaging fix: `08a332f` on the same branch.

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

Studio Media adapter test runtime:

- Active container: `owui-studio-media-test`
- Image: `open-webui-studio:media-adapter-08a332f`
- URL: `http://localhost:5173/studio/`
- Volume: `owui-studio-media-test-data`
- Runs as the unprivileged `studio` user.
- Studio page, health endpoint, OWUI reachability, OIDC discovery, and the Keycloak login redirect were passing. The container preserves the existing public origin and overrides only the non-secret container-to-host OWUI URL.

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
- Manual UI verification completed by the user in Chrome at normal and responsive/narrow widths.
- Studio Media adapter: 11 focused tests passing; full Studio server suite: 21 tests passing; Svelte check and changed-file ESLint passing.
- Studio image `open-webui-studio:media-adapter-08a332f` built successfully; the real Studio page and health endpoint return `200` from the healthy non-root container.

Do not use browser automation in the next session unless the user explicitly reverses this instruction; it repeatedly crashed the Codex desktop app. Prefer source tests, HTTP checks, Docker health/logs, and user-led manual UI verification.

## Open Welcome checks

- Two-user end-to-end proof with different group/model grants.
- Explicit permission-denied and upstream-unavailable presentation states.
- Physical-device mobile verification.
- Okta conformance when an Okta test application is available.

These checks do not block starting the Media contract review.

## Next slice: Phase 6 Media contract

Start with a read-only comparison; do not port the Media UI first.

The first Studio Media release is read-only apart from downloading: it lists, searches, previews, and downloads media already stored in OWUI. Upload, deletion, generation, transcription, narration, and other processing controls are out of scope for this release.

The read-only comparison and first-release contract are now recorded in `docs/media-contract-review.md`. Items 1 through 6 below are complete; resume by adding authenticated Studio Media server routes before implementing UI.

1. Inventory the legacy Media page, services, metadata expectations, preview behavior, and timeline references from the immutable `legacy/v0.6.36-custom` reference at `7f562ebb5c0893a886adc02521251fce7b725cb2`.
2. Compare them with v0.10.2 Files API listing, pagination, content, download, deletion, processing status, metadata, and access-control behavior.
3. Review the media-related pipes, action, and tools patched at revision `196b1a4` to understand the OWUI files and metadata they produce; invoking them from Studio is out of scope for the first release.
4. Audit and extend the existing typed, paginated, user-scoped Studio files adapter and the contract in `docs/owui-studio-contract.md`; do not create a second adapter or permission model.
5. Document only genuinely missing bridge endpoints; do not add direct OWUI database access.
6. Extend the existing adapter fixtures and permission tests for Media-specific listing, search, preview, download, pagination, missing files, and cross-user denial before implementing Media UI.
7. Keep OWUI as file/permission owner. Studio will own timeline projects, tracks, clips, markers, and versions using opaque OWUI file IDs.
