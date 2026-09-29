# Tiered Fraud Scoring API

Enterprise-style **FinTech fraud scoring** service: calibrated ML tiers (T0 rules → T1 fast → T2 full) plus an **operations-research router** that picks depth under a latency budget and **cascades** when scores are clearly safe or fraudulent.

Built for portfolio demos comparing **baseline** (always run the full stack) vs **optimized** (OR + cascade).

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) or `pip`

## Quick start (local)

**First time in Cursor on your Mac?** See Project Context `docs/local-ide-setup.md` (venv, interpreter, Run/Debug configs).

```bash
cd /workspace
uv sync                    # or: pip install -e .
python scripts/train_models.py
uvicorn app.main:app --host 127.0.0.1 --port 8742
```

Health check:

```bash
curl -s http://127.0.0.1:8742/health | jq
```

Score a transaction (optimized mode default):

```bash
curl -s -X POST http://127.0.0.1:8742/score \
  -H 'Content-Type: application/json' \
  -H 'X-Routing-Mode: optimized' \
  -d '{
    "request_id": "demo-1",
    "amount": 420.50,
    "merchant_category": "electronics",
    "country": "US",
    "device_risk_score": 0.15,
    "velocity_1h": 1,
    "velocity_24h": 3
  }' | jq
```

Baseline (always T0→T1→T2):

```bash
curl -s -X POST http://127.0.0.1:8742/score \
  -H 'Content-Type: application/json' \
  -H 'X-Routing-Mode: baseline' \
  -d '{ ... same body ... }' | jq
```

## Benchmarks

With the API running:

```bash
python scripts/load_test.py      # HTTP load test → artifacts/benchmark_results.json
python scripts/benchmark.py      # offline fraud capture @ 5% FPR (merges into same JSON)
pytest tests/
```

Metrics endpoint: `GET /metrics` (Prometheus) or `Accept: application/json`.

## Docker (optional)

```bash
docker compose up --build
```

## Project layout

| Path | Purpose |
|------|---------|
| `app/` | FastAPI app, config, metrics |
| `or_router/` | OR planning + scoring pipeline |
| `ml/` | Features, training, inference |
| `sim/` | Synthetic transaction generator |
| `scripts/` | Train + benchmark utilities |
| `tests/` | OR router unit tests |

## Routing modes

- **`X-Routing-Mode: baseline`** — sequential full tier stack (no early exit).
- **`X-Routing-Mode: optimized`** — latency-budget knapsack + adaptive cascade.

Storyline and architecture notes live in the Project store under `docs/portfolio-story.md` and `docs/architecture.md`.

## License

MIT (portfolio use).
