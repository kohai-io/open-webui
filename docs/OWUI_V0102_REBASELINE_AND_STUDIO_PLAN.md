# Open WebUI v0.10.2 rebaseline and Studio extraction plan

## Goal

Move the deployment from the legacy v0.6.36-based fork to a clean v0.10.2-based Open WebUI release, while moving substantial custom products such as Flows and the video timeline into a separately deployed Studio application.

The target state is:

- Open WebUI remains close to upstream and owns users, authentication, models, agents, chats, files, knowledge, and standard upstream features.
- Studio owns custom experiences, domain data, background work, and experimental interfaces.
- The integration between them is narrow, authenticated, documented, and tested.
- Open WebUI and Studio can be upgraded and rolled back independently.

## How to use this plan

- Check an item only when its evidence has been recorded.
- Do not pass an exit gate with unresolved issues that block its dependent work.
- Phases may overlap when their boundaries are already decided. Deployment-host capture in Phase 0 blocks staging and cutover, not the Phase 3 contract.
- Add links to commits, test output, deployment notes, or decision records beside completed items.
- Treat the rebaseline as a fresh deployment with empty OWUI and Studio databases.
- Do not migrate or import users, chats, files, knowledge, flows, schedules, preferences, OAuth state, or other data from the legacy fork.
- Preserve the legacy source reference and deployment record for archaeology; legacy data backup and recovery are outside this plan.
- Defer live deployment-host capture, reverse-proxy configuration, image publication, and cutover rehearsal until a homelab Proxmox staging target is selected. These items do not block Studio product extraction or source-maintenance work.

## Target architecture

```text
Browser
  |-- / and /api/* --------> Open WebUI v0.10.2+
  |                            users, models, chats, files, knowledge
  |
  +-- /studio/* ------------> Studio (SvelteKit)
                               Studio session and API adapter
                               Studio database
                               Flow worker
                               Media/timeline services
```

Studio must not read or write Open WebUI's database directly. Open WebUI object IDs are opaque external references in Studio, not database foreign keys.

## Proposed repositories and branches

### Repositories

- `open-webui`: upstream-derived fork with a minimal integration patch set.
- `open-webui-studio`: custom UI, persistence, workers, and tests.
- Deployment configuration can remain with the existing deployment initially and move to a third repository later if that becomes useful.

### Open WebUI references

- `legacy/v0.6.36-custom`: immutable reference to the current customised application.
- `archive/rebaseline-v0.9.4`: immutable reference to the unfinished earlier rebaseline.
- `rebaseline/upstream-v0.10.2`: clean v0.10.2 baseline and compatibility testing.
- `robert/stable`: deployed Open WebUI plus the minimal retained integration patches.

Do not rewrite the legacy or archived rebaseline histories.

---

## Phase 0: Preserve the current system

### Source and deployment record

- [ ] Record the currently deployed commit SHA.
- [x] Create and push an immutable `legacy/v0.6.36-custom` tag or branch. Published at captured pre-plan source commit `7f562ebb5c0893a886adc02521251fce7b725cb2`; this does not claim it is the live deployed SHA. See `docs/rebaseline-phase-0-source-record.md`.
- [x] Preserve the unfinished v0.9.4 rebaseline as `archive/rebaseline-v0.9.4`. Published at `d62f9dc9250be3699d27941f608712d46f4c3f38`. See `docs/rebaseline-phase-0-source-record.md`.
- [ ] Record the deployed container image and digest.
- [ ] Record Compose files, reverse-proxy routes, volumes, environment variable names, and external dependencies.
- [ ] Record the `functions_tools` submodule revision and how it is deployed. Compatibility revision `196b1a4` is published on `codex/v0102-file-api-compat` at `git.theoldschool.house/robert/open-webui-functions-tools`, and a fresh recursive clone resolves it correctly; live deployment use remains unverified. See `docs/rebaseline-phase-0-source-record.md` and `docs/functions-tools-v0.10.2-file-api-compatibility.md`.
- [ ] Store secrets only in the existing secret-management location; do not copy secret values into this plan.

### Fresh-start boundary

- [x] Confirm that the v0.10.2 deployment starts with empty application databases and storage.
- [x] Exclude legacy users, chats, files, knowledge, flows, schedules, preferences, OAuth sessions, and custom database rows from migration scope.
- [ ] Record the minimal bootstrap configuration and initial administrator creation procedure without secret values.
- [ ] Define rollback as switching back to the untouched legacy deployment, not downgrading or converting the new databases.

### Exit gate 0: preservation and cutover prerequisites

- [ ] The legacy source and deployment are reproducible.
- [x] The new deployment bootstrap is reproducible from empty storage. Two independent local rehearsals passed after explicit `DATA_DIR` provisioning.
- [ ] The legacy and new deployments have independent storage and can be selected without database conversion.

The immutable legacy source references exist. Live deployment, routing, image, and rollback evidence is intentionally deferred until homelab staging, but all three gate items must pass before Phase 9 cutover.

---

## Phase 1: Build the feature and data ledger

