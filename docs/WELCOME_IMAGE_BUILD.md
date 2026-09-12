# OWUI image build and Welcome customisation

## Source baseline

The production OWUI image comes from `main`. The maintained baseline is upstream Open WebUI `v0.11.3` (`2a960a5`), with the Welcome and Media patches listed in [`PATCHES.md`](../PATCHES.md).

Use `main` for maintained development and production releases. For the next upstream upgrade, create a short-lived branch from the selected upstream release tag and follow the rebase procedure in `PATCHES.md` before promotion to `main`. The previous customised fork remains frozen at `legacy/v0.6.36-custom`; `archive/pre-v0102-transition` and `archive/rebaseline-v0.9.4` preserve historical transition work.

## How the Welcome page enters the image

The repository contains the Welcome page as a native Svelte component. Docker does not apply an overlay or copy a separate theme at runtime.

1. `Dockerfile` copies the patched repository into the Node build stage.
2. `npm run build` compiles `Welcome.svelte` into the frontend bundle.
3. The final Python image receives that compiled bundle from `/app/build`.
4. `ENABLE_WELCOME_PAGE` enables `/welcome`, its sidebar Home link, and the default sign-in landing destination.

The backend reads `ENABLE_WELCOME_PAGE` in `backend/open_webui/config.py` and returns it from `/api/config` as `features.enable_welcome_page`. The thin route `src/routes/(app)/(custom)/welcome/+page.svelte` renders `<Chat welcome />` at `/welcome`. Chat's Placeholder supplies the native MessageInput to `src/lib/components/custom/welcome/Welcome.svelte`: below the greeting on desktop, and at the bottom of the screen on mobile with content scrolling above it. Model selection, uploads, voice, and sending use Chat's existing state and handlers. After the first message, Chat shows the ordinary conversation view. Route groups in parentheses do not appear in the URL.

`src/routes/(app)/+page.svelte` remains identical to upstream: `/` always renders Chat, with existing model, prompt, tool and voice query parameters unchanged. Sign-in without a destination opens `/welcome` when enabled; explicit redirects, including `/`, remain authoritative. The sidebar Home link opens Welcome and New Chat opens `/`.

The build imports Welcome at compile time, so the image contains its code even when the feature flag is off.

## Build requirements

Build from a clean checkout of `main` and record the source revision. The production image runs as UID/GID `1000:1000`:

```powershell
git switch main
git status --short
$revision = git rev-parse HEAD

docker build --platform linux/amd64 `
  --build-arg BUILD_HASH=$revision `
  --build-arg UID=1000 `
  --build-arg GID=1000 `
  --label "org.opencontainers.image.revision=$revision" `
  --tag <registry>/<owner>/open-webui:<tag> `
  .
```

Push and deploy an immutable image digest. Record the source revision, image digest, platform, UID/GID, base-image digests, and build command in the release evidence.

GitHub Actions runs frontend build and test checks and Python checks. This fork has no GitHub Actions workflows for Docker image publishing, GitHub releases, or PyPI publishing. Build images explicitly using the command above, verify the revision label and runtime user, and publish to the selected registry as a separate release action.

## Enable and roll back

Set the runtime environment variable:

```text
ENABLE_WELCOME_PAGE=True
```

Set it to `False` to hide the Home link and use `/` as the default sign-in destination. Requests to `/welcome` then redirect to `/` with history replacement. The root route always renders Chat regardless of this flag. The flag changes presentation only; rollback requires no database migration.

## Release checks

- Confirm the checkout is clean and based on the intended upstream tag.
- Run the focused Welcome Vitest tests and a production frontend build.
- Verify the image revision label and runtime user.
- Test `/welcome` and `/` with the flag enabled and disabled; verify default sign-in and explicit return destinations.
- Test sidebar Home and New Chat on desktop and mobile, temporary chat, desktop query/call events, agent/model visibility, prompt handoff, and attachments.
- Deploy the verified image digest and retain the build evidence.
