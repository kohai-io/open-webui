# Studio Media contract review

Date: 2026-07-11

## Decision

Implement Media in Studio and keep Open WebUI as the owner of files, storage, authentication, and permissions. Extend the existing typed Studio adapter; do not port the legacy Media backend endpoint or add a second file model.

The first release supports:

- listing self-owned image, video, and audio files already stored in OWUI;
- filename search;
- preview;
- download;
- bounded, incremental loading.

It does not support upload, deletion, generation, transcription, narration, processing controls, chat/folder grouping, prompt recovery, or timeline editing. Timeline ownership remains a later part of Phase 6.

Self-owned means the current user's files for every role, including administrators. Studio must never expose another user's file metadata or content through Media.

## Sources reviewed

- Legacy behavior: immutable `legacy/v0.6.36-custom` commit `7f562ebb5c0893a886adc02521251fce7b725cb2`.
- OWUI baseline: `v0.10.2` commit `ecd48e2f7` in `C:\tmp\owui-v0102-baseline`.
- Existing Studio adapter: `open-webui-studio` commit `abb86cc`, including the adapter introduced by `6df9f08`; the first Media adapter implementation is `5b5bb4e` on `codex/media-adapter-contract`.
- Files API compatibility work: `open-webui-functions-tools` revision `196b1a4`.

## Legacy behavior inventory

The legacy `/workspace/media` feature used a custom `GET /api/v1/files/media-overview` endpoint. It:

- filtered files to `image/*`, `video/*`, and `audio/*`;
- sorted media by `updated_at` descending;
- returned media, related chats, related folders, and a media-only total;
- inferred file-to-chat relationships by scanning chat history;
- persisted inferred `chat_id` or an `orphan` marker into file metadata;
- supported offset/limit pagination up to 500 items;
- grouped media by folder and chat and exposed an orphan view.

The browser added filename search, media-type filters, name/type/size/date sorting, grid/list modes, selection and deletion, preview navigation, prompt recovery from chat history, “chat with file”, and “open in timeline”. For libraries over 100 items it combined server pagination with a second client-visible pagination layer.

The legacy endpoint mixed presentation concerns with file and chat persistence, mutated metadata during a read, and depended on internal database models. None of those patterns should be recreated in Studio or added to the maintained OWUI patch set.

The legacy timeline is useful as interaction and calculation reference only. Its project save/export backend was unfinished, and its routes uploaded files directly to OWUI. Studio will define timeline persistence independently when that later slice begins.

## Upstream v0.10.2 capability comparison

| Need | Upstream operation | Result |
| --- | --- | --- |
| Incremental listing | `GET /api/v1/files/?page=N&content=false` | Supported. Page size is fixed at 50 and the response contains `items` and `total`. Results include all file types, so Studio filters media. |
| Filename search | `GET /api/v1/files/search?filename=...&skip=...&limit=...&content=false` | Supported. Search is filename-only, permits bounded offset/limit, returns a list without a total, and returns `404` for no matches. Studio normalises no matches to an empty page. |
| File metadata | `GET /api/v1/files/{id}` | Supported. Returns hidden `404` for inaccessible files. Studio uses the returned `user_id` for its stricter self-owned check. |
| Preview/content | `GET /api/v1/files/{id}/content` | Supported with access revalidation. Studio must proxy the response because the OWUI bearer token remains server-side. Video/audio range and seek behavior needs an executable contract test. |
| Download | `GET /api/v1/files/{id}/content?attachment=true` | Supported. Studio proxies an allowlisted and sanitised response. |
| Processing state | `GET /api/v1/files/{id}/process/status` | Available but outside the first-release UI contract. |
| Upload/delete | Existing Files API mutations | Available but explicitly outside the first release. |
| Media-only total | None | Not required initially. Studio incrementally scans file pages and filters supported media. Add no bridge merely to reproduce the legacy count. |
| Chat/folder media hierarchy | None | Deliberately deferred. Do not restore the legacy database-scanning endpoint. |

## Administrator behavior

With the v0.10.2 default `BYPASS_ADMIN_ACCESS_CONTROL=True`, the ordinary list, search, and count endpoints return all users' files to an administrator. The content and metadata endpoints also allow administrators to read any file.

Studio therefore applies a stricter invariant:

1. obtain the current OWUI user ID from the authenticated Studio session;
2. retain a file summary only when its OWUI `user_id` equals that user ID;
3. before preview or download, fetch current metadata and repeat the ownership check;
4. map a mismatch to the same `not_found` result as a missing file;
5. never send another user's summary to the browser, cache it, persist it, or include it in logs.

This can be implemented entirely in the Studio adapter and avoids an immediate OWUI patch. For an administrator, it may require scanning pages containing other users' records. If representative-library tests show that this is too costly, the only justified bridge candidate is an upstreamable `owned_only=true` option on list and search. Changing the deployment-wide admin bypass setting is not part of the Media design.

## Studio adapter extension

The existing adapter already normalises paginated file summaries through `listFiles(page)`. Extend it rather than creating a Media client.

### Browser-facing summary