Create `docs/feature-ledger.md`. Give every custom feature one explicit decision: `drop`, `use upstream`, `contribute upstream`, `extract to Studio`, or `retain as a small OWUI patch`.

### Inventory each feature

- [x] Custom Welcome experience. See `docs/feature-ledger.md`.
- [x] Agents catalogue, ordering, and launch experience. See `docs/feature-ledger.md`.
- [x] Flows editor, nodes, execution, and history. See `docs/feature-ledger.md`.
- [x] Media browser and previews. See `docs/feature-ledger.md`.
- [x] Video timeline/editor and project persistence. See `docs/feature-ledger.md`.
- [x] Scheduled prompts and notifications. See `docs/feature-ledger.md`.
- [x] Admin analytics and LiteLLM spend reporting. See `docs/feature-ledger.md`.
- [x] Google Drive OAuth, picker, and sync changes. Use upstream selected-file import; drop fork server OAuth/sync; contribute multi-file handling only if required. See `docs/mcp-oauth-google-drive-comparison.md`.
- [x] Agent Skills integration. See `docs/feature-ledger.md`.
- [x] MCP and OAuth fixes. Upstream covers token-auth passthrough, duplicate callback credentials, and cleanup; contribute the remaining unprefixed tool-name resolver. See `docs/mcp-oauth-google-drive-comparison.md`.
- [x] Model selector and chat rendering changes. See `docs/feature-ledger.md`.
- [x] Knowledge-management changes. See `docs/feature-ledger.md`.
- [x] Branding, navigation, and static assets. See `docs/feature-ledger.md`.
- [x] Pi Gateway and other experimental interfaces. See `docs/feature-ledger.md`.
- [x] `functions_tools` submodule features. See `docs/feature-ledger.md`; the 19 pipe functions plus one action and six tools that call the Files API were patched for v0.10.2, and the legacy prompt scheduler was removed. Per-artifact product disposition and runtime contract tests remain open. See `docs/functions-tools-v0.10.2-file-api-compatibility.md`.

### Remaining deployment evidence across features

The source-level routes, ownership, disposition, fresh-start acceptance, and rollback decisions needed for Exit Gate 1 are recorded in `docs/feature-ledger.md`. The following live deployment reconciliation remains open and does not block contract or foundation work:

- [ ] Current routes and source paths.
- [ ] Backend endpoints, database tables, migrations, jobs, and external dependencies.
- [ ] Whether it is used in the current deployment.
- [ ] The equivalent or overlapping functionality in v0.10.2.
- [ ] Target owner: upstream OWUI, minimal fork patch, Studio, another service, or archive.
- [ ] Required fresh-start configuration, bootstrap, or seed data.
- [ ] Acceptance test and rollback route.

### Initial assumptions to validate

- [x] Flows will be extracted to Studio. See `docs/feature-ledger.md`.
- [x] Media and the video timeline will be extracted to Studio. See `docs/feature-ledger.md`.
- [x] Welcome and Agents are candidates for the first Studio vertical slice. See `docs/feature-ledger.md`.
- [x] Scheduled prompts are replaced by upstream Automations/Calendar and `create_automation`. The fork implementation and its data are not ported or imported, and the legacy `functions_tools` prompt-scheduler tool has been deleted. See `docs/feature-ledger.md`.
- [x] Pi Gateway and experiments will not be added to the maintained OWUI fork. See `docs/feature-ledger.md`.
- [x] Fork fixes already present upstream will be dropped. See `docs/mcp-oauth-google-drive-comparison.md`; remaining feature areas still require their own upstream comparison.

### Exit gate 1

- [x] Every custom feature has one owner and one disposition. Initial decisions are in `docs/feature-ledger.md`; v0.10.2 comparison can refine them explicitly.
- [x] Every retained feature has an acceptance test. Acceptance summaries are in `docs/feature-ledger.md`; executable cases remain phase work.
- [x] Custom database objects and their target destinations are known. Legacy Flow, execution, scheduled-prompt, and OAuth-session objects are not imported; new Studio schemas start empty. See `docs/feature-ledger.md`.
- [x] Nothing is scheduled for porting merely because it exists in the legacy fork. Every inventoried feature has an explicit disposition.

---

## Phase 2: Establish a clean v0.10.2 baseline

### Upstream setup

- [x] Add the official Open WebUI repository as the `upstream` remote. See `docs/v0.10.2-baseline-comparison.md`.
- [x] Fetch the v0.10.2 tag and record its commit SHA. The ref came from the official remote; independent GPG trust verification remains open because the signing public key is unavailable locally. See `docs/v0.10.2-baseline-comparison.md`.
- [x] Create `rebaseline/upstream-v0.10.2` from the exact upstream tag. Created without switching the legacy working tree and published to the canonical Gitea origin.
- [x] Confirm there are no custom source changes on the initial baseline commit. The branch and release ref both resolve to `ecd48e2f718220a6400ecf49eafd4867a38feb10`.
- [x] Build and start unmodified v0.10.2 with empty disposable data. Frontend production build and initial backend health/bootstrap smoke checks passed. See `docs/v0.10.2-baseline-comparison.md`.
- [x] Define separate local runtimes: Node.js 22 for the frontend and a Conda Python 3.11 environment for the backend. See `docs/LOCAL_DEVELOPMENT.md`.

