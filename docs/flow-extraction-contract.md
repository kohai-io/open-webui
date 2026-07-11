# Studio Flows extraction contract

Date: 2026-07-11

## Decision

Extract Flows into Studio as a new, fresh-start product domain. Studio owns flow definitions, immutable versions, executions, checkpoints, cancellation, and execution history. Open WebUI remains the owner of users, authentication, model access, files, Knowledge, tools, and provider connections.

Do not port the legacy Flow database tables, browser-side executor, import/export path, or OWUI Flow routes. The legacy implementation is behavior reference only.

The first release supports a small server-executed text workflow:

```text
Input -> Model -> Transform -> Output
```

It supports branching-free directed acyclic graphs composed of `input`, `model`, `transform`, and `output` nodes. Unsupported node types fail definition validation; they are not retained as opaque nodes and are not skipped at runtime.

## Sources reviewed

- Legacy behavior: immutable `legacy/v0.6.36-custom` commit `7f562ebb5c0893a886adc02521251fce7b725cb2`.
- Unfinished rebaseline: immutable `archive/rebaseline-v0.9.4` commit `d62f9dc9250be3699d27941f608712d46f4c3f38`.
- OWUI baseline: `v0.10.2` commit `ecd48e2f718220a6400ecf49eafd4867a38feb10`.
- Studio adapter and persistence foundation: `open-webui-studio` through Media commit `dc082a9`.
- Existing ownership and authentication boundary: `docs/owui-studio-contract.md`.

## Legacy findings

The legacy editor defined nine node types:

| Node | Legacy behavior | First release |
| --- | --- | --- |
| Input | Browser-provided text plus inferred file IDs | Text input only |
| Model | Browser calls OWUI chat completion with the user's browser token | Server-side through the typed adapter; base text models only |
| Output | Formats text/JSON/Markdown and sometimes uploads generated media | Text or JSON result only |
| Transform | Uppercase, lowercase, trim, replace, extract, and template operations | Retain with strict typed configuration and bounded output |
| Conditional | Evaluates a comparison but has incomplete branch execution semantics | Defer |
| Merge | Combines multiple inputs | Defer until fan-in ordering is specified |
| Loop | Recursively executes an `EACH` branch in the browser | Defer; requires bounded durable checkpoint semantics |
| Knowledge | Calls legacy retrieval endpoints and derives internal collection names | Defer; Knowledge access/query contract is not in the Studio adapter |
| Web search | Calls processing and retrieval endpoints and logs returned content | Defer; connector, SSRF, retention, and API stability require a separate contract |

The `/api/v1/flows/{id}/execute` legacy endpoint was a placeholder that returned `delegated_to_client`. The browser performed execution, cancellation, file fetching, model calls, Knowledge retrieval, and web search. The browser then submitted its own claimed status, outputs, node results, errors, and duration to the execution-history endpoint.

That architecture is not trustworthy or durable: the client controls execution claims, tokens and prompts exist in browser code, closing the page stops work, retry boundaries are ambiguous, and extensive console logging includes prompts, inputs, results, response bodies, and retrieval content.

The v0.9.4 port consolidated the same OWUI-owned tables into one migration and reduced router code. It did not establish server-side execution, immutable versions, durable checkpoints, stable validation, or an independent Studio ownership boundary. Reuse no persistence code from it.

## Ownership and identity

- Every flow has one `owner_owui_user_id`, derived from the authenticated server-side Studio session.
- Every version, execution, checkpoint, event, and audit record is reached through its owning flow and the same owner predicate.
- Browser-supplied owner IDs, roles, subjects, session IDs, execution status, timestamps, and node results are ignored or rejected.
- Administrators receive no cross-user bypass in Studio Flows.
- The first release has no sharing, groups, collaboration, public links, templates, or transfer of ownership.
- OWUI IDs are opaque strings, never foreign keys into OWUI storage.

Cross-user reads, mutations, cancellation requests, event streams, and guessed IDs return the same `not_found` result as missing records.

## Definition and version contract

Definitions use a versioned JSON envelope:

```ts
interface FlowDefinitionV1 {
  schemaVersion: 1;
  nodes: FlowNodeV1[];
  edges: FlowEdgeV1[];
}
```

`studio_flow` stores flow identity, owner, display metadata, the current immutable version number, and an optimistic-concurrency revision. `studio_flow_version` stores the complete validated definition and its canonical SHA-256 hash. Versions are append-only.

Creating a flow atomically creates version `1`. Updating a flow requires the current revision, validates the complete replacement definition, creates the next version, and advances the flow revision in one transaction. A stale revision returns `conflict` and never creates a partial version. Renaming or changing the description also creates a version so history reflects the saved user-visible state.

