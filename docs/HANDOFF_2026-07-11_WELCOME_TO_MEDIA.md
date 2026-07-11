# Handoff: Media browser complete, Flows selected

Date: 2026-07-11

## Current outcome

The Open WebUI v0.10.2 rebaseline is running locally with the full native Welcome experience. Welcome remains an optional OWUI UI island because it composes OWUI-owned workspace models, functions/pipes, chat, files, tools, dictation, and voice mode. Studio does not own duplicate agent records.

The first Studio Media browser slice is also complete. It lists, searches, previews, and downloads self-owned OWUI image/video/audio files through the typed server-side adapter. It has no upload, deletion, generation, transcription, narration, or other processing controls. OWUI remains the file, storage, and permission owner.

The user parked timeline persistence after review and selected Phase 7 Flows as the next product slice. `docs/flow-extraction-contract.md` records its contract-first boundary.

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
  - `da39eb4a1` — restore distinct sidebar New Chat and Welcome navigation.
  - `6dca01731` — update the retained patch register.
- Patch register: `PATCHES.md`

### Studio

- Repository: `https://git.theoldschool.house/robert/open-webui-studio.git`
- Worktree: `C:\Users\Robert\dev\AI\open-webui\open-webui-studio`
- Base branch: `main` at `abb86cc`
- Active local branch: `codex/media-adapter-contract`
- Published branch: `origin/codex/media-adapter-contract`.
- Corrected OWUI-owned agent integration: `abb86cc`
- Studio-owned agent experiment reverted by `0d74d7f`.
- Media adapter contract: `5b5bb4e` on `codex/media-adapter-contract`.
- Container native-dependency packaging fix: `08a332f` on the same branch.
- First Studio Media page: `278be05` on the same branch.
- Representative-library performance hardening: `57f7673` on the same branch.
- Deleted-file preview race proof: `dc082a9` on the same branch.

### Functions and tools

- Repository: `https://git.theoldschool.house/robert/open-webui-functions-tools`
- v0.10.2 Files API compatibility revision: `196b1a4`
- Branch: `codex/v0102-file-api-compat`
- Prompt scheduler removed; upstream Automations/Calendar is used instead.

## Local runtime

- Active container: `owui-v0102-studio-test`
- Image: `open-webui-local:v0102-welcome-nav`
- URL: `http://localhost:8080/`
- Volume: `owui-v0102-studio-test-data`
- Feature flag: `ENABLE_WELCOME_PAGE=True`
- Health was passing at handoff.
- Local CORS now admits `http://localhost:5173` and `http://localhost:8080`; an origin-bearing Socket.IO WebSocket handshake passes.

Studio Media adapter test runtime:

- Active container: `owui-studio-media-test`
- Image: `open-webui-studio:media-perf-57f7673`
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
- Studio Media adapter and page service: 16 focused tests passing; full Studio server suite: 26 tests passing; Svelte check, changed-file ESLint, and production build passing.
- A 1,250-record mixed-library fixture proves 500-record scan bounds, opaque continuation across sparse administrator results, sequential upstream concurrency of one, and cancellation without retry/remapping.
- Studio image `open-webui-studio:media-perf-57f7673` built successfully. `/studio/media` and the health endpoint return `200`, grid cards do not preload full media bodies, unauthenticated content returns `401`, and the healthy non-root container can reach OWUI and OIDC.
- The user manually verified the authenticated Media page, previews, and downloads.
- The user manually verified two-user media separation and confirmed a direct cross-user content URL returns a hidden `404`.

Do not use browser automation in the next session unless the user explicitly reverses this instruction; it repeatedly crashed the Codex desktop app. Prefer source tests, HTTP checks, Docker health/logs, and user-led manual UI verification.

## Open Welcome checks

- Two-user end-to-end proof with different group/model grants.
- Explicit permission-denied and upstream-unavailable presentation states.
- Physical-device mobile verification.
- Okta conformance when an Okta test application is available.

These checks do not block starting timeline persistence.

## Completed Phase 6 slice: Media browser

The first Studio Media release is read-only apart from downloading: it lists, searches, previews, and downloads media already stored in OWUI. Upload, deletion, generation, transcription, narration, and other processing controls remain out of scope.

The read-only comparison and first-release contract are now recorded in `docs/media-contract-review.md`. The first Media page, authenticated preview/download route, search, pagination, navigation, empty/error states, cancellation, representative-library scan/concurrency bounds, deleted-file race behavior, and live two-user isolation are implemented and verified. The Media browser gate is complete. Timeline persistence is parked and Flows is the current slice. Do not use browser automation unless the user reverses the instruction above.