### Configuration compatibility

- [ ] Compare legacy environment variables with v0.10.2 configuration. Source/default and Compose-name comparison is complete; live deployment-host names remain. See `docs/v0.10.2-configuration-matrix.md`.
- [x] Classify source-level variables as unchanged, renamed, removed, replaced, or custom. All 534 directly read legacy backend names are accounted for; live deployment reconciliation remains separate.
- [ ] Create a staging configuration without production secrets.
- [ ] Verify reverse-proxy headers, WebSockets, streaming, upload limits, and callback URLs.
- [ ] Verify required model providers, Ollama/OpenAI-compatible endpoints, MCP servers, and OAuth providers.
  - Local OpenAI-compatible model discovery, explicit per-user model grants, denial, and SSE streaming pass with a disposable stub; intended real providers, MCP, and OAuth remain.

### Fresh data rehearsal

- [x] Start v0.10.2 against a new empty database and empty file/vector storage. Disposable rehearsal reached Alembic head `42e2978c7933`.
- [x] Create bootstrap administrators and representative test users through supported interfaces. First-admin signup and administrator-created ordinary user both passed.
- [ ] Configure representative groups, models, agents, files, knowledge, OAuth, MCP, and tools from scratch.
- [ ] Verify login, permissions, chats, uploads, knowledge, OAuth, MCP, tools, and API access.
- [x] Destroy and repeat the bootstrap from empty storage to prove reproducibility. Two independent fresh-data rehearsals initialised successfully after explicitly provisioning `DATA_DIR`.

### Exit gate 2

- [ ] Unmodified v0.10.2 passes its clean build and smoke tests.
- [x] A fresh empty database and storage set can be initialised reproducibly. See `docs/v0.10.2-baseline-comparison.md`.
- [ ] Core OWUI data and workflows work without Studio.
- [ ] The fresh deployment and legacy deployment have independent rollback boundaries.

The production frontend build and recorded backend/API smoke tests pass. `npm run check` still fails on existing upstream diagnostics, and the dependency audit reports unresolved advisories. Decide and record whether these block deployment before marking the first gate item complete.

---

## Phase 3: Define the Open WebUI–Studio contract

Create a short contract document before implementing the integration.

### Ownership contract

- [x] OWUI owns users, groups, roles, models, agents, chats, messages, files, and knowledge. See `docs/owui-studio-contract.md`.
- [x] Studio owns preferences specific to Studio, timeline projects, flow definitions, flow versions, execution state, and execution history. See `docs/owui-studio-contract.md`.
- [x] Studio does not access `webui.db` or other OWUI storage directly. See `docs/owui-studio-contract.md`.
- [x] Studio stores OWUI IDs as opaque references and revalidates access through authenticated APIs. See `docs/owui-studio-contract.md`.

### Authentication decision

- [x] Evaluate shared OIDC for both services as the preferred solution. Use the upstream v0.10.2 OAuth token-exchange endpoint server-side. See `docs/owui-studio-contract.md`.
- [x] If shared OIDC is unavailable, specify a short-lived, single-use OWUI-to-Studio launch-token exchange. The fallback is specified but must not be implemented while upstream exchange works. See `docs/owui-studio-contract.md`.
- [x] Derive identity server-side; never trust a browser-supplied OWUI user ID. See `docs/owui-studio-contract.md`.
- [x] Keep administrator credentials out of browser code and logs. The contract requires no administrator credential. See `docs/owui-studio-contract.md`.
- [x] Define logout, expiry, account disablement, and group/role refresh behaviour. See `docs/owui-studio-contract.md`.
- [x] Add negative tests for token replay, wrong issuer/audience, open redirects, and cross-user access. See `docs/owui-studio-contract.md`.

### API contract

- [x] List the minimum user-scoped OWUI operations Studio requires. See `docs/owui-studio-contract.md`.
- [x] Prefer documented OWUI APIs. See `docs/owui-studio-contract.md`.
- [x] Put OWUI response normalisation behind a typed server-side adapter. See `docs/owui-studio-contract.md`.
- [x] Add a narrow OWUI bridge endpoint only when no safe supported API exists. No bridge is currently justified; the admission rule is documented.
- [x] Define API compatibility fixtures for the supported OWUI version. See `docs/owui-studio-contract.md`.
- [x] Define timeouts, retries, error mapping, and request correlation IDs. See `docs/owui-studio-contract.md`.

### Provisional OWUI patch set

- [x] Studio navigation/launch seam: start with the reverse-proxied direct URL; add only a configuration-driven removable link if required. See `docs/owui-studio-contract.md`.
- [x] MCP unique-suffix tool-name resolver only if intended staging models reproduce the blocker; otherwise upstream contribution only. See `docs/owui-studio-contract.md`.
- [x] Google Drive multi-file handling as an upstream contribution only if retained as a requirement. See `docs/owui-studio-contract.md`.
- [x] No other OWUI patch is currently justified by the completed comparisons.