Only the owner may delete a flow, and Studio rejects deletion while an execution is non-terminal. A successful delete removes the flow, versions, executions, checkpoints, and execution payloads in one transaction. The first release has no recycle bin.

## First-release node schemas

### Input

- Stable user-defined input key.
- Value supplied when an execution is created; definitions may contain a non-secret default.
- String values only, with explicit byte and character limits.
- No file IDs, URLs, environment lookups, or secret fields.

### Model

- Opaque OWUI model ID.
- Prompt template using only documented references to upstream node outputs, such as `{{node.input.output}}`.
- Optional allowlisted parameters: temperature and maximum output tokens within configured bounds.
- Text request and text response only.
- No files, images, video, tools, functions/pipes, Knowledge attachment, web search, direct connections, terminal access, or arbitrary request fields.

The worker revalidates model availability for the execution owner before invocation. A removed or inaccessible model returns `dependency_not_found` without exposing model metadata.

### Transform

- Operations: `uppercase`, `lowercase`, `trim`, `replace`, `extract`, and `template`.
- Exact typed configuration per operation; unknown fields are rejected.
- Regular expressions are excluded initially. Replace is literal, and extract uses a bounded JSON property path rather than executable expressions.
- Input and output sizes are bounded.

### Output

- Produces either text or validated JSON.
- One terminal output node is required in the initial vertical slice.
- No upload, file generation, HTML rendering, Markdown execution, or media retention.

## Graph validation

Validation occurs before every version save and again before execution. It requires:

1. `schemaVersion` exactly `1`;
2. only supported node and edge fields;
3. unique bounded IDs matching the documented identifier grammar;
4. at least one input and exactly one output;
5. every edge references existing nodes and allowed ports;
6. no self-edge, duplicate edge, cycle, disconnected node, or unreachable output;
7. a maximum of 50 nodes, 100 edges, and a bounded canonical definition size;
8. node-specific configuration and template references that resolve to upstream nodes;
9. no secret-like keys, bearer tokens, connection credentials, embedded data URLs, or arbitrary URLs.

Validation returns stable field-addressed errors. It never partially repairs a definition.

## OWUI adapter contract

Extend the existing typed server-side adapter; do not create a Flow-specific OWUI client.

The first release needs:

- current identity and token expiry from the established Studio session;
- current user-visible model listing for save-time assistance and run-time revalidation;
- a non-streaming text completion operation against pinned v0.10.2;
- existing timeouts, cancellation, correlation IDs, error mapping, and non-retry mutation rules.

The model operation must have an executable compatibility fixture before worker implementation. First test whether a non-persisted `/api/chat/completions` request can execute an authorised base model without creating an OWUI chat. Do not create hidden or disposable OWUI chats merely to imitate the legacy executor. If pinned v0.10.2 cannot support the narrow operation safely, stop and record the missing contract before proposing an OWUI bridge.

The browser never receives an OWUI token and never calls the completion endpoint directly.

## Durable execution model

Creating an execution validates the requested flow/version and runtime inputs, then inserts a `queued` execution with an owner-scoped idempotency key. It never accepts client-supplied results or terminal status.

Execution states are:

```text
queued -> running -> succeeded
                  -> failed
                  -> cancel_requested -> cancelled
```

The worker:

1. atomically claims a queued execution;
2. pins the immutable flow version;
3. evaluates nodes in deterministic topological order;
4. commits each completed node result as a checkpoint before advancing;
5. refreshes its heartbeat while running;
6. checks cancellation before and after every node and aborts an active OWUI request where supported;
7. commits exactly one terminal state.

One execution per owner runs concurrently by default. Global and per-owner limits are configurable and server-enforced. Definitions specify no concurrency values.

The worker may resume deterministic nodes from committed checkpoints after a restart and reuse a completed model checkpoint. If the worker disappears during a model request, the billing and result remain uncertain. The worker does not repeat that request; the execution fails with `model_result_unknown`, and the user may rerun it with a new idempotency key.

The worker does not retry model calls after dispatch. It uses bounded backoff for rate limits and upstream failures only when the adapter can prove that OWUI did not accept the request. Studio enforces whole-run and per-node deadlines.

## Execution credentials

A background worker must not depend on a browser cookie or store a raw session handle in an execution. At queue time, Studio creates an encrypted, execution-bound OWUI credential lease whose expiry cannot exceed the OWUI token or Studio session expiry. The lease contains no refresh token, is usable only for its owner and execution, and is deleted on terminal state or expiry.

