# Handoff: Flow execution verified, Svelte Flow canvas next

Date: 2026-07-11

## Current outcome

The Open WebUI v0.10.2 rebaseline is running locally with the full native Welcome experience. Welcome remains an optional OWUI UI island because it composes OWUI-owned workspace models, functions/pipes, chat, files, tools, dictation, and voice mode. Studio does not own duplicate agent records.

The first Studio Media browser slice is also complete. It lists, searches, previews, and downloads self-owned OWUI image/video/audio files through the typed server-side adapter. It has no upload, deletion, generation, transcription, narration, or other processing controls. OWUI remains the file, storage, and permission owner.

The user parked timeline persistence after review and selected Phase 7 Flows. Studio has the first constrained Flow workspace and uses the durable server-side execution path in `docs/flow-extraction-contract.md`.

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

Studio commit `259179e` completes the pinned v0.10.2 non-persisted text-completion adapter fixture. It admits current-user base text models only, omits every chat-management field, creates no OWUI chat, dispatches each completion once, and fails closed for denial, malformed response, rate limit, timeout, cancellation, and upstream failure. The full server suite then had 64 passing tests. The adapter tests invoked no live model.

Studio commit `a18151f` completes the credential-lease security gate. Migration `0004_flow_credential_leases.sql` adds execution-owner foreign keys and invalidates pre-contract leases. The service encrypts the OWUI token with owner-and-execution associated data, caps its lifetime at five minutes or the token expiry, hides it from other users, rejects ciphertext copied to another execution, and deletes it on cancellation or terminal state. The full server suite now has 73 passing tests; scoped Prettier, project ESLint, zero-warning Svelte check, and the production build pass.

Resume with the execution lifecycle store and tests: idempotent creation, atomic claims, ordered checkpoints and events, heartbeats, stale-claim recovery, cancellation, and one terminal transition. Add no routes or editor before those invariants pass. Connect the durable worker only after the lifecycle service can prove them without invoking a live model.

Studio commit `f31dfe1` completes that lifecycle gate. Migration `0005_flow_execution_lifecycle.sql` adds hashed expiring claims, deterministic node order, migration fail-closed behavior, and terminal claim cleanup. `FlowExecutionStore` now owns encrypted input/output history, ordered encrypted checkpoints, metadata-only events, immutable-version pinning, owner-scoped idempotency, immediate-lock claims, one active run per owner, global concurrency, heartbeat renewal, cancellation, stale deterministic recovery, and `model_result_unknown` handling. Failure and cancellation settle open nodes, while terminal rows retain their last heartbeat and no claim capability. The full server suite now has 85 passing tests; scoped Prettier, project ESLint, zero-warning Svelte check, and the production build pass. The tests invoked no live model.

Resume with the durable worker core. Inject the OWUI client and clock, acquire the execution credential lease, evaluate Input, Transform, and Output nodes in stored order, dispatch Model once through the proven adapter, refresh heartbeats, enforce deadlines, and abort on cancellation. Prove the worker with stubs before adding Flow routes or the editor.

Studio commit `53fe122` completes the worker-core gate. `FlowWorker` recovers stale claims, evaluates supported nodes in stored order, resumes completed checkpoints, and commits terminal output. It acquires an execution credential before each Model dispatch, calls the proven adapter once, refreshes heartbeats during the request, enforces run and node deadlines, and aborts after owner cancellation. An abandoned in-flight Model node fails `model_result_unknown` and no worker dispatches it again. The worker also maps OWUI errors to stable Flow codes and keeps input, output, credentials, prompts, and upstream bodies out of events. Graph validation now rejects transform and output fan-in without merge semantics, and expired claims reject late heartbeats.

All 100 Studio server tests pass; scoped Prettier, project ESLint, zero-warning Svelte check, and the production build pass. Tests use the real adapter stub and make no live model call.

The worker is not running as a background process yet. Studio still has no Flow API routes, event stream, or UI. Resume with a queue service that creates the execution and credential lease in one transaction, add the background runner, then expose owner-scoped Flow and execution routes for the first small UI.

