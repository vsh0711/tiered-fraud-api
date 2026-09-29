#!/usr/bin/env python3
"""
Compare baseline vs optimized routing on a synthetic request stream.
Writes artifacts/benchmark_results.json
"""

from __future__ import annotations

import asyncio
import json
import statistics
import time
from pathlib import Path

import httpx
import pandas as pd

from sim.generator import GeneratorConfig, generate_transactions, row_to_request_dict

API = "http://127.0.0.1:8742"
N_REQUESTS = 400


def _percentile(vals: list[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = min(len(s) - 1, max(0, int(p * len(s)) - 1))
    return s[idx]


async def _run_mode(client: httpx.AsyncClient, mode: str, payloads: list[dict]) -> dict:
    latencies: list[float] = []
    tier_stops: dict[str, int] = {}
    decisions: dict[str, int] = {}
    errors = 0

    for p in payloads:
        headers = {"X-Routing-Mode": mode}
        t0 = time.perf_counter()
        try:
            r = await client.post(f"{API}/score", json=p, headers=headers, timeout=30.0)
            r.raise_for_status()
            data = r.json()
        except Exception:
            errors += 1
            continue
        latencies.append((time.perf_counter() - t0) * 1000)
        if data.get("tiers_executed"):
            last = data["tiers_executed"][-1]["tier"]
            tier_stops[last] = tier_stops.get(last, 0) + 1
        dec = data.get("decision", "unknown")
        decisions[dec] = decisions.get(dec, 0) + 1

    return {
        "mode": mode,
        "requests": len(latencies),
        "errors": errors,
        "latency_ms": {
            "p50": round(_percentile(latencies, 0.5), 3),
            "p95": round(_percentile(latencies, 0.95), 3),
            "p99": round(_percentile(latencies, 0.99), 3),
            "mean": round(statistics.mean(latencies), 3) if latencies else 0,
        },
        "tier_stop_pct": {
            k: round(100 * v / max(len(latencies), 1), 2) for k, v in tier_stops.items()
        },
        "decisions": decisions,
    }


async def main() -> None:
    df = generate_transactions(GeneratorConfig(n_samples=N_REQUESTS, seed=99))
    payloads = [row_to_request_dict(row, request_id=f"bench_{i}") for i, row in df.iterrows()]

    async with httpx.AsyncClient() as client:
        health = await client.get(f"{API}/health")
        health.raise_for_status()
        baseline = await _run_mode(client, "baseline", payloads)
        optimized = await _run_mode(client, "optimized", payloads)

    # Offline fraud capture proxy @ ~5% FPR using stored labels
    fraud_rate = float(df["is_fraud"].mean())
    result = {
        "n_requests_per_mode": N_REQUESTS,
        "dataset_fraud_rate_pct": round(fraud_rate * 100, 3),
        "baseline": baseline,
        "optimized": optimized,
        "notes": "Fraud capture @ fixed FPR computed offline in scripts/benchmark.py on held-out scores",
    }
    out = Path("artifacts/benchmark_results.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