If the lease expires before a model node begins, the execution fails `authentication_required`; it does not use an administrator or service credential. Account disablement or a changed OIDC-to-OWUI identity binding fails closed on the next OWUI call.

Implement this lease only after a focused security review of the existing encrypted session store. Do not copy encrypted session payloads into ordinary execution JSON.

## Persistence outline

Use numbered Studio SQLite migrations, with foreign keys enabled:

- `studio_flow`: owner, name, description, current version, revision, timestamps;
- `studio_flow_version`: flow ID, version, canonical definition, definition hash, creator, timestamp;
- `studio_flow_execution`: owner, pinned version, state, idempotency key, timestamps, heartbeat, stable error code;
- `studio_flow_execution_node`: execution ID, node ID/type, state, attempt, timing, encrypted result/checkpoint payload;
- `studio_flow_credential_lease`: execution-bound encrypted credential and expiry;
- `studio_flow_event`: bounded sequence of owner-visible state-transition metadata.

Raw prompts, runtime inputs, model outputs, and checkpoint values are user data. If retained for execution history or recovery, store them in encrypted payload columns using the established Studio encryption key. Do not put them in searchable metadata, audit rows, URLs, exceptions, or logs.

Migrations are forward-only and transactional. Document backup/restore and rollback by restoring the previous Studio image and database backup; do not attempt to downgrade OWUI or change its schema.

## Browser and event surface

The browser may create, list, read, update, delete, run, cancel, and inspect its own flows through same-origin `/studio/api/flows` routes. All routes derive identity from the Studio session.

Execution progress uses an authenticated owner-scoped server-sent event stream initially. Events contain execution ID, sequence, node ID/type, state, timing, and stable error code only. They exclude prompts, inputs, outputs, tokens, credentials, and upstream response bodies. Reconnection resumes from a bounded sequence number and falls back to execution-state polling.

The editor is ported only after persistence, validation, adapter, and worker service tests pass. It must consume Studio types and routes and must not import OWUI stores, browser tokens, or legacy API modules.

## Secrets and connectors

The first release has no connector, tool, web-search, terminal, or arbitrary HTTP nodes and therefore accepts no connector secrets.

Future connector nodes must store encrypted credentials separately and reference them by opaque Studio credential ID. Definitions, versions, exports, execution events, audit records, and logs must never contain credential values. Adding any connector requires its own outbound-host policy, redaction tests, rotation/revocation behavior, and permission contract.

## Stable error codes

At minimum:

- `not_found`;
- `validation_failed`;
- `conflict`;
- `authentication_required`;
- `dependency_not_found`;
- `rate_limited`;
- `upstream_unavailable`;
- `timeout`;
- `cancelled`;
- `model_result_unknown`;
- `internal_error`.

User-facing errors may name the current user's flow or node but must not include upstream bodies, tokens, another user's identifiers, prompt text, or model output.

## Required tests before editor porting

1. Empty-database migrations create only Studio Flow tables and are idempotent.
2. Two users cannot list, read, update, delete, execute, cancel, stream, or infer each other's records.
3. Browser-supplied ownership, execution status, results, timestamps, and unknown definition fields are rejected or ignored as specified.
4. Definition validation covers unsupported nodes, malformed configuration, bad references, cycles, disconnected nodes, limits, and secret-like values.
5. Create and update atomically create immutable versions; stale revisions produce no version.
6. Executions pin a version and are unaffected by a later flow edit.
7. The worker claims once, writes checkpoints in deterministic order, respects concurrency, and commits one terminal state.
8. Duplicate idempotency keys do not create or dispatch duplicate work.
9. Cancellation before dispatch, between nodes, and during an OWUI request reaches `cancelled` safely.
10. Worker restart resumes deterministic checkpoints without repeating an uncertain model call.
11. Model access is revalidated for every run, including administrator and removed-model cases.
12. Pinned v0.10.2 completion fixtures cover success, denial, malformed response, timeout, rate limiting, cancellation, and upstream failure without creating an OWUI chat.
13. Credential leases are execution-bound, encrypted, expiry-bounded, deleted after completion, and unusable across users or executions.
14. Logs, audit rows, events, URLs, and stable errors contain no tokens, prompts, inputs, outputs, checkpoint payloads, or upstream bodies.
15. Studio blocks deletion during active execution and otherwise removes all owned Flow data in one transaction.

## Explicitly deferred

- legacy import/export and templates;
- sharing, groups, collaboration, public links, and schedules;
- conditional, merge, loop, Knowledge, web-search, file/media, tool/function, connector, terminal, and arbitrary HTTP nodes;
- streaming model output and browser-side execution;
- generated-file upload and retention;
- automatic retries of dispatched model calls;
- visual-editor porting until the contract tests pass.