Studio commit `69029f9` completes that server-facing slice. `FlowQueueService` creates the execution and credential lease in one transaction and caps the lease at the OWUI token, absolute session, and idle session expiries. The in-process runner polls without overlap, accepts queue wakeups, contains failures, and records its configured identity on each claim. Environment settings control enablement, polling, claim/heartbeat timing, deadlines, and concurrency.

Seven authenticated handlers now cover Flow CRUD, immutable versions, execution queue/list/read, cancellation, and owner-scoped SSE. Routes derive identity and credentials from `locals.session`, require `Idempotency-Key` for execution creation, reject unknown fields and cross-origin mutations, hide cross-user records as `not_found`, and keep retained user data out of events. The route fixture covers version conflict, active-delete guard, two-user hiding, cancellation, transaction rollback, and terminal stream redaction.

All 111 Studio server tests pass; scoped Prettier, project ESLint, zero-warning Svelte check, and the production build pass. This slice made no live model call and did not rebuild a deployed Studio container.

Studio commit `e9accc5` completes the first UI slice in the local worktree. `/studio/flows` provides owner-scoped list/create/update/delete, a constrained Input, Model, optional Transform, Output editor, execution history, live SSE node progress, cancellation, and output display. Definitions with settings the first editor cannot represent remain read-only so a save cannot discard them. Welcome, Agents, and Media link to Flows.

The first live run exposed two adapter gaps. Commit `eac13a2` normalises OWUI token expiry from Unix seconds to JavaScript milliseconds and repairs old sessions at read time. Commit `18efba0` changes direct Model calls from non-streaming JSON to bounded SSE, matching the path that works inside OWUI. The streaming adapter requires `[DONE]`, caps bytes and output, supports split transport chunks, preserves cancellation and deadlines, dispatches once, and omits OWUI chat-management fields. The user confirmed the rebuilt Flow completes against the configured `chatgpt/*` model.

All 117 Studio server tests pass. Scoped Prettier, ESLint, zero-warning Svelte check, the production build, and the signed-out headless route test pass. Docker image `open-webui-studio:flows-ui-local` runs in `owui-studio-media-test` at `http://localhost:5173/studio/`; the container reports healthy. The prior Studio containers remain stopped as rollback points.

## Completed slices: locked and editable Svelte Flow canvas

The legacy `src/lib/components/flows/FlowEditor.svelte` at commit `7f562ebb5c0893a886adc02521251fce7b725cb2` used `@xyflow/svelte` `0.1.19` for draggable nodes, handles, edges, controls, a minimap, fixed panels, and responsive graph layout. Use Svelte Flow `1.6.2`, reviewed on 2026-07-11, with Studio's Svelte 5 stack. See the [Svelte Flow quick start](https://svelteflow.dev/learn).

The local Studio worktree now implements the locked-topology Input, Model, optional Transform, and Output canvas:

1. `@xyflow/svelte` `1.6.2` and its required stylesheet are installed for the Svelte 5 application.
2. Typed adapters map shared `FlowDefinitionV1` nodes and edges to Svelte Flow view types and write only positions back.
3. Linear drafts preserve saved positions; adding or removing the optional Transform does not overwrite the other nodes' positions.
4. Custom node cards, selected-node configuration, Controls, Background, MiniMap, fit view, and draggable saved positions are present while arbitrary add/delete/connect remains disabled.
5. Existing execution records and SSE events populate a separate node-ID execution map. Runtime state is not written into definitions.

All 122 server tests pass, including focused adapter, execution-map, position, and component coverage. Svelte check reports zero errors and warnings, full ESLint passes, changed files pass Prettier, and the production build succeeds. The Node 22.17.0 Docker image builds and the rebuilt `owui-studio-media-test` container is healthy at `http://localhost:5173/studio/`, still using `owui-studio-media-test-data`. The prior container is preserved as `owui-studio-media-test-pre-svelte-flow`; older rollback containers are unchanged. Health and signed-out Flows HTTP checks return `200`, and container logs are clean.

The user accepted the locked canvas and requested the legacy-style editing interaction. Studio commit `70462a8` makes the canvas the main editor surface and unlocks add, delete, and connect for Input, Model, Transform, and Output only. A typed local graph editor provides deterministic placement, duplicate/cycle/direction checks, incident-edge cleanup, and incomplete-topology feedback. The server validator remains authoritative on save.