### Exit gate 3

- [x] Identity and data ownership boundaries are documented. See `docs/owui-studio-contract.md`.
- [x] Cross-user denial tests are specified. See `docs/owui-studio-contract.md`.
- [x] The planned OWUI patch set is narrow and enumerated. No patch is required for the first identity/API slice.
- [x] No Studio feature requires direct OWUI database access or a browser-visible administrator key. See `docs/owui-studio-contract.md`.

---

## Phase 4: Create the Studio foundation

### Repository and application

- [x] Create the private `open-webui-studio` repository. Canonical origin is `https://git.theoldschool.house/robert/open-webui-studio.git`; validated foundation through commit `6df9f08`. The former GitHub location is retained only as a secondary remote unless explicitly retired.
- [x] Scaffold a SvelteKit TypeScript application using `adapter-node`. The repository pins Node.js `22.17.0` for development and containers.
- [ ] Configure deployment under `/studio`. The application base path and browser tests use `/studio`; reverse-proxy deployment remains.
- [x] Add formatting, linting, type checking, unit tests, integration tests, and Playwright tests. Formatting, lint, zero-diagnostic Svelte check, eight Vitest assertions, production build, and the `/studio` shell/health browser test pass.
- [x] Add a production Dockerfile running as a non-root user. Image `open-webui-studio:phase4` builds successfully, runs as `studio`, starts on port 3000, and passes a disposable `/studio/health` container smoke test.
- [x] Add a health endpoint that exposes no secrets. `GET /studio/health` returns only status, service, and application version.
- [x] Add structured logs and request correlation. Server requests emit bounded JSON metadata and an allowlisted/generated `X-Request-ID` without query strings or bodies.

### Core services

- [x] Implement Studio sessions and authentication. Studio commits `bccf2ef` and `2f0bd9b` provide migration-backed opaque handles, AES-256-GCM storage, expiry/rotation/revocation, subject binding, discovery, Authorization Code + PKCE, state/nonce, single-use transactions, secure cookie integration, provider-token exchange, login/callback/logout routes, and a fake-provider suite. Live Okta conformance remains a Phase 2/staging check.
- [x] Implement the typed server-side OWUI adapter. Studio commit `6df9f08` covers upstream OAuth token exchange, current identity, filtered models/agents, paginated files, paginated Knowledge, and chat creation with normalized response types and stable error mapping.
- [x] Add a Studio-owned database and migrations. Studio commit `bccf2ef` adds an independent SQLite database, transactional numbered migrations, identity bindings, encrypted session rows, ignored local data files, and container migration assets.
- [x] Add fixtures or a stub service for OWUI contract tests. Studio commit `6df9f08` adds a deterministic injected-fetch stub covering success, two-user separation, hidden-resource denial, malformed responses, transient read retry, and mutation non-retry.
- [ ] Add a test user matrix covering ordinary users, administrators, groups, and denied resources.

### Deployment seam

- [ ] Route `/studio/*` to Studio through the existing reverse proxy.
- [ ] Verify direct page loads and asset paths under `/studio`.
- [ ] Add the smallest possible OWUI navigation integration.
- [ ] Verify independent deployment and rollback of the empty Studio shell.

### Exit gate 4

- [ ] An authenticated user can open the empty Studio shell.
- [ ] Unauthenticated and cross-user access fails closed.
- [ ] OWUI continues to work when Studio is stopped.
- [ ] Studio can be rolled back without rolling back OWUI.

---

## Phase 5: First vertical slice — Welcome and Agents

- [x] Define executable-model, accessible workspace-model/function, and native OWUI launch contracts.
- [x] Retain Welcome as a feature-flagged native OWUI UI island because it composes OWUI-owned chat, files, tools, dictation, voice, and workspace-model behavior.
- [x] List only models and agents available to the current user.
- [x] Preserve user-arranged agent order as a browser-local presentation preference; do not create a second agent record or permission model.
- [x] Hand an authorised model or agent to OWUI's native new-chat route, with server-side availability revalidation.
- [x] Verify launch redirects to `/?models=<id>` so OWUI applies the workspace model's prompt, knowledge, skills, and tools.
- [ ] Add loading, empty, permission-denied, and upstream-unavailable states.
- [ ] Add end-to-end tests for two users with different access.
- [x] Manually verify live Welcome interactions in Chrome at normal and responsive/narrow widths.
- [ ] Verify Welcome on a physical mobile device.
- [x] Deploy behind `ENABLE_WELCOME_PAGE`, disabled by default.

### Exit gate 5

- [x] Native Welcome and Agents work without adding backend domain tables or duplicating OWUI authorization.
- [x] A user cannot discover or launch inaccessible models or agents; the two-user end-to-end proof remains open above.
- [x] Rollback requires only disabling `ENABLE_WELCOME_PAGE` or restoring an upstream/previous OWUI image; no data conversion is required.

---

## Phase 6: Media browser and video timeline

