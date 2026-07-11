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
- [ ] Create and push an immutable `legacy/v0.6.36-custom` tag or branch.
- [ ] Preserve the unfinished v0.9.4 rebaseline as `archive/rebaseline-v0.9.4`.
- [ ] Record the deployed container image and digest.
- [ ] Record Compose files, reverse-proxy routes, volumes, environment variable names, and external dependencies.
- [ ] Record the `functions_tools` submodule revision and how it is deployed. The source revision and compatibility work are recorded; live deployment use remains unverified. See `docs/rebaseline-phase-0-source-record.md` and `docs/functions-tools-v0.10.2-file-api-compatibility.md`.
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

The immutable legacy source references must exist before maintained-source implementation begins. Live deployment, routing, image, and rollback evidence may be completed in parallel, but all three gate items must pass before Phase 9 staging/cutover.

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
- [x] `functions_tools` submodule features. See `docs/feature-ledger.md`; all pipe files were inventoried and the 19 file-API callers were patched for v0.10.2. Action/tool disposition and runtime contract tests remain open. See `docs/functions-tools-v0.10.2-file-api-compatibility.md`.

### Record for every feature

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
- [x] Create `rebaseline/upstream-v0.10.2` from the exact upstream tag. Created locally without switching the legacy working tree.
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

- [ ] OWUI owns users, groups, roles, models, agents, chats, messages, files, and knowledge.
- [ ] Studio owns preferences specific to Studio, timeline projects, flow definitions, flow versions, execution state, and execution history.
- [ ] Studio does not access `webui.db` or other OWUI storage directly.
- [ ] Studio stores OWUI IDs as opaque references and revalidates access through authenticated APIs.

### Authentication decision

- [ ] Evaluate shared OIDC for both services as the preferred solution.
- [ ] If shared OIDC is unavailable, specify a short-lived, single-use OWUI-to-Studio launch-token exchange.
- [ ] Derive identity server-side; never trust a browser-supplied OWUI user ID.
- [ ] Keep administrator credentials out of browser code and logs.
- [ ] Define logout, expiry, account disablement, and group/role refresh behaviour.
- [ ] Add negative tests for token replay, wrong issuer/audience, open redirects, and cross-user access.

### API contract

- [ ] List the minimum user-scoped OWUI operations Studio requires.
- [ ] Prefer documented OWUI APIs.
- [ ] Put OWUI response normalisation behind a typed server-side adapter.
- [ ] Add a narrow OWUI bridge endpoint only when no safe supported API exists.
- [ ] Define API compatibility fixtures for the supported OWUI version.
- [ ] Define timeouts, retries, error mapping, and request correlation IDs.

### Provisional OWUI patch set

- [ ] Studio navigation/launch seam, preferably feature-flagged or configuration-driven.
- [ ] MCP unique-suffix tool-name resolver only if intended staging models reproduce the blocker; otherwise upstream contribution only.
- [ ] Google Drive multi-file handling as an upstream contribution only if retained as a requirement.
- [x] No other OWUI patch is currently justified by the completed comparisons.

### Exit gate 3

- [ ] Identity and data ownership boundaries are documented.
- [ ] Cross-user denial tests are specified.
- [ ] The planned OWUI patch set is narrow and enumerated.
- [ ] No Studio feature requires direct OWUI database access or a browser-visible administrator key.

---

## Phase 4: Create the Studio foundation

### Repository and application

- [ ] Create the private `open-webui-studio` repository.
- [ ] Scaffold a SvelteKit TypeScript application using `adapter-node`.
- [ ] Configure deployment under `/studio`.
- [ ] Add formatting, linting, type checking, unit tests, integration tests, and Playwright tests.
- [ ] Add a production Dockerfile running as a non-root user.
- [ ] Add a health endpoint that exposes no secrets.
- [ ] Add structured logs and request correlation.

### Core services

- [ ] Implement Studio sessions and authentication.
- [ ] Implement the typed server-side OWUI adapter.
- [ ] Add a Studio-owned database and migrations.
- [ ] Add fixtures or a stub service for OWUI contract tests.
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

- [ ] Define minimal `StudioUser`, `OwuiModel`, `OwuiAgent`, and chat-launch contracts.
- [ ] Port only the reusable visual components; replace OWUI internal stores with explicit Studio data/services.
- [ ] List only models and agents available to the current user.
- [ ] Preserve Studio-owned ordering or favourites in the Studio database.
- [ ] Launch a new OWUI chat using an authorised model or agent.
- [ ] Verify deep links back to OWUI.
- [ ] Add loading, empty, permission-denied, and upstream-unavailable states.
- [ ] Add end-to-end tests for two users with different access.
- [ ] Deploy behind a feature flag or removable navigation link.

### Exit gate 5

- [ ] Welcome and Agents work in Studio without legacy OWUI UI code.
- [ ] A user cannot discover or launch inaccessible models or agents.
- [ ] Rollback requires only disabling Studio navigation or restoring the previous Studio image.

---

## Phase 6: Media browser and video timeline

### Media access

- [ ] Define a paginated, user-scoped media contract.
- [ ] Determine which file metadata and preview operations existing OWUI APIs support.
- [ ] Add only the narrow bridge endpoints that remain necessary.
- [ ] Implement pagination, lazy previews, cancellation, and bounded concurrency.
- [ ] Test large libraries and inaccessible/deleted file references.