Node selection opens an in-canvas settings drawer. It covers Input keys/defaults, Model selection/prompt/temperature/max tokens, all admitted Transform operations and their fields, and Output format. Connections are created by dragging between typed ports and explicitly deleted when selected. The runner renders the saved version's Input keys, so unsaved graph edits cannot change the execution request before a successful save. Deferred node types remain rejected.

All 126 server tests pass, including focused graph-editing and component coverage. Svelte check reports zero errors and warnings, full ESLint passes, changed files pass Prettier, and both local and Node 22.17.0 Docker production builds succeed. The rebuilt `owui-studio-media-test` container is healthy on the preserved `owui-studio-media-test-data` volume. Its predecessor is retained as `owui-studio-media-test-pre-editable-flow`, and `owui-studio-media-test-pre-svelte-flow` plus older rollbacks remain unchanged. Health and signed-out Flows HTTP checks return `200`; logs are clean.

The remaining UI gate is a user-led authenticated check of adding and deleting each admitted node, connecting and deleting edges, editing and saving settings, position reload, structural feedback, run inputs, live progress, cancellation, output, and history.

The user explicitly asked to retry the in-app browser and signed in. The authenticated check confirmed the existing saved flow, adding a Transform node, incomplete-topology feedback, and changing the Transform setting from trim to uppercase. The browser controller stalled at the native delete confirmation, so no save or server mutation was made. Deletion, edge editing, save/reload position persistence, and a fresh run/cancel/history pass remain useful manual confidence checks.

## Completed slice: Flow audit and automated Phase 7 lifecycle gate

Studio commit `bf7dd04` adds migration `0007_flow_audit.sql` and transactional metadata-only audit records for flow creation/update/deletion and execution queue/start/requeue/cancel/success/failure transitions. The table has fixed columns for owner, action, Flow/version IDs, execution ID/state, stable error code, and timestamp. It has no flexible JSON or fields for names, descriptions, definitions, model IDs, prompts, inputs, outputs, request IDs, idempotency keys, tokens, or connector secrets. Audit rows intentionally survive terminal Flow deletion.

Focused tests prove transaction rollback, one audit event for idempotent queueing, owner-scoped audit reads, the exact fixed schema, and absence of sensitive markers. A representative two-user lifecycle fixture creates both flows from empty Studio storage, queues user A against version 1, saves version 2, proves the worker still executes version 1, hides flow/execution/event/audit data from user B, cancels user B's queued run, deletes user A's terminal Flow, and retains only metadata audit history.

All 130 Studio server tests pass. Svelte check reports zero errors and warnings, full ESLint passes, changed TypeScript files pass Prettier, `git diff --check` is clean, and the production build succeeds. The repository-wide Prettier check still reports the same 34 baseline files outside this slice.

Image `open-webui-studio:flows-ui-local` was rebuilt from the validated worktree. Only `owui-studio-media-test` was rotated; it is healthy, runs as `studio`, uses the preserved `owui-studio-media-test-data` volume, and reports migration `0007_flow_audit.sql` and `studio_flow_audit` present. The previous container remains stopped as `owui-studio-media-test-pre-flow-audit`; all older rollback containers remain unchanged. `/studio/health` returns `200`, startup logs are clean, and anonymous Flow/API requests retain hidden `404` behavior.

Do not copy the legacy global stores, browser executor, broad `any` types, window event listener, forced `flowKey` remount, random node placement, weak graph validation, discarded handle IDs, or automatic breakpoint layout that overwrites user positions. Keep the server validator authoritative. Unlock add, delete, and connect for the four admitted node types after the locked canvas passes. Deferred node types retain the admission gates in `docs/flow-extraction-contract.md`.

Do not use in-app browser automation again unless the user explicitly asks. The user reversed the earlier prohibition for one authenticated check, but the controller stalled at a native confirmation. Prefer automated tests, HTTP checks, container logs, and user-led UI verification.

The Studio branch contains six unpushed commits: `e9accc5`, `eac13a2`, `18efba0`, locked-canvas commit `cd30583`, editable-canvas commit `70462a8`, and audit/lifecycle commit `bf7dd04`. This planning repository also has local commits and documentation changes awaiting publication. Push each repository only after the user gives fresh approval for its private remote.
