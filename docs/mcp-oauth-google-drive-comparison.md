# MCP, OAuth, and Google Drive comparison against v0.10.2

Recorded on 2026-07-11 against fork commit `e63358ac5` and upstream `v0.10.2` (`ecd48e2f718220a6400ecf49eafd4867a38feb10`). This is a source-level comparison. Live OAuth, MCP, and Google integration tests still require fresh provider credentials and endpoints.

## Decision summary

| Area | Decision | Maintained OWUI impact |
| --- | --- | --- |
| MCP unprefixed tool-name resolution | **Contribute upstream** | Do not patch by default; retain a temporary focused patch only if the intended staging model reproduces the failure |
| MCP OAuth token endpoint authentication method | **Use upstream** | Drop fork commit `f71acf28e`; v0.10.2 passes the method through |
| MCP OAuth callback duplicate client parameters | **Use upstream** | Drop fork commit `e98245922`; v0.10.2 explicitly avoids duplicate credentials |
| MCP client cleanup and diagnostics | **Use upstream** | Drop fork commit `b4098ef1e`; v0.10.2 cleanup is safer; never port token-preview logging |
| Non-standard dynamic-registration array coercion | **Drop** | Do not carry fork commit `663a8737b` without a current reproducible provider requirement |
| General login OAuth/OIDC | **Use upstream** | Configure fresh providers and sessions; do not port fork session state |
| Google Drive selected-file chat import | **Use upstream** | Configure v0.10.2 picker credentials and require fresh browser authorisation |
| Google Drive multi-file result handling | **Contribute upstream** | Upstream enables multi-select but consumes only the first selected document; fix upstream if this workflow is required |
| Google Drive server OAuth/settings/sync-all | **Drop** | Do not port the custom router, settings page, localStorage token fallback, or sync utilities |

## MCP tool-name resolution

Fork commits `6ff7ca430` and `a608f839c` address two tool execution paths. They accept an exact registered name first, then resolve an unprefixed model request such as `search` to a unique registered suffix such as `amplitude-mcp_search`. Ambiguous suffixes are rejected.

The v0.10.2 middleware still performs exact lookups in both relevant paths:

- tool dispatch around `backend/open_webui/utils/middleware.py:1184`
- native response tool dispatch around `backend/open_webui/utils/middleware.py:4706`

No equivalent unique-suffix resolver or regression test was found. This is a real behavioural gap, but its workaround changes global tool dispatch semantics. The preferred path is an upstream contribution with tests covering:

1. exact name wins;
2. one unique suffix resolves;
3. two matching suffixes fail closed;
4. an unknown tool fails without disclosure of sensitive server configuration;
5. the resolved name is used consistently for direct execution and result processing.

A temporary OWUI patch is justified only if the intended staging model actually emits unprefixed names and blocks required MCP use.

## MCP OAuth and client lifecycle

| Fork change | v0.10.2 evidence | Decision |
| --- | --- | --- |
| `f71acf28e`: pass `token_endpoint_auth_method` into the registered Authlib client | `OAuthClientManager.add_client()` includes `token_endpoint_auth_method` in `client_kwargs`; discovery/DCR also selects a supported method | Drop fork commit |
| `e98245922`: avoid explicitly resending client ID/secret during MCP callback | `handle_callback()` contains the same explicit warning and calls `authorize_access_token()` only with optional resource | Drop fork commit |
| `663a8737b`: coerce single-item `client_id`/`client_secret` arrays from DCR | No equivalent coercion found; OAuth registration requires scalar identifiers | Drop unless a current provider is proven non-conformant; then contribute a validated normalisation upstream |
| `b4098ef1e`: guard a missing exit stack | v0.10.2 `disconnect()` is idempotent, clears state before closing, and handles cancellation/task-group constraints | Drop fork commit |
| `b4098ef1e`: diagnostic token preview | Not required for functionality and leaks a token prefix into logs | Drop unconditionally |
| hard-coded 10-second initialise timeout | v0.10.2 uses configurable `MCP_INITIALIZE_TIMEOUT` | Use upstream |

