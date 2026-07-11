# Open WebUI–Studio contract

Status: Phase 3 contract for Open WebUI v0.10.2. This defines the integration boundary; it does not authorise either service to read the other's database or storage.

## Ownership

Open WebUI owns identities, users, groups, roles, permissions, models, agents, chats, messages, files, Knowledge, tools, and their access grants. Studio treats every OWUI identifier as an opaque string.

Studio owns Studio preferences and ordering, timeline projects and versions, flow definitions and versions, execution state/history, worker state, and Studio audit records. Studio starts with an empty database and does not create legacy OWUI tables.

Studio must never read or write `webui.db`, OWUI storage paths, vector storage, Redis keys, or internal model classes. Every OWUI reference is resolved through an authenticated API at use time. A cached display label is non-authoritative and cannot grant access.

## Authentication

### Primary decision: shared OIDC with upstream token exchange

Both services use the same OIDC provider and stable provider subject. Studio completes its own Authorization Code + PKCE flow and stores provider and Studio session material server-side. It then calls the upstream v0.10.2 endpoint `POST /api/v1/auths/oauth/{provider}/token/exchange` with the current provider access token. `ENABLE_OAUTH_TOKEN_EXCHANGE=True` is enabled only after the provider, allowed domains, subject/email claims, and account-linking policy are tested.

Studio stores the returned user-scoped OWUI JWT only in its encrypted server-side session and sends it to OWUI from the server-side adapter. It is never placed in browser JavaScript, localStorage, a URL, an analytics event, or a log. Studio does not create or retain OWUI API keys and has no administrator service credential.

The exchange requires the user to have signed into OWUI once and linked the same provider subject. The upstream exchange resolves the account by provider subject. On first successful exchange, Studio binds its `(issuer, subject)` pair to the returned OWUI user ID; later exchanges must return the same OWUI ID. Email alone is not an identity key.

### Fallback

If the selected provider cannot supply a token acceptable to upstream exchange, implement a narrow OWUI-to-Studio launch exchange only after a separate security review. The launch code must be random, single-use, audience-bound to Studio, expire within 60 seconds, bind an exact relative return path, and yield a short-lived server-side Studio session. Store only a hash of an unused code. Reject replay, absolute/cross-origin return URLs, wrong issuer/audience, expired codes, disabled users, and subject changes.

Do not implement this fallback while upstream token exchange satisfies staging.

### Session lifecycle

- Studio sessions use `Secure`, `HttpOnly`, and appropriate `SameSite` cookies, rotate after authentication, and have idle and absolute expiry.
- Logout clears the Studio session and OWUI token. Global logout also invokes the configured IdP/OWUI logout flow where supported.
- On OWUI `401`, Studio clears its cached OWUI token and attempts at most one fresh server-side exchange. A second failure requires login.
- On OWUI `403`, Studio does not refresh or retry; it returns permission denied.
- Studio refreshes identity, role, and group-dependent data on login, token exchange, and before privileged operations. Account disablement must fail closed on the next OWUI call.

## Minimum OWUI API surface

All calls carry the current user's OWUI bearer token. Studio does not call administrator list/export endpoints.

| Studio capability | v0.10.2 operation | Contract |
| --- | --- | --- |
| Establish current identity | `GET /api/v1/auths/` | Return current user ID, role, profile fields, and session status; identity must match the Studio OIDC subject binding. |
| Exchange shared OIDC token | `POST /api/v1/auths/oauth/{provider}/token/exchange` | Server-to-server only; never log either token. |
| List launchable models and agents | `GET /api/models` | This filtered endpoint is authoritative for the current user. Studio must not reconstruct access from admin model records. |
| Create a chat launch target | `POST /api/v1/chats/new` | Create only for the current user using an ID returned by the filtered model endpoint. |
| Read/update a Studio-launched chat when needed | `GET /api/v1/chats/{id}` and `POST /api/v1/chats/{id}` | OWUI enforces ownership/access; Studio maps missing and denied responses without revealing metadata. |
| List/search media | `GET /api/v1/files/`, `GET /api/v1/files/search`, and `GET /api/v1/files/count` | Use bounded pages and user-scoped results. Never use admin/all-files methods. |
| Read media metadata/content | `GET /api/v1/files/{id}` and `GET /api/v1/files/{id}/content` | Revalidate on every preview/download. Proxy or redirect only according to an explicit content policy. |
| Upload/delete user media if required | `POST /api/v1/files/` and `DELETE /api/v1/files/{id}` | User initiated; enforce size/type limits and do not infer ownership from a supplied user ID. |
| List/read Knowledge references | `GET /api/v1/knowledge/`, search endpoints, and `GET /api/v1/knowledge/{id}` | Use only the user's filtered results. Mutating Knowledge is outside the first Studio slice. |