Current point (2026-07-11): Studio includes native Welcome, the first read-only Media browser, and the constrained Flow workspace. The user confirmed authenticated Flow execution through the streaming OWUI completion path. The next UI slice adds a locked-topology Svelte Flow canvas. The user parked timeline persistence. See `docs/HANDOFF_2026-07-11_WELCOME_TO_MEDIA.md` and `docs/flow-extraction-contract.md`.

### Media access

- [x] Audit the existing typed, paginated, user-scoped files adapter and define its Media extension; do not create a second adapter. See `docs/media-contract-review.md`.
- [x] Determine which file metadata, search, preview, download, pagination, and access-control operations existing OWUI APIs support. See `docs/media-contract-review.md`.
- [x] Add no OWUI bridge endpoint initially. Revisit only an upstreamable `owned_only=true` list/search option if representative administrator tests prove Studio-side self-filtering too costly.
- [x] Extend the Studio adapter with bounded listing/search, strict self-ownership checks, and hardened preview/download streaming. Studio commits `5b5bb4e` and `08a332f`; 11 focused tests, all 21 server tests, Svelte check, image build, and non-root container smoke checks pass.
- [x] Implement first-release listing, search, lazy preview, download, and pagination for existing OWUI media; exclude upload, deletion, generation, and processing controls. Studio commit `278be05`.
- [x] Manually verify the authenticated Media page, previews, and downloads.
- [x] Verify cancellation and bounded preview concurrency with a representative 1,250-record mixed library. Studio commit `57f7673` proves 500-record scan bounds, opaque continuation, sequential upstream concurrency of one, cancellation without retry, and zero full-media grid preloads.
- [x] Test representative large libraries, inaccessible cross-user references, and files deleted between metadata validation and content streaming. Studio commits `57f7673` and `dc082a9`.
- [x] Manually verify two users see only their own media and a direct cross-user content URL returns hidden `404`.

### Timeline ownership

Parked by user decision on 2026-07-11. These items remain valid but do not block Phase 7 Flows work.

- [ ] Define Studio-owned project, track, clip, marker, and version schemas.
- [ ] Store OWUI file IDs as opaque external references.
- [ ] Add project migrations, autosave, optimistic concurrency, and recovery behaviour.
- [ ] Port timeline calculations and UI independently of OWUI stores and routes.
- [ ] Decide whether rendering/export belongs in the web process or a separate worker.
- [ ] Define upload, generated-output, retention, and cleanup policies.
- [ ] Add unit tests for timeline calculations and end-to-end save/reload tests.

### Exit gate 6

- [x] Media access is user-scoped and performs acceptably on representative data.
- [ ] Timeline projects persist entirely outside OWUI's schema.
- [x] Missing or inaccessible OWUI files fail safely without exposing metadata.
- [ ] OWUI can upgrade without migrating Studio timeline tables.

---

## Phase 7: Flows extraction

### Design before porting

- [x] Review the legacy Flows implementation and the unfinished v0.9.4 port as reference material. See `docs/flow-extraction-contract.md`.
- [x] Compare every node type and integration with v0.10.2 APIs. The legacy nine-node inventory and admission decisions are recorded in `docs/flow-extraction-contract.md`.
- [x] Define the supported first-release node set; reject deferred nodes rather than preserving or skipping them. First release: text Input, Model, Transform, and Output.
- [x] Specify immutable flow definition versioning, optimistic concurrency, graph validation, and stable errors. See `docs/flow-extraction-contract.md`.
- [x] Specify user-scoped access to models, files, Knowledge, and tools. The first release admits accessible base text models only; files, Knowledge, tools/functions, and media are deferred.
- [x] Define connector-secret storage and redaction. The first release accepts no connector secrets; future connectors require separate encrypted credential references and admission tests.

### Studio implementation

