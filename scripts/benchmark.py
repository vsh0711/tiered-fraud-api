#!/usr/bin/env python3
"""Offline evaluation: fraud capture + decision mix for baseline vs optimized."""

from __future__ import annotations

import json
from pathlib import Path

from app.config import get_settings
from app.services.eval_report import build_capture_report, persist_capture_report
from app.services.thresholds import apply_trained_thresholds
from ml.inference import InferenceEngine, reset_engine


def main() -> None:
    settings = apply_trained_thresholds(get_settings())
    reset_engine()
    engine = InferenceEngine(settings.models_dir)
    engine.load()
    report = build_capture_report(engine, settings, n_samples=1200, seed=7)
    persist_capture_report(report)

    bench_path = Path("artifacts/benchmark_results.json")
    enrich = json.loads(bench_path.read_text()) if bench_path.exists() else {}
    enrich["offline_eval"] = report
    bench_path.parent.mkdir(parents=True, exist_ok=True)
    bench_path.write_text(json.dumps(enrich, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
