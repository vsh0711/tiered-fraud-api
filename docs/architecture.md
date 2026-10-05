# Architecture

## System overview

Tiered Fraud Scoring Platform routes each payment through the cheapest model depth that still meets a latency budget, then persists the decision for ops review.

![Architecture diagram](architecture-diagram.svg)

```mermaid
flowchart TB
  subgraph clients [Clients]
    browser[Ops_Console_Nextjs]
    scripts[API_Clients_curl_scripts]
  end

  subgraph edge [Public_edge]
    web[web_service]
    api[api_FastAPI]
  end

  subgraph data [Data_plane]
    pg[(PostgreSQL)]
    redis[(Redis)]
  end

  subgraph async [Async]
    worker[worker_process]
  end

  subgraph ml [Scoring_core]
    t0[T0_rules]
    t1[T1_fast_ML]
    t2[T2_full_ML]
    orr[OR_router_cascade]
  end

  browser --> web
  browser --> api
  scripts --> api
  web -->|NEXT_PUBLIC_API_BASE| api
  api --> pg
  api --> redis
  api --> orr
  orr --> t0 --> t1 --> t2
  worker --> pg
  worker --> redis
```

## Request path (score)

1. Client sends `POST /v1/score` with `X-API-Key` and optional `X-Routing-Mode`.
2. Auth + rate-limit middleware run (Redis sliding window when available).
3. OR router plans tier depth under `deadline_ms`.
4. Tiers execute (T0 → T1 → T2); optimized mode may early-exit.
5. Decision thresholds map score → `approve` / `review` / `decline`.
6. Event is written to `score_events` in Postgres and returned with `event_id`.

## Routing modes

| Mode | Behavior |
|------|----------|
| `baseline` | Always run T0→T1→T2 |
| `optimized` | Knapsack-style depth plan + cascade early exit |

## Async jobs

- Dashboard/API enqueues `batch_score` or `drift_scan` onto Redis list `fraud:jobs`.
- Worker BRPOPs jobs, updates `jobs` table, and writes scores / drift snapshots.

## Auth

- Dashboard: register/login JWT (`/v1/auth/*`), forgot-password reset tokens emailed or logged.
- Scoring: hashed API keys (`X-API-Key`).

## Deploy topology (Render)

| Service | Role | Public |
|---------|------|--------|
| Postgres | Persistence | No |
| Redis (Key Value) | Queue + rate limit | No |
| api | FastAPI + migrations | Yes |
| web | Next.js Ops Console | Yes |
| worker | Job consumer (optional, paid) | No |

See [deploy-render.md](deploy-render.md) for setup steps.