- [x] Move flow definitions and immutable versions into the Studio database. Studio commit `6b957d0` on published branch `codex/flows-foundation` adds migration `0003_flows.sql`, strict definition validation, owner-scoped CRUD, optimistic concurrency, and version history.
- [x] Move execution history and checkpoints into the Studio database. Studio commit `f31dfe1` adds encrypted execution payloads, ordered node checkpoints, bounded metadata-only events, owner-scoped history, and migration coverage.
- [x] Port the first constrained editor without OWUI internal stores or routes. Local Studio commit `e9accc5` adds list/create/update/delete, linear Input/Model/optional Transform/Output editing, run history, SSE progress, cancellation, and output display. Remote publication awaits approval.
- [x] Review the legacy Svelte Flow editor and the current library API. The legacy component used `@xyflow/svelte` `0.1.19`; version `1.6.2`, reviewed on 2026-07-11, supports Svelte 5 and recommends `$state.raw` for nodes and edges. Reuse the canvas interaction model, not the legacy global stores, browser execution, runtime data inside definitions, forced remounts, random placement, or breakpoint-driven position rewrites.
- [x] Add a locked-topology Svelte Flow canvas for the admitted Input, Model, optional Transform, Output shape. Studio commit `cd30583` on `codex/flows-foundation` uses `@xyflow/svelte` `1.6.2`, typed definition/view adapters, saved positions, custom node cards, selected-node configuration, Controls, Background, MiniMap, and fit view. Arbitrary add/delete/connect remains disabled.
- [x] Overlay SSE node progress and terminal state on the canvas without writing runtime state into saved definitions. The existing execution/node records and SSE events populate a separate node-ID map; focused adapter, execution-map, position, and component tests pass.
- [x] After the locked canvas passes tests, permit add, delete, and connect for Input, Model, Transform, and Output nodes. Studio commit `70462a8` makes the canvas the primary editor, adds deterministic admitted-node creation, port-to-port connections, explicit node/edge deletion, in-canvas settings for every admitted configuration, and structural client feedback while retaining server validation as the authority.
- [ ] Admit Conditional, Merge, Loop, Knowledge, web search, files, tools, and other nodes after their server schemas, permission boundaries, limits, checkpoint rules, and redaction tests pass.
- [x] Prove the narrow v0.10.2 text-completion adapter contract without creating OWUI chats. Studio commit `259179e` revalidates base-model access, omits chat-management fields, dispatches once, and covers denial, malformed response, rate limit, timeout, cancellation, and failure fixtures.
- [x] Implement execution-bound credential leases. Studio commit `a18151f` adds owner-bound authenticated encryption, bounded expiry, database-enforced cancellation and terminal cleanup, and cross-user/cross-execution tests.
- [x] Implement the execution lifecycle state machine. Studio commit `f31dfe1` adds idempotent creation, atomic claims, per-owner/global concurrency, heartbeats, cancellation, deterministic recovery, uncertain-model failure, and sealed terminal states.
- [x] Implement the dependency-injected durable worker core. Studio commit `53fe122` evaluates supported nodes, resumes checkpoints, acquires Model credentials, dispatches once through the adapter, refreshes heartbeats, and seals results.
- [x] Add cancellation, timeout, idempotency, and concurrency controls. Commits `f31dfe1` and `53fe122` cover owner cancellation, abort signals, run/node deadlines, owner-scoped idempotency, global/per-owner claims, and no Model retry after dispatch.
- [x] Add the background worker runner and deployment lifecycle. Studio commit `69029f9` wires a non-overlapping in-process poller with queue wakeups, stable error containment, environment controls, and recorded worker identity.
- [x] Stream execution events to authorised users. Studio commit `69029f9` adds owner-scoped SSE with reconnect cursors and metadata-only payloads.
- [x] Prevent client-supplied ownership or user identity. All Flow routes derive the owner and OWUI credential from the authenticated Studio session and reject unknown request fields.
- [ ] Add audit records without prompt, token, or secret leakage.

### Fresh-start validation

- [ ] Do not add a legacy Flow export or import path.
- [ ] Create representative supported flows from scratch in Studio fixtures and end-to-end tests.
- [x] Confirm Studio creates no legacy Flow tables in OWUI storage. Empty and existing-foundation migration tests create only `studio_flow*` tables in the independent Studio database.

### Exit gate 7

- [ ] Representative new flows can be created, versioned, executed, and deleted in Studio.
- [ ] Flow execution is user-scoped, observable, cancellable, and resumable as designed.
- [ ] OWUI contains no Flow domain tables, editor implementation, or execution engine.
- [ ] Studio and its worker can be upgraded or rolled back independently of OWUI.

---

## Phase 8: Remaining customisations and minimal OWUI patch set

- [x] Decide the scheduled-prompt destination: use upstream Automations/Calendar exclusively; remove the fork implementation and do not import its records.
- [x] Use upstream v0.10.2 admin analytics rather than porting the fork dashboard.
- [x] Decide the optional LiteLLM spend-reporting destination: Studio server-side admin reporting, with credentials kept out of browser code and OWUI. Implementation remains future Studio work if the report is retained. See `docs/feature-ledger.md`.
- [x] Decide the destination of Google Drive customisations after comparing v0.10.2: use upstream picker/chat import, drop fork server OAuth/sync, and contribute multi-file handling only if required.
- [x] Use upstream v0.10.2 Agent Skills; do not port the fork implementation.
- [x] Drop MCP/OAuth fixes already present upstream. Token-auth passthrough, duplicate callback credentials, and safe cleanup are upstream; unprefixed tool-name resolution remains an upstream contribution candidate.
- [ ] Submit generally useful remaining fixes upstream where practical.
- [ ] Move experiments such as Pi Gateway outside the maintained OWUI source tree.
- [ ] Reduce branding and navigation changes to configuration/assets where possible.
- [x] Create `PATCHES.md` listing every retained OWUI commit, rationale, owner, test, and upstream status. The rebaseline branch documents the Welcome series; future retained patches must be added as they are accepted.

### Exit gate 8

- [ ] Every retained OWUI patch is small, single-purpose, documented, and tested.
- [ ] Large product features no longer live in the OWUI fork.
- [ ] The patch series can be applied to a clean release without manual archaeology.

---

## Phase 9: Staging, cutover, and rollback

### Staging rehearsal

- [ ] Build immutable OWUI and Studio images with recorded digests.
- [ ] Provision empty OWUI and Studio databases and storage in staging.
- [ ] Run the complete bootstrap and fresh-data seed procedure.
- [ ] Run core OWUI, Studio, permission, performance, and rollback tests.
- [ ] Rehearse rollback at the OWUI, Studio, worker, and data levels.
- [ ] Record timings and refine the maintenance window.

