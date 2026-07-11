# Local development environments

Use separate runtimes for the frontend and backend. Node and frontend packages do not belong in the Conda environment.

## Frontend: Node.js 22

The repository pins Node.js `22.17.0` in `.nvmrc`. Open WebUI supports Node.js 18.13 through 22, and the v0.10.2 baseline build was rehearsed with this Node 22 release.

With nvm-windows:

```powershell
nvm install 22.17.0
nvm use 22.17.0
node --version
npm --version
npm ci
npm run dev
```

`npm ci` must use the committed `package-lock.json`. Do not commit `node_modules` or substitute an automatically rewritten lockfile during the rebaseline.

## Backend: Conda with Python 3.11

The backend environment is defined in `environment.yml`. It intentionally installs only Python and pip through Conda; the authoritative application dependencies remain in `backend/requirements.txt`.

Create and populate the environment:

```powershell
conda env create -f environment.yml
conda activate open-webui-v0102-backend
python -m pip install -r backend/requirements.txt
```

If the environment already exists:

```powershell
conda env update -f environment.yml --prune
conda activate open-webui-v0102-backend
python -m pip install -r backend/requirements.txt
```

Run the backend with isolated local data:

```powershell
$env:DATA_DIR = Join-Path $PWD '.local-data'
$env:WEBUI_SECRET_KEY = '<local-development-secret>'
$env:OFFLINE_MODE = 'true'
Set-Location backend
python -m uvicorn open_webui.main:app --host 127.0.0.1 --port 8080 --workers 1
```

Use a real randomly generated local secret and do not commit it. `.local-data` should remain disposable and must not point at legacy or production storage.

## Verification

From separate terminals with the frontend and backend environments active:

```powershell
npm run check
npm run build
```

```powershell
python --version
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8080/health
```

The upstream v0.10.2 frontend production build currently passes while its type check has existing upstream diagnostics. Record those diagnostics; do not hide them by changing the pinned environment or baseline source.

## Deployment boundary

Conda and nvm are local-development conveniences. Staging and production should use immutable container images with recorded digests.
