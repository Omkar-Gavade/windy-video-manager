# Docker Deployment — Windy Video & Input Manager

Two containers, one Compose file:

- **windy-backend** — FastAPI + boto3 (`:8000`)
- **windy-frontend** — React build served by nginx (`:80`), which also reverse-
  proxies `/api/*` to the backend (same-origin → no hardcoded backend URL, no CORS).

## Architecture

```
React SPA (Videos + Inputs, React Router)
        │  Axios, same-origin /api/*
        ▼
nginx (static + reverse proxy)
        │  Docker network → windy-backend:8000
        ▼
FastAPI (boto3) ── presigned URLs / metadata JSON ──▶ AWS S3 (private)
```

- **Videos** — upload (deterministic `<plant>_YYMMDD_HH_MM.mp4` + JSON sidecar), list, filter, preview, download.
- **Inputs** — categorized uploads (`Site_Details`, `Enercast_Data`, `Metered_Data`, `WP/Images`, `WP/Videos`, `fetch_manifest.json`), list, filter, preview (JSON/CSV/TXT/image/PDF), download.
- **Dynamic State/Plant** — discovered from S3 folders (no hardcoded values) for both modules.

## Docker architecture / container diagram

```
┌──────────────────────── Docker Compose network: windy ────────────────────────┐
│                                                                                │
│   ┌─────────────────────────┐        ┌──────────────────────────────────┐     │
│   │  windy-frontend          │        │  windy-backend                    │     │
│   │  nginx:alpine  :80        │  /api  │  python:3.12-slim  :8000          │     │
│   │  - serves React dist      │──────▶ │  - uvicorn (2 workers, non-root)  │     │
│   │  - SPA fallback           │  proxy │  - HEALTHCHECK /health            │     │
│   │  - HEALTHCHECK (wget /)   │        │  - boto3 → AWS S3                 │     │
│   └─────────────┬───────────-─┘        └──────────────┬───────────────────┘     │
│                 │ 80:80                                │ 8000:8000               │
└─────────────────┼─────────────────────────────────────┼───────────────────────┘
        Browser ──┘                          (optional direct API) ──┘
                                                            │
                                                            ▼  IAM role / keys
                                                        AWS S3 (private bucket)
```

## Project structure

```
.
├── docker-compose.yml          # orchestrates both services
├── DEPLOY_DOCKER.md
├── backend/
│   ├── Dockerfile              # python:3.12-slim, non-root, HEALTHCHECK /health
│   ├── .dockerignore
│   ├── .env.example            # copy -> .env and fill in
│   ├── requirements.txt
│   └── app/
├── frontend/
│   ├── Dockerfile              # multi-stage: node:20-alpine build -> nginx:alpine
│   ├── nginx.conf              # SPA fallback + /api proxy
│   ├── .dockerignore
│   ├── .env.example
│   └── src/
```

## Port mapping

| Service | Container | Host | Purpose |
| --- | --- | --- | --- |
| windy-frontend | 80 | 80 | Public app entry (nginx) |
| windy-backend | 8000 | 8000 | API (optional to expose; nginx already proxies `/api`) |

## Environment variables

### Backend — `backend/.env` (loaded by Compose `env_file`)

| Variable | Required | Notes |
| --- | --- | --- |
| `AWS_REGION` | ✅ | Must match the bucket region |
| `S3_BUCKET` | ✅ | Target bucket name |
| `S3_PREFIX` | – | Videos prefix (default `videos/`) |
| `INPUTS_PREFIX` | – | Inputs prefix (default `inputs/`) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | ⚠️ | Local/dev only — **use an IAM role in prod and omit** |
| `MAX_UPLOAD_MB` | – | Default 200 |
| `ALLOWED_VIDEO_MIME` | – | Video upload allowlist |
| `ALLOWED_DATA_EXTENSIONS` / `ALLOWED_INPUT_VIDEO_EXTENSIONS` / `ALLOWED_INPUT_IMAGE_EXTENSIONS` | – | Inputs allowlists |
| `PREVIEW_EXPIRY_SECONDS` / `DOWNLOAD_EXPIRY_SECONDS` | – | Presigned URL lifetimes |
| `ALLOWED_ORIGINS` | – | Only relevant if the API is called cross-origin |