Each deferred node type requires an explicit schema, permission boundary, deterministic execution/checkpoint semantics, resource limits, stable errors, redaction tests, and v0.10.2 adapter fixture before admission.

## First implementation deliverable

The first implementation deliverable adds numbered migrations, typed definition validation, immutable version CRUD, and two-user service tests. It does not include the legacy editor or execute model calls.

## Foundation implementation evidence

Studio commit `6b957d0` on published branch `codex/flows-foundation` implements this first deliverable from Media commit `dc082a9`:

- migration `0003_flows.sql` creates flows, immutable versions, executions, node checkpoints, credential leases, and bounded events in the Studio database;
- composite foreign keys enforce consistent ownership across flows, versions, executions, and events;
- `schemaVersion: 1` validation accepts Input, Model, Transform, and Output nodes and rejects deferred nodes, unknown fields, secret material, bad templates, invalid references, cycles, disconnected graphs, and configured limits;
- `FlowStore` provides owner-scoped create, list, read, update, delete, and version history with revision conflicts and active-execution deletion guards;
- empty-database and existing-0001/0002 migration tests pass without changing OWUI storage;
- 22 Flow assertions pass as part of the 48-test Studio server suite; Prettier, ESLint, zero-warning Svelte check, and the production build pass.

The foundation adds no browser routes, editor, worker, credential-lease service, or OWUI completion call.

Studio commit `259179e` on the same published branch adds the pinned v0.10.2 text-completion adapter contract:

- the adapter revalidates the selected model against the current user's model, workspace-model, and function catalogues and admits base text models only;
- it sends one non-streaming `POST /api/chat/completions` request without `parent_id`, `chat_id`, `user_message`, `session_id`, files, tools, or browser-visible credentials;
- pinned v0.10.2 treats an absent `parent_id` as the direct legacy API path with no chat management, and the fixture proves Studio never calls an OWUI chat-creation route;
- the adapter accepts one bounded text choice and rejects empty, oversized, or malformed responses;
- fixtures cover inaccessible agents/functions, invalid input, `429`, `503`, `504`, internal timeout, caller cancellation, network failure, and single-dispatch no-retry behavior;
- 64 server tests pass; Prettier, ESLint, zero-warning Svelte check, and the production build pass.

This contract slice invoked no live model.

Studio commit `a18151f` adds the execution credential-lease boundary:

- migration `0004_flow_credential_leases.sql` adds the owner to each lease and enforces the execution-owner foreign key;
- AES-256-GCM associated data binds each ciphertext to its owner and execution, so copied ciphertext fails authentication;
- the service caps each lease at five minutes or the upstream token expiry, whichever comes first, and deletes expired rows on access or sweep;
- database triggers reject leases for inactive executions and delete credentials when cancellation starts or an execution reaches a terminal state;
- the migration discards pre-contract leases because their ciphertext lacks execution-bound associated data;
- tests cover encryption at rest, owner isolation, cross-execution replay, expiry, invalid credentials, migration, cancellation, and terminal cleanup.

The full Studio server suite has 73 passing tests. Scoped Prettier, project ESLint, zero-warning Svelte check, and the production build pass. Resume with the execution lifecycle store for idempotent creation, claims, checkpoints, events, heartbeat recovery, cancellation, and terminal transitions before connecting the durable worker.

Studio commit `f31dfe1` implements the execution lifecycle boundary:

- migration `0005_flow_execution_lifecycle.sql` adds hashed claim tokens, claim expiry and attempts, deterministic node order, claim indexes, and terminal claim cleanup;
- execution creation validates runtime inputs, pins an immutable version, encrypts retained inputs, creates ordered node rows, and returns the original owner-scoped execution for a duplicate idempotency key;
- SQLite immediate transactions enforce atomic claims, the global worker limit, and one active execution per owner;
- the store encrypts checkpoints and outputs with owner, execution, node, and attempt context while events retain metadata only;
- heartbeats extend claims, queued cancellation settles without dispatch, and claimed cancellation requires worker acknowledgement;
- stale deterministic work returns to the queue, while an uncheckpointed model call fails `model_result_unknown` and cannot dispatch again;
- failure and cancellation settle open nodes, terminal transitions clear claim capabilities, and the database retains the last heartbeat for history;
- migration tests fail pre-contract active executions closed because they lack claim metadata and node order.