### Production readiness

- [ ] Announce the maintenance and rollback window.
- [ ] Keep the legacy deployment unchanged while provisioning the fresh deployment.
- [ ] Provision independent empty production storage for OWUI and Studio.
- [ ] Deploy the tested image digests and configuration.
- [ ] Initialise each new database once from the designated process.
- [ ] Run smoke tests before restoring user access.
- [ ] Monitor authentication, errors, latency, workers, storage, and initialisation health.

### Exit gate 9

- [ ] Core OWUI and released Studio features meet their acceptance tests in production.
- [ ] No unresolved security or data-integrity issue remains.
- [ ] Rollback means routing users back to the unchanged legacy deployment; no new data is converted back.

---

## Phase 10: Establish the ongoing upgrade routine

- [ ] Pin production to tested upstream release tags, never `main` or `dev`.
- [ ] Run scheduled CI against the next upstream release without automatically deploying it.
- [ ] Test clean installation, upgrades from the first fresh-deployment schema onward, adapter contracts, and end-to-end workflows.
- [ ] Keep an OWUI compatibility matrix in the Studio repository.
- [ ] Use a short-lived upgrade branch for each upstream release.
- [ ] Rebase or reapply only the documented minimal patch series.
- [ ] Upgrade Studio independently unless an OWUI API contract changes.
- [ ] Review retained patches every release and remove those accepted or superseded upstream.
- [ ] Test backup restoration periodically, not only during upgrades.
- [ ] Define owners and release notes for both applications.

### Final exit gate

- [ ] The maintained OWUI branch is close to upstream v0.10.2 or newer.
- [ ] Studio owns Flows, Media/timeline, and selected custom experiences.
- [ ] A subsequent upstream upgrade has been rehearsed successfully.
- [ ] The legacy deployment can be retired after the agreed retention period.

---

## Decision log

Record material decisions here or link to separate decision records.

| Date | Decision | Reason | Revisit when |
| --- | --- | --- | --- |
| 2026-07-11 | Rebaseline from clean Open WebUI v0.10.2 | The legacy fork and unfinished v0.9.4 port are too divergent for a sustainable merge | A newer release is selected before implementation starts |
| 2026-07-11 | Extract Flows and video timeline from OWUI core | They are independent product domains with their own persistence and release needs | OWUI provides an official stable extension architecture covering these needs |
| 2026-07-11 | Remove the fork scheduled-prompt feature and use upstream Automations/Calendar | v0.10.2 now provides the required upstream feature; maintaining duplicate UI, APIs, tables, scheduling, and notifications would add unnecessary fork surface | Upstream removes the capability or a documented production requirement is proven missing |
| 2026-07-11 | Start v0.10.2 and Studio with fresh data | Legacy data does not need to be carried forward, which removes schema conversion and custom-feature import risk | A specific legacy dataset is explicitly brought back into scope |
| 2026-07-11 | Use upstream MCP/OAuth except for a proposed tool-name resolver contribution | v0.10.2 supersedes the fork's token-auth, callback, and cleanup fixes but still requires exact tool names | Upstream accepts the resolver or intended staging models never reproduce the issue |
| 2026-07-11 | Use upstream Google Drive selected-file import and drop fork synchronisation | The upstream browser picker covers fresh imports; server OAuth and continuous sync are a separate product/security lifecycle | Continuous Drive synchronisation becomes an explicit Studio/connector requirement |
| 2026-07-11 | Use upstream admin analytics and move only LiteLLM spend reporting to Studio | v0.10.2 already owns standard analytics; LiteLLM credentials and provider-specific reporting do not belong in the OWUI patch set | Upstream gains the required LiteLLM reporting or the report is no longer needed |
| 2026-07-11 | Keep Studio OIDC provider-neutral with Okta as the intended production provider | Discovery and standards-based Authorization Code + PKCE allow automated fake-provider tests now and Okta conformance later without making a homelab IdP a production dependency | Okta requires a documented non-standard integration or the production IdP changes |
| 2026-07-11 | Keep agent definitions in OWUI and classify executable workspace models/functions for Welcome | OWUI workspace models already provide prompts, knowledge, skills/tools and user/group access; the legacy Welcome page correctly intersected them with the authorised executable catalogue | Revisit only if upstream replaces these APIs or adds a first-class equivalent catalogue |
| 2026-07-11 | Prefer a thin, feature-flagged OWUI Welcome page while retaining Studio as a compatibility implementation | Welcome presents OWUI-owned concepts and benefits from native chat/workspace navigation; Media and other independent schemas still belong in Studio | Upstream accepts an equivalent dashboard, or the UI patch becomes materially costly to rebase |

## Evidence log

Add concise links or references as work completes.