```ts
type StudioMediaType = 'image' | 'video' | 'audio';

interface StudioMediaSummary {
  id: string;
  filename: string;
  mediaType: StudioMediaType;
  contentType: string | null;
  size: number | null;
  createdAt: number;
  updatedAt: number | null;
}
```

OWUI `user_id` is validated server-side but is not included in the browser-facing type. Classify from a valid `content_type` first and use a conservative extension fallback for known image, video, and audio formats. Unknown and conflicting types are excluded. SVG is excluded from the initial preview surface because active SVG content must not be served from Studio's authenticated origin.

### Required adapter operations

- `listMedia(cursor)`: scan bounded OWUI file pages, enforce ownership, filter media, and return an opaque continuation cursor rather than exposing assumptions about OWUI page size.
- `searchMedia(query, cursor)`: perform bounded filename search, enforce ownership and media type, and normalise upstream `404` to an empty result.
- `getOwnedMedia(id)`: fetch current metadata and fail closed unless `user_id` matches the current user.
- `openMediaContent(id, disposition, range?)`: call `getOwnedMedia` first, then proxy preview or download content with an operation-specific deadline and cancellation.

The generic JSON request helper currently assumes every successful response is JSON. Content proxying needs a separate streaming response path; binary bodies must never pass through JSON parsing or application logs.

### Studio server routes

Expose same-origin Studio routes for browser use, for example:

- `GET /studio/api/media`;
- `GET /studio/api/media/search`;
- `GET /studio/api/media/{id}/content`;
- `GET /studio/api/media/{id}/download`.

These are Studio routes, not OWUI bridge endpoints. They retrieve the current server-side session, call the typed adapter, and never expose an OWUI token. Forward only required range request headers and allowlist response headers such as content type, content length, content range, accept-ranges, ETag, last-modified, and a sanitised content disposition.

## First-release presentation behavior

- Default to newest first using OWUI list order; filename search is server-backed.
- Offer image, video, and audio filters.
- Load results incrementally with an opaque cursor and bounded prefetch.
- Lazy-load preview content only when a card enters the preview path.
- Cancel superseded search, pagination, and preview requests.
- Use native image, video, and audio elements; exclude SVG and do not generate thumbnails or waveforms in the initial Media slice.
- Show stable empty, loading, not-found, permission-denied, unsupported-media, and upstream-unavailable states without revealing hidden metadata.
- Provide download but no upload, selection/delete, generation, processing, chat grouping, prompt recovery, or timeline launch.

## Contract tests required before UI implementation

1. Paginated mixed file types return only owned image/video/audio summaries.
2. Ordinary users with disjoint files cannot discover each other's IDs or metadata.
3. An administrator receives only their own summaries despite upstream admin bypass behavior.
4. Direct preview/download with another user's ID returns `not_found`, including for an administrator.
5. Search escapes and bounds input, filters non-media results, paginates, and maps upstream no-match `404` to an empty result.
6. Missing or malformed content type, size, timestamp, and metadata fail or normalise as specified.
7. Preview and download proxy content without exposing tokens and forward only allowlisted headers.
8. Video/audio range requests and cancellation work against pinned v0.10.2.
9. Deleted files and files deleted between listing and preview fail safely.
10. `401`, hidden `404`, `429`, timeout, malformed response, and `5xx` use the existing stable error mapping.
11. Representative large libraries demonstrate bounded memory, request concurrency, and acceptable admin self-filter performance.

## Bridge endpoint decision

No OWUI bridge endpoint is justified for the initial implementation. The upstream APIs cover listing, search, metadata, preview, and download. Revisit only the narrow `owned_only=true` list/search option if tests prove the administrator scan is an operational problem; do not restore `/files/media-overview`.

## Implementation evidence

Studio commit `5b5bb4e` adds the normalized Media types, bounded opaque-cursor listing and search, administrator self-ownership filtering, ownership-checked preview/download streaming, range forwarding, header allowlisting, MIME hardening, SVG exclusion, and deterministic contract fixtures. Eleven focused adapter tests pass as part of the 21-test Studio server suite; Svelte check and changed-file ESLint also pass.

Studio commit `08a332f` preserves the `better-sqlite3` native binding in the production image and makes Docker health validate the real Studio page rather than only the configuration-independent liveness endpoint. Image `open-webui-studio:media-adapter-08a332f` was smoke-tested as a non-root container; `/studio/`, `/studio/health`, OWUI reachability, OIDC discovery, and the Keycloak login redirect passed before the Media UI image replaced it.

Studio commit `278be05` adds `/studio/media`, Welcome/Agents navigation, authenticated self-owned content proxying, filename search, opaque-cursor pagination, responsive media cards, lazy image loading, image/video/audio preview, download, and explicit authentication, empty, denied, and upstream-unavailable states. Thirteen focused adapter/page-service tests pass as part of the 23-test server suite; changed-file ESLint, zero-warning Svelte check, production build, container health, Media route, unauthenticated content denial, OWUI reachability, and OIDC reachability pass. The user manually verified the authenticated Media page, previews, and downloads; representative-library performance checks remain.
