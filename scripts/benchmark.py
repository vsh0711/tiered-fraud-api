#!/usr/bin/env python3
"""Offline evaluation: fraud capture @ 5% FPR for baseline (always T2) vs optimized cascade."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from app.config import get_settings
from app.models.schemas import RoutingMode, TransactionRequest
from ml.inference import InferenceEngine
from or_router.pipeline import score_transaction
from sim.generator import GeneratorConfig, generate_transactions, row_to_request_dict


def capture_at_fpr(scores: np.ndarray, labels: np.ndarray, target_fpr: float = 0.05) -> float:
    thresh = np.quantile(scores[labels == 0], 1 - target_fpr)
    caught = (scores[labels == 1] >= thresh).mean()
    return float(caught)


def main() -> None:
    settings = get_settings()
    engine = InferenceEngine(settings.models_dir)
    engine.load()
    df = generate_transactions(GeneratorConfig(n_samples=600, seed=7))
    labels = df["is_fraud"].values

    base_scores = []
    opt_scores = []
    base_lat = []
    opt_lat = []
    opt_tiers = []

    for i, row in df.iterrows():
        req = TransactionRequest(**row_to_request_dict(row, f"offline_{i}"))
        b = score_transaction(req, RoutingMode.baseline, engine, settings)
        o = score_transaction(req, RoutingMode.optimized, engine, settings)
        base_scores.append(b.fraud_probability)
        opt_scores.append(o.fraud_probability)
        base_lat.append(b.cumulative_latency_ms)
        opt_lat.append(o.cumulative_latency_ms)
        if o.tiers_executed:
            opt_tiers.append(o.tiers_executed[-1].tier.value)

    base_scores_a = np.array(base_scores)
    opt_scores_a = np.array(opt_scores)
    cap_base = capture_at_fpr(base_scores_a, labels, 0.05)
    cap_opt = capture_at_fpr(opt_scores_a, labels, 0.05)

    tier_pct = pd.Series(opt_tiers).value_counts(normalize=True).mul(100).round(2).to_dict()

    enrich = {}
    bench_path = Path("artifacts/benchmark_results.json")
    if bench_path.exists():
        enrich = json.loads(bench_path.read_text())
    enrich["offline_eval"] = {
        "fraud_capture_at_5pct_fpr": {"baseline": round(cap_base, 4), "optimized": round(cap_opt, 4)},
        "simulated_latency_ms_mean": {"baseline": round(float(np.mean(base_lat)), 3), "optimized": round(float(np.mean(opt_lat)), 3)},
        "optimized_tier_stop_pct": tier_pct,
    }
    bench_path.parent.mkdir(parents=True, exist_ok=True)
    bench_path.write_text(json.dumps(enrich, indent=2))
    print(json.dumps(enrich["offline_eval"], indent=2))


if __name__ == "__main__":
    main()