Upstream also includes protected-resource metadata discovery/scopes, static OAuth 2.1 support, multi-node client recovery, configurable SSL/timeouts, OAuth session persistence, and user-scoped session deletion. These substantially supersede the older fork implementation.

## General OAuth/OIDC

The v0.10.2 general login flow includes capabilities added after the fork baseline:

- server-side runtime configuration;
- audience and authorisation parameters;
- optional access-token client ID behaviour;
- refreshed JWKS handling after signing-key rotation;
- refresh-token scope support;
- token exchange controls;
- encrypted OAuth client/session material;
- back-channel logout and configured sign-out redirect;
- user/group/role refresh controls and account policy checks.

The fresh deployment should use this upstream implementation without copying OAuth sessions, tokens, encryption keys, or browser state. Provider-specific login, callback, refresh, logout, issuer/audience, disabled-account, and negative tests remain staging work.

## Google Drive

### What v0.10.2 provides

- Feature flag and admin configuration.
- Browser-visible picker `client_id` and API key through `/api/config`.
- Google Identity Services browser token client.
- Scopes `drive.readonly` and `drive.file`.
- Picker support for PDFs, text, DOCX, and Google Docs, Sheets, and Slides exports.
- Browser download of the selected file followed by ordinary authenticated OWUI upload.
- An in-memory access token; page reload or expiry causes fresh browser authorisation.

This is sufficient for the selected-file import workflow and keeps administrator credentials and refresh tokens out of the browser.

### Fork functionality not present upstream

- `/api/v1/google-drive/oauth` authorise, callback, token, revoke, status, and sync endpoints.
- Server-persisted Google Drive OAuth sessions.
- User settings UI for authorisation status, revoke, and sync-all.
- Browser localStorage access-token persistence/fallback.
- Drive metadata persistence for later refresh detection.
- Server and browser sync utilities.
- Sync-all and automatic Knowledge reprocessing after Drive changes.

These features add a second OAuth/session lifecycle and a long-lived synchronisation product. They are outside the required fresh selected-file workflow and should not be moved into the maintained OWUI fork. If continuous Drive synchronisation becomes a product requirement later, design it as a separately owned Studio/connector service with server-side tokens, explicit retention, audit, and revocation rules.

### Narrow upstream gaps

The upstream picker enables `MULTISELECT_ENABLED` but reads `DOCUMENTS[0]` and returns one object. The fork iterates all selected documents and returns an array. The chat upload handler in v0.10.2 also expects a single object. Multi-file selection is therefore not complete end to end upstream.

Treat this as a small upstream contribution if multi-select is required. The change needs bounded concurrency, partial-failure reporting, cancellation, file-count and size limits, and tests; do not port the fork's sequential loop and verbose token/file logging unchanged.

Shared-drive behaviour also requires a live test. The fork added `supportsAllDrives`; v0.10.2 does not visibly add that query parameter to its download/export URLs. Do not retain a patch speculatively: reproduce with an authorised Shared Drive file first, then contribute the smallest supported fix.

## Security observations

- Do not port fork logs containing token previews, user identifiers tied to token retrieval, or detailed provider responses.
- Do not persist Google access tokens in browser localStorage.
- Do not expose Google client secrets or OWUI administrator credentials to browser code.
- Fresh OAuth authorisation is required for every provider after cutover.
- Provider callbacks must use explicit production origins and HTTPS.
- Negative tests must cover wrong issuer/audience, replay/state mismatch, open redirect, cross-user session access, revoked tokens, and disabled accounts.

## Remaining live tests

1. Intended MCP server without OAuth: discovery, unique names, call, timeout, error, and cleanup.
2. Intended OAuth MCP server: DCR/static registration as applicable, PKCE, scopes/resource, callback, refresh, logout/revoke, and account isolation.
3. Intended login IdP: login, group/role refresh, logout, expiry, disabled account, issuer/audience, and negative cases.
4. Google Drive: single selected file, Google Workspace export, token expiry/re-authorisation, cancellation, inaccessible/deleted file, and Shared Drive file.
5. Multi-select only if retained as an explicit requirement.
