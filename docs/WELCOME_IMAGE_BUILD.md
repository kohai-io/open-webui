# OWUI image build and Welcome customisation

## Source baseline

The maintained OWUI image comes from branch `rebaseline/upstream-v0.10.2`. The branch starts at upstream Open WebUI `v0.10.2` (`ecd48e2f7`) and applies the Welcome patch series listed in [`PATCHES.md`](../PATCHES.md).

Do not build this image from the legacy `main` branch.

## How the Welcome page enters the image

The repository contains the Welcome page as a native Svelte component. Docker does not apply an overlay or copy a separate theme at runtime.

1. `Dockerfile` copies the patched repository into the Node build stage.
2. `npm run build` compiles `Welcome.svelte` into the frontend bundle.
3. The final Python image receives that compiled bundle from `/app/build`.
4. `ENABLE_WELCOME_PAGE` controls which root-page component OWUI renders at runtime.

The backend reads `ENABLE_WELCOME_PAGE` in `backend/open_webui/config.py` and returns it from `/api/config` as `features.enable_welcome_page`. The frontend route `src/routes/(app)/+page.svelte` renders Welcome only for `/` with no query parameters. New Chat and other query-based links continue to render the upstream Chat component.

The build imports Welcome at compile time, so the image contains its code even when the feature flag is off.

## Build requirements

Build from a clean checkout of the maintained branch and record the source revision. The production image runs as UID/GID `1000:1000`:

```powershell
git switch rebaseline/upstream-v0.10.2
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

The customised `.github/workflows/docker.yaml` triggers for the maintained branch, passes UID/GID `1000:1000`, and checks the runtime user after each image build. Preserve these safeguards when rebasing the workflow from upstream.

## Enable and roll back

Set the runtime environment variable:

```text
ENABLE_WELCOME_PAGE=True
```

Set it to `False` to restore the upstream root Chat page. The flag changes presentation only; rollback requires no database migration.

## Release checks

- Confirm the checkout is clean and based on the intended upstream tag.
- Run the focused Welcome Vitest tests and a production frontend build.
- Verify the image revision label and runtime user.
- Test `/`, New Chat, agent/model visibility, prompt handoff, and attachments.
- Deploy the verified image digest and retain the build evidence.
