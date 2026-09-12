# Maintained Open WebUI patch series

This branch starts from upstream Open WebUI `v0.11.3` at `2a960a5`. Retained changes must remain small enough to review and reapply independently on the next selected upstream release.

See [`docs/WELCOME_IMAGE_BUILD.md`](docs/WELCOME_IMAGE_BUILD.md) for the image build path, runtime flag, and release requirements.

The v0.11.3 port retains upstream's logout/SSO handling and revised sidebar. Welcome uses the upstream user menu without the removed `showArchivedChats` store or obsolete archive event handler. The `/welcome` and `/media` routes do not collide with upstream's `/home` route. Upgrading from v0.10.2 requires a database backup; reverting only the image after migration is insufficient.

## Native Welcome page

### Purpose

Provide the fork's user landing experience beside the OWUI-owned concepts it presents: workspace models, functions/pipes, tools, files, voice features, and chat initialisation.

### Commits

- `559cd28f1` — add the disabled-by-default feature seam and OWUI catalogue classification.
- `e9ca2fc11` — restore the full legacy Welcome experience and adapt it to v0.10.2 APIs.
- `3ccdbe83c` — harden ordering, composer handoff, and ordinary-file upload behavior.
- `da39eb4a1` — keep sidebar New Chat navigation separate from the parameter-free Welcome route.
- `31f35d817` — wait for pending file operations and harden composer handoff.
- `445258a39` — synchronise Welcome translation keys across locales.
- `ba387521a` — load agent icons from the model profile-image endpoint.

The maintained implementation now uses `/welcome`, under `src/routes/(app)/(custom)/welcome/`, and `src/lib/components/custom/welcome/`. This supersedes the root-route switch and sidebar URL rewrites in the historical commits above. Use the current patch surface when porting the feature; replaying only the initial four commits is insufficient.

### Configuration

Set `ENABLE_WELCOME_PAGE=True` to enable `/welcome`, the sidebar Home link, and Welcome as the default sign-in destination. Explicit sign-in redirects take precedence, including `/` and chat, model, tool and prompt links. The default is `False`; when disabled, `/welcome` redirects to `/` with history replacement and the Home link is hidden.

`/` always renders the upstream Chat component. Existing chat query parameters remain unchanged. `(app)` and `(custom)` are source route groups and do not appear in public URLs. Visiting `/` directly, including signing in to return to an explicitly requested `/`, opens Chat.

### Ownership and boundaries

- `/api/models` remains the authoritative executable, user-filtered catalogue.
- `/api/v1/models/list` supplies accessible workspace-model metadata and is paginated.
- `/api/v1/functions/` supplies active function/pipe identifiers.
- Agent definitions, prompts, knowledge, skills, tools, grants, files, and chats remain OWUI-owned.
- Agent presentation order is a browser-local preference under `welcome-agent-order`; it is not an agent record or access-control mechanism.
- Ordinary files are uploaded through OWUI's Files API before Chat handoff. Image and screen captures retain the existing data-URL handoff behavior.

### Patch surface

- `backend/open_webui/config.py`
- `backend/open_webui/main.py`
- `src/lib/stores/index.ts`
- `src/routes/(app)/(custom)/welcome/+page.svelte`
- `src/routes/auth/+page.svelte` (default destination only)
- `src/lib/components/custom/welcome/*`
- A narrow Welcome attachment restore block in `src/lib/components/chat/Chat.svelte`
- A CustomLinks import and two insertions in `src/lib/components/layout/Sidebar.svelte`; the custom component includes WelcomeLink
- Welcome strings in `src/lib/i18n/locales/*/translation.json`

Keep the root route identical to upstream. Keep fork-owned components, helpers and tests together under `custom/`, with route entry points under `(custom)/`. These directories identify ownership; imports of upstream menus and the attachment handoff still require compatibility checks.

### Verification

- Focused Vitest coverage for access-aware classification, ordering, and composer query handoff.
- Full Vite production build.
- Navigation checks with the flag on and off: `/welcome`, `/`, default sign-in, explicit sign-in redirects, sidebar Home and New Chat (expanded/collapsed/mobile), temporary chat, and desktop query/call events.
- Manual checks: agent/model visibility, prompt submission, integrations, file/image attachment, dictation, voice mode, ordering persistence, quick actions, and mobile layout.