> The backend starts even without AWS credentials — `/health` stays 200; only
> S3 operations fail (HTTP 502). `AWS_REGION` and `S3_BUCKET` are still required.

### Frontend — build-time only

`VITE_API_BASE_URL` is baked at build time; Compose sets it to `/` so the app
calls the same origin and nginx proxies `/api`. **`frontend/.env` is not needed
for the Docker deployment** (it only matters for `npm run dev` outside Docker).

## API surface (proxied at `/api/*`)

```
GET  /health
GET  /api/videos            POST /api/videos/upload
GET  /api/videos/preview    GET  /api/videos/download
GET  /api/videos/states     GET  /api/videos/plants?state=
GET  /api/inputs            POST /api/inputs/upload
GET  /api/inputs/preview    GET  /api/inputs/download
GET  /api/inputs/states     GET  /api/inputs/plants?state=
GET  /api/inputs/content?key=
```

## Deploy

```bash
docker compose build
docker compose up -d
```

- Backend becomes **healthy** (HEALTHCHECK `/health`), then the frontend starts
  (`depends_on: service_healthy`). Open **http://localhost/** (or `http://<EC2_IP>/`).

## Logs

```bash
docker compose logs -f                 # both
docker compose logs -f windy-backend
docker compose logs -f windy-frontend
```

## Health check

```bash
docker compose ps                                   # STATUS shows (healthy)
curl http://localhost:8000/health                   # {"success":true,...}
curl -o /dev/null -w "%{http_code}\n" http://localhost/inputs   # 200 (SPA)
curl http://localhost/api/videos/states             # via nginx proxy → backend
```

## Restart / Update / Stop / Cleanup

```bash
# Restart
docker compose restart                 # both
docker compose restart windy-backend

# Update after code changes
git pull
docker compose build
docker compose up -d                   # recreates changed containers

# Stop
docker compose down                    # stop + remove containers (keeps images)

# Cleanup (also remove images + build cache)
docker compose down --rmi local
docker builder prune -f
```

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `env file ./backend/.env not found` | `cp backend/.env.example backend/.env` then fill values |
| Port 80 / 8000 in use | Stop the conflicting service, or change the published port (`8080:80`) |
| `/api/*` returns 502 | Backend can't reach S3 — bad/missing AWS creds, wrong region, or bucket. `docker compose logs windy-backend` |
| Refresh on `/videos` or `/inputs` 404s | nginx `try_files … /index.html` handles it — rebuild the frontend image |
| Dynamic State/Plant empty | The bucket has no `videos/<State>/` or `inputs/<State>/` folders yet — upload something first |
| Presigned preview/download 403 | Bucket region mismatch — backend already pins regional virtual-hosted addressing; confirm `AWS_REGION` matches the bucket |
| Frontend never starts | Backend not healthy yet — check `docker compose ps` / backend logs |

## EC2 deployment (fresh Ubuntu)

```bash
# 1. Install Docker + Compose plugin
sudo apt-get update && sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER   # re-login for this to take effect

# 2. Get the project and configure
git clone <repo-url> windy && cd windy
cp backend/.env.example backend/.env    # set AWS_REGION, S3_BUCKET, (IAM role in prod)
# frontend/.env is NOT required for Docker.

# 3. Build + run
docker compose build
docker compose up -d
docker compose ps
```

**Security group**: open inbound **80** (frontend). Port **8000** can stay private
(the frontend proxies `/api`). Put an ALB/TLS terminator in front for HTTPS.

**Production hardening**

- Attach an **IAM role** to the instance; remove static AWS keys from `.env`.
- Terminate **HTTPS** at an ALB or a TLS reverse proxy.
- Least-privilege S3 policy: `s3:ListBucket` (prefix-scoped), `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject` (video sidecar rollback) on the bucket only.