The full Studio server suite has 85 passing tests. Scoped Prettier, project ESLint, zero-warning Svelte check, and the production build pass. The tests use no live model. Resume with the durable worker core using a dependency-injected OWUI stub. Prove ordered evaluation, credential acquisition, model dispatch boundaries, deadlines, heartbeat refresh, and `AbortController` cancellation before adding routes or the editor.

Studio commit `53fe122` implements the durable worker core:

- `FlowWorker` recovers stale claims, claims one queued execution, evaluates nodes in stored order, commits each checkpoint, and seals the execution result;
- Input, Transform, and Output evaluation runs without an OWUI credential; Model acquires its execution lease at dispatch time and calls the proven text-completion adapter once;
- the worker refreshes heartbeats during Model calls, enforces separate run and node deadlines, and aborts the adapter signal after an owner cancellation request;
- completed checkpoints survive worker recovery, while an abandoned in-flight Model node fails `model_result_unknown` before a new worker can dispatch it;
- OWUI denial and failure codes map to stable Flow errors without retries or upstream response data in events;
- graph validation rejects fan-in for transforms and outputs that lack merge semantics;
- execution heartbeats cannot revive an expired claim, and a background heartbeat error aborts and seals the run.

The test suite uses the real adapter against its OWUI stub for the success path and controlled clients for failure timing. All 100 Studio server tests pass. Scoped Prettier, project ESLint, zero-warning Svelte check, and the production build pass. The tests make no live model call.

The worker remains a server library. Studio has no background runner, Flow API routes, event stream, or UI. Resume with an owner-scoped queue service that creates the execution and credential lease in one transaction, then add the worker runner and Flow API surface before building the first UI.

Studio commit `69029f9` adds queue orchestration, the runner, and the owner-scoped API surface:

- `FlowQueueService` creates an execution and its credential lease in one SQLite immediate transaction, bounds the lease by OWUI token plus absolute and idle session expiry, and wakes the runner after commit;
- `FlowWorkerRunner` polls without overlapping runs, coalesces wakeups, contains worker errors, and starts from the Studio service lifecycle unless `FLOW_WORKER_ENABLED=false`;
- migration `0006_flow_worker_identity.sql` records the configured worker ID with each claim for multi-replica diagnostics;
- Flow APIs support create, list, read, update, delete, immutable version history, execution queue/list/read, and cancellation;
- execution creation requires an `Idempotency-Key` header, rejects unknown body fields, and derives ownership plus the OWUI credential from the server session;
- mutations reject cross-origin browser requests, while missing and cross-user records return the same `not_found` response;
- the authenticated SSE endpoint supports reconnect cursors and streams bounded metadata without input, output, prompt, credential, or upstream body data;
- `.env.example` and the Studio README document runner settings and the heartbeat-before-claim-expiry constraint.

All 111 Studio server tests pass. Scoped Prettier, project ESLint, zero-warning Svelte check, and the production build pass. Automated tests cover transaction rollback, session expiry, runner polling and wakeups, CRUD, version conflict, active-delete guard, cancellation, two-user hiding, same-origin enforcement, and terminal SSE redaction.

This slice made no live model call and did not rebuild or start a deployed Studio container. Resume with the first Flow UI: list and create a constrained linear text flow, run it with an idempotency key, show execution state and node progress, allow cancellation, and consume the SSE endpoint. Keep arbitrary graph editing and deferred node types out of that slice.

The local `codex/flows-foundation` worktree contains Studio commit `e9accc5`, which implements the first Flow UI and awaits remote publication:

- `/studio/flows` lists owner-scoped flows and execution history;
- the editor creates and updates one constrained Input, Model, optional Transform, Output shape and treats definitions with unsupported settings as read-only;
- the runner supplies an idempotency key, follows owner-scoped SSE events, displays node state and output, and supports cancellation;
- Studio navigation links to Flows from Welcome, Agents, and Media;
- page loading admits authorised base models and returns the signed-out state without constructing production services;
- the UI preserves history after an update and closes the event stream when an execution event reaches a terminal state.

All 115 Studio server tests pass. Scoped Prettier, ESLint, zero-warning Svelte check, the production build, and the signed-out headless route test pass. Image `open-webui-studio:flows-ui-local` runs in the healthy `owui-studio-media-test` container at `http://localhost:5173/studio/`. HTTP checks return `200` for `/studio/flows` and the health endpoint. The checks made no live model call. The user asked us to stop in-app browser testing because it crashes the ChatGPT app.

The next gate is a user-led authenticated create, save, run, progress, cancellation, history, and delete check against the rebuilt container. After that check, add metadata-only audit records and the representative two-user Flow test before closing the Phase 7 exit gate.