1. Inventoried the legacy Media page, services, metadata expectations, preview behavior, and timeline references from the immutable `legacy/v0.6.36-custom` reference at `7f562ebb5c0893a886adc02521251fce7b725cb2`.
2. Compared them with v0.10.2 Files API listing, pagination, content, download, deletion, processing status, metadata, and access-control behavior.
3. Reviewed the media-related pipes, action, and tools patched at revision `196b1a4` to understand the OWUI files and metadata they produce; invoking them from Studio remains out of scope for the first release.
4. Audited and extended the existing typed, paginated, user-scoped Studio files adapter and the contract in `docs/owui-studio-contract.md`; no second adapter or permission model was created.
5. Confirmed no OWUI bridge endpoint is initially justified and added no direct OWUI database access.
6. Extended adapter fixtures and permission tests for Media-specific listing, search, preview, download, pagination, missing files, and cross-user denial before implementing Media UI.
7. Kept OWUI as file/permission owner. Studio will own timeline projects, tracks, clips, markers, and versions using opaque OWUI file IDs.

## Parked slice: Phase 6 timeline persistence

Parked by user decision on 2026-07-11. When resumed, start with the Studio-owned data and service contract; do not port the legacy timeline UI first.

The immutable behavior reference remains `legacy/v0.6.36-custom` at `7f562ebb5c0893a886adc02521251fce7b725cb2`. The legacy editor provides useful player, scrub, zoom, waveform, thumbnail, marker, and segment interaction references, but its save/export backend was unfinished and no project table was found. Do not treat the legacy README's “production-ready” language as persistence evidence.

Work to retain for when timeline resumes:

1. Reconfirm the legacy timeline types, calculations, routes, save TODOs, upload behavior, and OWUI file assumptions from the pinned commit.
2. Write `docs/timeline-persistence-contract.md` before implementation.
3. Define Studio-owned project, track, clip, marker, and immutable version schemas. Store the current OWUI user ID as owner and OWUI file IDs only as opaque strings, never database foreign keys.
4. Define create/list/read/update/delete and version-history service operations with strict owner scoping, transactional saves, optimistic concurrency, and stable validation/errors.
5. Add numbered SQLite migrations and migration/rollback documentation without changing OWUI storage or schema.
6. Add deterministic tests for two-user separation, save/reload, version creation, stale-write conflict, invalid timeline ranges, missing/deleted OWUI files, and migrations from an empty Studio database.
7. Keep rendering/export, upload, generated-output retention, collaboration, and advanced editing out of the first persistence slice.
8. Port timeline calculations and UI only after the persistence contract and tests pass.

The first deliverable should be the contract document plus executable schema/service tests, not a visually complete editor.

## Current slice: Phase 7 Flows extraction

The legacy and unfinished v0.9.4 Flow implementations have been audited. They share the same fundamental limitation: execution occurs in the browser, the backend execute route is only a placeholder, and the browser submits its own claimed execution history. Do not port that executor architecture or the legacy OWUI Flow tables/routes.

The design contract is `docs/flow-extraction-contract.md`. The first release is intentionally limited to server-executed text DAGs containing Input, Model, Transform, and Output nodes. Conditional, Merge, Loop, Knowledge, web search, files/media, tools/functions, connectors, terminal, and arbitrary HTTP nodes are rejected until separately admitted.

Immediate implementation work:

1. Add numbered Studio SQLite migrations for flows, immutable versions, executions, checkpoints, credential leases, and bounded events.
2. Implement typed `schemaVersion: 1` definition validation with strict node/edge limits and stable field errors.
3. Implement owner-scoped create/list/read/update/delete and immutable version history with optimistic concurrency.
4. Add deterministic two-user, migration, validation, version, conflict, and deletion tests before porting the editor.
5. Add and prove the narrow v0.10.2 non-persisted text-completion adapter fixture before implementing the worker.
6. Implement execution credentials and the durable worker only after the session-store security review required by the contract.

The first implementation deliverable is migrations, validation, immutable version CRUD, and two-user service tests. It contains no legacy editor and performs no model calls.

Studio commit `6b957d0` on published branch `codex/flows-foundation` implements the foundation from Media commit `dc082a9`. Migration `0003_flows.sql` creates the Studio Flow persistence envelope with database-level ownership constraints. Strict definition validation and `FlowStore` implement owner-scoped immutable version CRUD, optimistic concurrency, and guarded deletion. Empty and existing-database migration coverage plus 22 Flow assertions pass within the 48-test server suite; Prettier, ESLint, zero-warning Svelte check, and the production build pass.

Studio commit `259179e` completes the pinned v0.10.2 non-persisted text-completion adapter fixture. It admits current-user base text models only, omits every chat-management field, creates no OWUI chat, dispatches each completion once, and fails closed for denial, malformed response, rate limit, timeout, cancellation, and upstream failure. The full server suite now has 64 passing tests; Svelte check and production build pass. No live model was invoked.

Resume with the execution credential-lease security review and service tests. Do not add routes, the editor, or the durable worker until the lease is execution-bound, encrypted, expiry-bounded, removed on terminal state, and proven unusable across users or executions.
