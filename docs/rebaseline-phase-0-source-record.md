# Rebaseline Phase 0 source record

Recorded on 2026-07-11 from the local repository. This is source-control evidence only; it does not identify the commit or image currently running in production.

## Repository state

| Item | Recorded value |
| --- | --- |
| Local branch | `main` |
| Local and `origin/main` commit | `7f562ebb5c0893a886adc02521251fce7b725cb2` |
| Declared application version | `0.6.36` in `package.json` |
| `origin` | `https://git.theoldschool.house/robert/open-webui` |
| Preserved rebaseline reference | `origin/rebaseline/kohai-upstream-v0.9.4` |
| Upstream remote | `https://github.com/open-webui/open-webui.git` (added during Phase 2) |
| Matching local legacy/rebaseline tags | Upstream release tags are now fetched; legacy preservation refs remain to be created |

The repository status at capture time contained one untracked planning document: `docs/OWUI_V0102_REBASELINE_AND_STUDIO_PLAN.md`. No claim is made that the working tree corresponds exactly to production until the deployed SHA is independently recorded.

## `functions_tools`

- Git submodule path: `functions_tools`
- Legacy source: `https://github.com/kohai-io/open-webui-functions-tools.git`
- Canonical maintained source: `https://git.theoldschool.house/robert/open-webui-functions-tools.git`
- Legacy pinned tree entry: `15a73d36764ab82522326ee3ca0f99fe15504731`
- Maintained v0.10.2 compatibility revision: `196b1a4` on `codex/v0102-file-api-compat`
- The root Docker build context copies the repository before the frontend build. The production deployment must still be checked to establish whether it builds this checkout, uses a prebuilt image, or deploys the submodule separately.

## Deployment material present in source

- Root image definition: `Dockerfile`
- Primary Compose definition: `docker-compose.yaml`
- Compose overlays: `docker-compose.api.yaml`, `docker-compose.data.yaml`, `docker-compose.gpu.yaml`, `docker-compose.amdgpu.yaml`, `docker-compose.a1111-test.yaml`, `docker-compose.otel.yaml`, and `docker-compose.playwright.yaml`
- Kubernetes manifests: `kubernetes/manifest`
- Configuration-name template: `.env.example`
- Compose volumes declared by the primary file: `ollama` and `open-webui`
- Default image references declared by the primary file: `ollama/ollama:${OLLAMA_DOCKER_TAG-latest}` and `ghcr.io/open-webui/open-webui:${WEBUI_DOCKER_TAG-main}`

These files are candidates, not proof of the live topology. The running Compose files, proxy configuration, image digest, volume bindings, environment-variable names, and external services must be captured from the deployment host without recording secret values.

## Required operator evidence

Phase 0 remains blocked on evidence outside this checkout:

1. Deployed commit, immutable image reference, and image digest.
2. Live Compose/project configuration and reverse-proxy routes.
3. Actual volumes, database engine, object/file storage, vector storage, caches, certificates, and external dependencies.
4. Fresh deployment bootstrap steps and routing-based rollback timing.
5. Confirmation of how `functions_tools` is built and deployed.
