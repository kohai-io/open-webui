# Maintained Open WebUI patch series

This branch starts from upstream Open WebUI `v0.10.2` at `ecd48e2f7`. Retained changes must remain small enough to review and reapply independently on the next selected upstream release.

## Native Welcome page

### Purpose

Provide the fork's user landing experience beside the OWUI-owned concepts it presents: workspace models, functions/pipes, tools, files, voice features, and chat initialisation.

### Commits

- `559cd28f1` — add the disabled-by-default feature seam and OWUI catalogue classification.
- `e9ca2fc11` — restore the full legacy Welcome experience and adapt it to v0.10.2 APIs.
- `3ccdbe83c` — harden ordering, composer handoff, and ordinary-file upload behavior.
- `da39eb4a1` — keep sidebar New Chat navigation separate from the parameter-free Welcome route.

### Configuration

Set `ENABLE_WELCOME_PAGE=True` to replace the parameter-free `/` chat landing page. The default is `False`, which preserves upstream behavior. Any query parameter routes to the upstream Chat component, including model, prompt, tool, voice, and quick-action handoffs.

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
- `src/routes/(app)/+page.svelte`
- `src/lib/components/welcome/*`
- A narrow Welcome attachment restore block in `src/lib/components/chat/Chat.svelte`
- Sidebar route adjustments in `src/lib/components/layout/Sidebar.svelte`

### Verification

- Focused Vitest coverage for access-aware classification, ordering, and composer query handoff.
- Full Vite production build.
- Manual checks: agent/model visibility, prompt submission, integrations, file/image attachment, dictation, voice mode, ordering persistence, quick actions, sidebar New Chat and Welcome navigation, and mobile layout.

### Rebase procedure

1. Create a short-lived branch from the next tested upstream release tag.
2. Reapply this series in order.
3. Confirm the three OWUI API contracts and Chat query parameters have not changed.
4. Run focused tests and a production build.
5. Run the manual checks against representative users and groups.
6. Remove any part superseded by upstream before merging.

### Removal and rollback

Set `ENABLE_WELCOME_PAGE=False` or deploy an unpatched upstream image. No database rollback or data conversion is required.
