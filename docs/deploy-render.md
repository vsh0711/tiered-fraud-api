# Deploy on Render

Blueprint file: [`render.yaml`](../render.yaml)

## Services

| Service | Type | Plan | Public URL |
|---------|------|------|------------|
| `tiered-fraud-api` | Web (Docker) | Free | `https://tiered-fraud-api.onrender.com` |
| `tiered-fraud-web` | Web (Docker) | Free | `https://tiered-fraud-web.onrender.com` |
| `tiered-fraud-db` | Postgres | Free | private |
| `tiered-fraud-redis` | Key Value (Redis) | Free | private |

Background **workers are not free** on Render. Batch/drift jobs need a paid Starter worker (same image, `python -m worker.main`). Scoring, auth, history, and holdout upload work without it.

## One-click Blueprint

1. Push this repo to GitHub (includes `render.yaml` + baked model artifacts under `data/models/`).
2. Open [Render Blueprints](https://dashboard.render.com/blueprints) → **New Blueprint Instance**.
3. Connect `vsh0711/tiered-fraud-api` (or your fork), branch `main`.
4. Apply the Blueprint and wait for first deploys (API build installs deps; models are copied from the repo).
5. Open the web URL → **Create account** → Playground.

## Env notes

- `DATABASE_URL` / `REDIS_URL` are wired by the Blueprint.
- `app/config.py` normalizes `postgres://` → `postgresql+asyncpg://`.
- API entrypoint runs `alembic upgrade head` then uvicorn on `$PORT`.
- No SMTP: password-reset links appear in **tiered-fraud-api** logs.
- Free web services **spin down after ~15 minutes idle** — first request may take ~1 minute.

## Optional worker (Starter)

1. New → Background Worker → Docker, same repo / Dockerfile as API.
2. Docker Command: `python -m worker.main`
3. Copy `DATABASE_URL`, `REDIS_URL`, `FRAUD_JWT_SECRET`, `FRAUD_DEMO_API_KEY` from the API service.

## Smoke test

```bash
curl -sS https://tiered-fraud-api.onrender.com/v1/health
open https://tiered-fraud-web.onrender.com
```