Groups and permissions are consumed only when returned for the current identity or needed for a tested user-scoped decision. Studio does not manage OWUI users, groups, models, access grants, or Knowledge in its first release.

## Server-side adapter

All OWUI calls pass through a typed Studio adapter. UI code receives normalised Studio types such as `StudioUser`, `OwuiModel`, `OwuiAgent`, `OwuiFileSummary`, and `OwuiKnowledgeSummary`, not raw OWUI responses. Unknown response fields are ignored; missing required fields fail contract validation.

Compatibility fixtures are captured from an empty v0.10.2 test deployment for success, pagination, empty results, `401`, `403`, `404`, validation error, rate limit, and upstream failure. Fixtures contain synthetic IDs and no tokens or user content. CI runs adapter contract tests against the pinned OWUI version.

Default call policy:

- connection timeout: 3 seconds;
- response-header timeout: 10 seconds for metadata calls;
- upload/download and chat operations use explicit operation-specific deadlines;
- retry one time only for idempotent reads on connection failure, `502`, `503`, or `504`, with jitter;
- never automatically retry mutations, authentication exchange, uploads, or deletes;
- propagate an allowlisted `X-Request-ID` or create a new opaque request ID;
- log operation name, status class, duration, and request ID, but no token, prompt, filename, query text, or response body.

Error mapping is stable: `401` → `authentication_required`, `403` → `permission_denied`, inaccessible `404` → `not_found`, `409` → `conflict`, `429` → `rate_limited`, timeout/`5xx` → `upstream_unavailable`. The UI must not distinguish a cross-user hidden resource from a nonexistent one.

## Security and denial tests

The contract-test matrix includes two ordinary users with disjoint models/files/chats/Knowledge, an administrator, a disabled user, and an unauthenticated session. It must prove:

1. changing an OWUI ID in a Studio request cannot reveal another user's metadata or content;
2. a model or agent omitted from `GET /api/models` cannot be launched through Studio;
3. browser-supplied user IDs, roles, group IDs, token fields, and ownership fields are ignored or rejected;
4. provider-token and fallback-code replay fail;
5. wrong issuer, audience, subject, state, nonce, PKCE verifier, and redirect origin fail;
6. expired/revoked tokens and disabled accounts fail closed;
7. logout and session rotation invalidate the prior Studio session;
8. OWUI `403`/hidden `404` responses do not leak names, sizes, owners, or existence;
9. request and error logs contain no provider token, OWUI JWT, administrator key, prompt, or file content.

## Narrow OWUI patch set

No OWUI patch is required for identity exchange or the initial adapter surface.

1. Start Studio at `/studio` through the reverse proxy with a direct URL. Add a configuration-driven OWUI navigation link only if usability testing requires it; keep it one removable commit with no Studio domain logic.
2. Keep the MCP unique-suffix resolver out of the maintained patch set unless an intended staging model reproduces the blocker. Prefer an upstream contribution with ambiguity tests.
3. Keep Google Drive multi-file handling out unless multi-select is confirmed as a requirement. Submit it upstream rather than carrying the legacy OAuth/sync implementation.
4. Add a bridge endpoint only when a documented, user-scoped v0.10.2 API cannot satisfy a concrete tested operation. Each bridge needs its own threat model, typed fixture, denial tests, owner, and removal condition.

## Version and change control

The initial supported server is Open WebUI `v0.10.2` at `ecd48e2f718220a6400ecf49eafd4867a38feb10`. An upstream upgrade is blocked until the adapter fixtures and denial suite pass. Contract changes are reviewed independently from Studio database migrations; OWUI IDs remain opaque across versions.