The reusable Cypress navigation checks live at `src/lib/components/custom/welcome/navigation.cy.js`. Run against a disposable local instance with an existing test account. Set `CYPRESS_WELCOME_TEST_EMAIL` and `CYPRESS_WELCOME_TEST_PASSWORD` in the environment, then run:

```sh
npx cypress run --e2e --config-file src/lib/components/custom/welcome/cypress.config.js
```

The default test URL is `http://127.0.0.1:18765`; set `CYPRESS_BASE_URL` to override it. The checks override the browser's feature-flag response to exercise both settings. They cover default and explicit sign-in destinations, root Chat navigation, and desktop/mobile sidebar links without making model calls.

### Rebase procedure

1. Create a short-lived branch from the next tested upstream release tag.
2. Port the complete maintained patch surface, including follow-up fixes and the dedicated Welcome route; do not restore the superseded root-route switch.
3. Confirm the three OWUI API contracts, imported menu interfaces, authentication redirects and Chat query parameters have not changed.
4. Run focused tests and a production build.
5. Run the manual checks against representative users and groups.
6. Remove any part superseded by upstream before merging.

### Removal and rollback

Set `ENABLE_WELCOME_PAGE=False` or deploy an unpatched upstream image. No database rollback or data conversion is required.

## Media gallery: phase one

`/media` is a thin route under `src/routes/(app)/(custom)/media/`. Its implementation,
Files API adapter and focused tests live under `src/lib/components/custom/media/`.
`custom/navigation/CustomLinks.svelte` provides the shared sidebar integration for
Welcome and Media, in both expanded and collapsed navigation.

Media is available to signed-in, approved users independently of `ENABLE_WELCOME_PAGE`.
This phase adds no backend endpoint, environment setting, database migration or Chat
change. It reuses the existing paginated `/api/v1/files/?page=N&content=false` endpoint,
file content URLs and file deletion API. Listing follows upstream access rules:
administrators may see other users' files when `BYPASS_ADMIN_ACCESS_CONTROL` allows it.

The gallery supports image/video/audio filtering, filename search, previews, downloads
and confirmed single-file deletion. Search and filters apply only to loaded files.
Each Load more action fetches one upstream page (currently 50 files, including non-media
files); no automatic full-library scan occurs. After deletion, pagination restarts to
avoid skipping files as upstream offsets shift. Video/audio load only in the preview.

Chat/folder grouping, orphan classification, prompt extraction, bulk deletion, timeline
editing, sorting across the whole library and Chat attachment handoff are deferred.
The legacy `/workspace/media` URL is not restored. Feature-owned copy lives in `media/copy.ts`
and uses the `customMedia` i18next namespace with English defaults. Existing labels reuse
upstream translations. An extraction regression test ensures the custom components add no
keys to upstream locale dictionaries during the CI translation check.

Upgrade checks: confirm the Files response still has `items` and `total`, page numbering
and access rules; check content/download authentication, deletion, and imported modal
interfaces; check `/media` for an upstream route collision. Verify sidebar navigation
on desktop/mobile with Welcome enabled and disabled, empty/non-media pages, pagination
and retries, media previews and deletion on a disposable file. Run focused Media and
Welcome tests and a production frontend build. Remove the custom route/components and
restore the WelcomeLink sidebar insertions to remove this feature.

Run the focused tests with `npx vitest run --dir src/lib/components/custom`.
For the mocked browser checks, build the frontend, start `npx vite preview --host
127.0.0.1 --port 18766`, then run `npx cypress run --e2e --config-file
src/lib/components/custom/media/cypress.config.js`. These checks stub all API requests
and exercise only fake files; they need no credentials. They do not replace live
verification of server permissions or media streaming.

## Repository automation

Keep the frontend and Python validation workflows. The inherited Docker publishing, GitHub release, and PyPI publishing workflows are removed from this fork; do not restore them when updating the upstream baseline. Image publishing remains an explicit release action documented in [the build guide](docs/WELCOME_IMAGE_BUILD.md).
