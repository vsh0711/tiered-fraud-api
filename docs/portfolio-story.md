# Portfolio story

## One-liner

A production-style FinTech fraud platform that spends model depth only when a transaction needs it — proving latency savings without giving up operational control.

## The problem

Card / payment fraud systems sit on a painful tradeoff:

- **Catch fraud** → deeper models, more features, more milliseconds
- **Approve good customers** → tight latency budgets (often under 100ms)

Always running the full model stack wastes compute on obviously safe traffic.  
Always running cheap rules misses harder fraud.

## The product idea

Score every transaction in **tiers**:

1. **T0 rules** — instant, interpretable first pass  
2. **T1 fast ML** — light calibrated model  
3. **T2 full ML** — heavier model with richer features  

An **operations-research router** chooses depth under a latency budget and **cascades** (early-exits) when the score is clearly safe or clearly fraudulent.

## Why baseline vs optimized matters

| Mode | Story |
|------|--------|
| Baseline | Always T0→T1→T2 — simple, expensive, predictable |
| Optimized | Plan + cascade — usually faster for the same decision quality story |

The Ops Console and holdout reports make that claim measurable: latency, tier-stop mix, capture @ fixed FPR, operational recall.

## What “production-style” means here

Not a notebook demo. The portfolio artifact includes:

- Versioned FastAPI (`/v1`) with OpenAPI docs  
- Postgres persistence + Alembic migrations  
- Redis-backed jobs and rate limiting  
- JWT auth, self-serve registration, password reset flow  
- Next.js ops dashboard (playground, history, drift, jobs, holdout upload)  
- Docker + CI + Render live deploy path  

## Demo narrative (2 minutes)

1. Open the live Ops Console and register.  
2. Playground: same transaction in **optimized** vs **baseline** — show early exit and latency delta.  
3. History: prove the decision landed in Postgres.  
4. Upload a labeled CSV → holdout capture report (real scores vs labels).  
5. Enqueue a batch job → worker completes via Redis.  

## Interview talking points

- Resource-constrained routing (latency as the scarce resource)  
- Cascade / early-exit as an ops policy, not just an ML trick  
- Calibration + thresholds that produce approve/review/decline mix  
- Observability: request IDs, metrics, persisted audit trail  
- Honest limitation: synthetic data / portfolio-scale infra — architecture is the skill signal  

## Links

- Architecture: [architecture.md](architecture.md)  
- Deploy: [deploy-render.md](deploy-render.md)  
- Repo: https://github.com/vsh0711/tiered-fraud-api  
