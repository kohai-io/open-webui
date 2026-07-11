# Maintainable Welcome feature options

## Recommendation

Implement Welcome as a thin, feature-flagged UI island in the Open WebUI fork, while keeping Media and other independently evolving applications in Studio.

OWUI already owns everything Welcome presents: executable models, workspace model definitions, functions/pipes, permissions, and chat initialisation. Keeping this page beside those capabilities avoids inventing a second agent domain and gives users direct access to OWUI's Workspace management UI.

The feature branch should remain rebased on an exact upstream tag and contain no database schema or backend ownership changes. Its catalogue should use the same user-scoped APIs as the legacy page:

- `GET /api/models` for the current user's executable catalogue;
- `GET /api/v1/models/list` for accessible workspace-model metadata;
- `GET /api/v1/functions/` for active function/pipe identifiers;
- OWUI's native `/?models=<id>` route to initialise a chat.

An item is presented as an agent only when its executable ID is also an active workspace model with a `base_model_id`, or an active function. The `/api/models` intersection remains the final access-control boundary.

## Options

### 1. Thin OWUI feature branch (recommended)

Add an isolated Welcome component and one feature-flagged route/navigation seam. Link creation and editing to `/workspace/models`; reuse upstream stores and API clients rather than copying them.

This gives the best user experience and preserves OWUI semantics. The maintenance cost is a small Svelte patch that must be rebased and browser-tested for each upstream release.

### 2. Studio companion page

Keep the current Studio catalogue as a compatibility implementation. It uses server-side OIDC and typed OWUI adapters, and does not own agent definitions. This has near-zero OWUI merge cost, but duplicates catalogue presentation and makes the OWUI-to-Studio-to-OWUI journey more visible.

Studio remains the better boundary for Media, timelines, flows, and other features with their own data model and release cadence.

### 3. Build-time patch overlay

Store the isolated Welcome changes as a versioned patch applied to an unmodified upstream checkout during the image build. This makes the delta explicit and proves whether it still applies, but patch conflicts are less pleasant to review than a normal feature branch. Use this only if repository policy requires a pristine upstream branch.

### 4. Upstream contribution

Shape the thin implementation as an optional upstream Welcome/dashboard contribution. This offers the lowest long-term fork cost if accepted, but product fit and review timing are external dependencies. Keep the fork implementation independently releasable meanwhile.

## Maintenance rules

- Keep upstream history intact; rebase the feature branch onto each selected release tag.
- Keep the hook small: one flag, one route or home-page selection, and isolated components/tests.
- Do not add a second agent table, permission model, token store, or chat creation protocol.
- Treat OWUI's filtered `/api/models` result as authoritative before displaying or launching anything.
- Add contract tests for the three API shapes and a browser test covering workspace-agent launch.
- Record upstream API or route changes in the rebaseline plan before adapting the feature.
- If the patch grows into independent schemas or workflows, move that part to Studio instead.