| Phase | Evidence | Result |
| --- | --- | --- |
| 0 | `docs/rebaseline-phase-0-source-record.md` | Root, compatibility submodule, captured legacy source, archived v0.9.4 rebaseline, and clean v0.10.2 baseline refs are published to canonical private Gitea repositories; a fresh recursive clone succeeds; live deployed SHA, branch-protection confirmation, routing, image, topology, and rollback evidence still required |
| 1 | `docs/feature-ledger.md` | Source-level inventory, disposition, ownership, fresh-start acceptance, and rollback ledger created; live usage/deployment reconciliation remains open; no legacy data migration or import is in scope |
| 2 | `docs/v0.10.2-baseline-comparison.md`; `docs/v0.10.2-configuration-matrix.md`; local branch/worktree `rebaseline/upstream-v0.10.2` | Clean build/start, admin/auth, OpenAI-compatible discovery/SSE chat, explicit model grant/denial, private file/Knowledge denial, processing, attachment, and retrieval pass; source variables classified; real providers, OAuth/MCP/Drive, proxy/browser checks, upstream type check, live deployment names, and signature trust remain |
| 3 | `docs/owui-studio-contract.md` | Ownership, shared-OIDC/token-exchange authentication, fallback launch exchange, minimum user-scoped API surface, typed adapter policy, denial matrix, and narrow patch set documented; no direct database access or administrator browser credential required |
| 4 | Studio repository `git.theoldschool.house/robert/open-webui-studio` through `b40cd51`; functions repository `git.theoldschool.house/robert/open-webui-functions-tools` through `196b1a4`; live Keycloak realm `homelab` | Canonical origins are private Gitea; Studio shell, non-root container, typed v0.10.2 adapter, SQLite migrations, encrypted sessions, provider-neutral OIDC routes, and fake IdP pass automated validation; shared Keycloak login and OWUI provider-token exchange were manually verified against a locally built clean v0.10.2 image; live Okta, second-user matrix, proxy, and rollback checks remain |
| 5 | OWUI branch `rebaseline/upstream-v0.10.2` commits `559cd28f1`, `e9ca2fc11`, and `3ccdbe83c`; branch `PATCHES.md`; Studio commits `0d74d7f` and `abb86cc`; `docs/welcome-feature-maintenance-options.md` | The Studio-owned agent experiment was reverted. Native OWUI Welcome is a disabled-by-default UI island using authorised executable models, accessible workspace models, active functions, and native chat initialisation. The full legacy experience is restored and hardened: composer integrations, Files API upload/handoff, dictation, voice mode, tested local agent order, responsive launchers, and quick actions. Four focused tests and the production build pass. Live interactions were manually verified in Chrome at normal and responsive/narrow widths; physical-device mobile verification and the two-user browser proof remain. |
| 6 | `docs/media-contract-review.md`; legacy `7f562ebb5c0893a886adc02521251fce7b725cb2`; OWUI `ecd48e2f7`; Studio commits `5b5bb4e`, `08a332f`, `278be05`, `57f7673`, and `dc082a9`; image `open-webui-studio:media-perf-57f7673` | The first-release Media browser gate is complete. Read-only comparison, typed adapter, authenticated content proxy, first Media page, representative-library performance hardening, deleted-file race proof, and live two-user isolation pass. Self-owned listing/search, administrator denial, pagination, preview/download streaming, range forwarding, MIME/header hardening, cancellation, sequential bounded scans, zero grid-body preload, navigation, UI states, 26 server tests, build, non-root container startup, user-led authenticated preview/download checks, and hidden cross-user `404` pass. Upload, deletion, generation/processing controls, chat/folder hierarchy, prompt recovery, and timeline persistence remain out of the browser slice. No OWUI bridge is initially justified. |
| 7 | `docs/flow-extraction-contract.md`; legacy `7f562ebb5c0893a886adc02521251fce7b725cb2`; archived v0.9.4 `d62f9dc9250be3699d27941f608712d46f4c3f38`; OWUI `ecd48e2f7`; Studio through local commit `70462a8` on `codex/flows-foundation` | Studio owns strict definitions, immutable versions, encrypted execution history, ordered checkpoints, bounded events, execution credentials, worker claims and identity, concurrency, heartbeats, cancellation, recovery, terminal transitions, queue orchestration, the in-process runner, CRUD/execution APIs, owner-scoped SSE, and the editable Svelte Flow workspace. The canvas is the primary surface and supports deterministic add/delete/connect plus in-canvas settings for Input, Model, Transform, and Output only; deferred types remain rejected. Saved definitions and execution overlays remain separate, unsaved edits cannot change the pinned run-input contract, and the server validator remains authoritative. The user confirmed live execution before the canvas work and accepted the locked canvas before requesting editable topology. All 126 Studio server tests, focused graph/component tests, zero-warning Svelte check, full ESLint, changed-file formatting, the production build, container health, and HTTP smoke checks pass. Remote publication, audit records, representative two-user Flow execution, and user-led editable-canvas interaction remain. |
| 8 | `docs/mcp-oauth-google-drive-comparison.md` | MCP/OAuth fixes classified commit by commit; use upstream Google Drive selected-file import; fork server OAuth/sync dropped; tool-name resolver and optional Drive multi-file handling identified as narrow upstream contribution candidates |
| 9 | | |
| 10 | | |