### Timeline ownership

- [ ] Define Studio-owned project, track, clip, marker, and version schemas.
- [ ] Store OWUI file IDs as opaque external references.
- [ ] Add project migrations, autosave, optimistic concurrency, and recovery behaviour.
- [ ] Port timeline calculations and UI independently of OWUI stores and routes.
- [ ] Decide whether rendering/export belongs in the web process or a separate worker.
- [ ] Define upload, generated-output, retention, and cleanup policies.
- [ ] Add unit tests for timeline calculations and end-to-end save/reload tests.

### Exit gate 6

- [ ] Media access is user-scoped and performs acceptably on representative data.
- [ ] Timeline projects persist entirely outside OWUI's schema.
- [ ] Missing or inaccessible OWUI files fail safely without exposing metadata.
- [ ] OWUI can upgrade without migrating Studio timeline tables.

---

## Phase 7: Flows extraction

### Design before porting

- [ ] Review the legacy Flows implementation and the unfinished v0.9.4 port as reference material.
- [ ] Compare every node type and integration with v0.10.2 APIs.
- [ ] Define the supported first-release node set; archive unused nodes.
- [ ] Specify flow definition versioning and validation.
- [ ] Specify user-scoped access to models, files, knowledge, and tools.
- [ ] Define connector-secret storage and redaction.

### Studio implementation

- [ ] Move flow definitions and versions into the Studio database.
- [ ] Move execution history and checkpoints into the Studio database.
- [ ] Port the editor without OWUI internal stores or routes.
- [ ] Implement server-side flow execution in a durable worker.
- [ ] Add cancellation, retry, timeout, idempotency, and concurrency controls.
- [ ] Stream execution events to authorised users.
- [ ] Prevent client-supplied ownership or user identity.
- [ ] Add audit records without prompt, token, or secret leakage.

### Fresh-start validation

- [ ] Do not add a legacy Flow export or import path.
- [ ] Create representative supported flows from scratch in Studio fixtures and end-to-end tests.
- [ ] Confirm Studio creates no legacy Flow tables in OWUI storage.

### Exit gate 7

- [ ] Representative new flows can be created, versioned, executed, and deleted in Studio.
- [ ] Flow execution is user-scoped, observable, cancellable, and resumable as designed.
- [ ] OWUI contains no Flow domain tables, editor implementation, or execution engine.
- [ ] Studio and its worker can be upgraded or rolled back independently of OWUI.

---

## Phase 8: Remaining customisations and minimal OWUI patch set

- [x] Decide the scheduled-prompt destination: use upstream Automations/Calendar exclusively; remove the fork implementation and do not import its records.
- [x] Use upstream v0.10.2 admin analytics rather than porting the fork dashboard.
- [x] Implement optional LiteLLM spend reporting in Studio server-side admin reporting; keep credentials out of browser code and OWUI. See `docs/feature-ledger.md`.
- [x] Decide the destination of Google Drive customisations after comparing v0.10.2: use upstream picker/chat import, drop fork server OAuth/sync, and contribute multi-file handling only if required.
- [x] Use upstream v0.10.2 Agent Skills; do not port the fork implementation.
- [x] Drop MCP/OAuth fixes already present upstream. Token-auth passthrough, duplicate callback credentials, and safe cleanup are upstream; unprefixed tool-name resolution remains an upstream contribution candidate.
- [ ] Submit generally useful remaining fixes upstream where practical.
- [ ] Move experiments such as Pi Gateway outside the maintained OWUI source tree.
- [ ] Reduce branding and navigation changes to configuration/assets where possible.
- [ ] Create `PATCHES.md` listing every retained OWUI commit, rationale, owner, test, and upstream status.

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

## Evidence log

Add concise links or references as work completes.

| Phase | Evidence | Result |
| --- | --- | --- |
| 0 | `docs/rebaseline-phase-0-source-record.md` | Local source, remote, branch, submodule, and candidate deployment material recorded; live deployment, routing, image, and rollback evidence still required |
| 1 | `docs/feature-ledger.md` | Initial inventory, disposition, ownership, fresh-start acceptance, and rollback ledger created; no legacy data migration or import is in scope |
| 2 | `docs/v0.10.2-baseline-comparison.md`; `docs/v0.10.2-configuration-matrix.md`; local branch/worktree `rebaseline/upstream-v0.10.2` | Clean build/start, admin/auth, OpenAI-compatible discovery/SSE chat, explicit model grant/denial, private file/Knowledge denial, processing, attachment, and retrieval pass; source variables classified; real providers, OAuth/MCP/Drive, proxy/browser checks, upstream type check, live deployment names, and signature trust remain |
| 3 | | |
| 4 | | |
| 5 | | |
| 6 | | |
| 7 | | |
| 8 | `docs/mcp-oauth-google-drive-comparison.md` | MCP/OAuth fixes classified commit by commit; use upstream Google Drive selected-file import; fork server OAuth/sync dropped; tool-name resolver and optional Drive multi-file handling identified as narrow upstream contribution candidates |
| 9 | | |
| 10 | | |
