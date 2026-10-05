# Tiered Fraud Scoring Platform

This project is about making fraud checks fast enough for payments without blindly running the heaviest model every time.

The pain point
In real payment/fraud systems you have a tradeoff:

- Catch fraud → needs deeper ML (more features, slower)
- Approve good customers quickly → needs low latency (often <100ms)
If you always run the full model stack on every transaction:

   1/ you burn latency and infra cost
   2/ most traffic is legitimate anyway
   3/ you overpay compute for easy “obviously safe” cases
If you only run a cheap rules check:

```
* you miss harder fraud
* false negatives go up
```

That tension is the core problem.

What this project does about it
It scores a transaction in tiers:

- T0 rules — cheap/fast first pass
- T1 fast ML — light model
- T2 full ML — expensive, more accurate
Then an OR (operations-research) router decides how deep to go under a latency budget, and can early-exit when the score is clearly safe or clearly fraud.

So instead of “always run everything,” it asks:

 What’s the smartest amount of model depth I can afford for this transaction?

Why baseline vs optimized matters

- Baseline: always T0→T1→T2 (safe but slow/expensive)
- Optimized: plan + cascade (usually faster, similar fraud catch)
The dashboard/holdout report is there to prove that claim with numbers: latency savings, decision mix, capture/recall.

**One-line version**
It’s a FinTech portfolio system that shows how to route fraud scoring under latency constraints so you don’t waste full-model cost on every payment.

Production-style **FinTech fraud scoring** portfolio project: calibrated ML tiers (T0 rules → T1 fast → T2 full), an **operations-research router** under a latency budget, Postgres persistence, Redis async jobs, JWT/API-key auth, and a dark **Ops Console** dashboard.

## Stack


| Layer        | Tech                                                  |
| ------------ | ----------------------------------------------------- |
| API          | FastAPI, Pydantic v2, Prometheus metrics              |
| ML / OR      | LightGBM, scikit-learn, cascade + knapsack router     |
| DB           | PostgreSQL, SQLAlchemy 2 (async), Alembic             |
| Cache / jobs | Redis worker (`batch_score`, `drift_scan`)            |
| Auth         | API keys (`X-API-Key`) + JWT dashboard login          |
| Frontend     | Next.js + TypeScript + Tailwind + Recharts            |
| Ops          | Docker Compose, GitHub Actions CI, `/ready` + `/live` |




## Quick start (Docker)

```bash
# ensure models exist (also auto-trained in compose)
export PATH="$HOME/.local/bin:$PATH"
uv sync --extra dev
uv run python scripts/train_models.py

docker compose up --build
```

- API: [http://127.0.0.1:8742/docs](http://127.0.0.1:8742/docs)  
- Web: [http://127.0.0.1:3000](http://127.0.0.1:3000) → **Create account**, then sign in  
- Forgot password emails use SMTP (`FRAUD_SMTP_*`); in local `development` without SMTP the reset link is logged by the API  
- Service API key (scripts): `tf_demo_key_change_me`

Seed history (optional, with stack running):

```bash
docker compose exec api python scripts/seed_demo.py
```



## Local (uv + Compose infra)

```bash
cp .env.example .env
docker compose up -d db redis
export PATH="$HOME/.local/bin:$PATH"
uv sync --extra dev
uv run alembic upgrade head
uv run python scripts/train_models.py
uv run uvicorn app.main:app --host 127.0.0.1 --port 8742 --reload
# other terminal
uv run python -m worker.main
# frontend
cd web && npm install && npm run dev
```



## API examples

```bash
curl -s http://127.0.0.1:8742/v1/health | jq

curl -s -X POST http://127.0.0.1:8742/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"vish","email":"you@example.com","password":"your-secure-password"}' | jq

curl -s -X POST http://127.0.0.1:8742/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"you@example.com","password":"your-secure-password"}' | jq

curl -s -X POST http://127.0.0.1:8742/v1/score/compare \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: tf_demo_key_change_me' \
  -d '{
    "request_id":"demo-1",
    "amount":420.50,
    "merchant_category":"electronics",
    "country":"US",
    "device_risk_score":0.15,
    "velocity_1h":1,
    "velocity_24h":3,
    "deadline_ms":100
  }' | jq
```



## Project layout

```
app/           FastAPI app (api/v1, core, db, services)
or_router/     OR planning + cascade pipeline
ml/            Features, training, inference
sim/           Synthetic transactions + drift
worker/        Redis job consumer
web/           Next.js ops console
alembic/       DB migrations
scripts/       Train, seed, benchmarks
tests/         Unit + smoke tests
```



## Routing modes

- `baseline` — always T0→T1→T2  
- `optimized` — latency-budget plan + adaptive cascade early exit



## License

MIT (portfolio use).