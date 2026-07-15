# OWUI Portainer stack on Docker VM 113

This bundle records an evaluated Portainer-managed Docker Standalone
alternative for VM `113`. It was not selected for the Phase 9 OWUI rehearsal.
The active deployment remains the dedicated unprivileged LXC `105`; do not
deploy this stack unless a later explicit topology decision reactivates it.

## Boundaries

- Stack name: `owui-staging`
- Container name: `owui-staging`
- Image:
  `git.theoldschool.house/robert/open-webui@sha256:012e5f80e9aaf508c5831fde9440a78fea3b7ff2f4b2a8ca451758e904e696c9`
- Runtime user: `1000:1000`
- Data path: `/srv/stacks/owui-staging/data`
- Container port: `8080`
- Host bind address and port: `10.100.1.144:8080`
- Public name: `owui-stage.theoldschool.house`
- Model gateway: LiteLLM service `litellm` on external Docker network `infra`
- Legacy rollback: LXC `106`, unchanged

The image digest is hard-coded. Do not replace it with `main`, `latest`, a
branch tag, or another mutable reference.

## Secret and configuration ownership

Portainer owns the stack variables for this topology. Define values
individually in Portainer or upload a temporary uncommitted `.env` file. The
Compose file references each OWUI variable explicitly using `${NAME}`
substitution, matching the existing homelab Portainer stack convention.

`OWUI_BIND_ADDRESS` and `OWUI_HOST_PORT` are used only to render the published
port. The remaining listed variables are explicitly passed to OWUI. The stack
does not use `stack.env` and therefore does not pass unrelated Portainer
variables into the container.

Use `owui-stack-env.names` as the value-free inventory. Do not paste values
into the Compose file, Git, Proxmox notes, logs, or chat. Restrict Portainer
administrator access and include Portainer's own data in the homelab backup
policy. Portainer administrators can manage stack variables.

## Host preparation

Copy `prepare-owui-host.sh` to VM `113`. After selecting an unused address and
port, run:

```text
chmod 0555 prepare-owui-host.sh
sudo ./prepare-owui-host.sh --bind-address <VM-address> --host-port <port> --check-only
sudo ./prepare-owui-host.sh --bind-address <VM-address> --host-port <port> --confirm
```

The command validates Docker Standalone, host architecture, the bind address,
port availability, local filesystem type, free space, and Gitea TLS/API. It
creates only `/srv/stacks/owui-staging/data` as `1000:1000` mode `0750`.

## Portainer deployment

1. Add `git.theoldschool.house` under Portainer registries using credentials
   authorized to pull the private image. Do not expose the credential.
2. Add a new stack named `owui-staging` using Upload or Web editor and
   `owui-stack.compose.yaml`.
3. Select the Gitea registry for the stack if the installed Portainer version
   exposes registry selection.
4. Define all required values from `owui-stack-env.names`. Set
   `OWUI_BIND_ADDRESS` and `OWUI_HOST_PORT` to the values validated by the host
   preparation command. Set `OPENAI_API_BASE_URL` to
   `http://litellm:4000/v1` and supply its credential through
   `OPENAI_API_KEY`.
5. Deploy the stack. Do not enable an automatic mutable-image updater.
6. Wait for container health `healthy` and test `/health` through the selected
   host address and port.
7. Configure Caddy only after the local health check passes.

Do not inspect or export the resolved container environment as evidence.

## Limitations before Phase 9 acceptance

- VM `113` resource usage, Docker/Portainer versions, storage filesystem,
  existing ports, and backup target still require capture.
- Stopped-service backup and paired image/data rollback tooling must be
  adapted to the shared Docker host before update rehearsal.
- A failure or maintenance event on VM `113` affects its other Docker stacks.
- OWUI and LiteLLM share the existing external `infra` Docker network; no
  LiteLLM host-port hop is required for model traffic.
- Studio placement remains a separate decision.
- LXC `105` must not be deleted until this topology passes and its preserved
  partial state is recorded.
