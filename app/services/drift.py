from __future__ import annotations

import numpy as np
import pandas as pd

from app.db.models import DriftSnapshot
from sim.drift import generate_with_drift
from sim.generator import GeneratorConfig, generate_transactions


def _psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    eps = 1e-6
    quantiles = np.linspace(0, 1, bins + 1)
    breaks = np.unique(np.quantile(expected, quantiles))
    if len(breaks) < 3:
        return 0.0
    e_counts, _ = np.histogram(expected, bins=breaks)
    a_counts, _ = np.histogram(actual, bins=breaks)
    e_perc = e_counts / max(e_counts.sum(), 1) + eps
    a_perc = a_counts / max(a_counts.sum(), 1) + eps
    return float(np.sum((a_perc - e_perc) * np.log(a_perc / e_perc)))


def compute_drift_snapshot(n_samples: int = 2000, drift_strength: float = 0.35) -> DriftSnapshot:
    baseline = generate_transactions(GeneratorConfig(n_samples=n_samples, seed=7, drift_strength=0.0))
    current = generate_with_drift(n_samples=n_samples, drift_strength=drift_strength)

    numeric_cols = ["amount", "device_risk_score", "velocity_1h", "velocity_24h"]
    psi_by_feature: dict[str, float] = {}
    feature_stats: dict[str, dict] = {}

    for col in numeric_cols:
        psi_by_feature[col] = round(_psi(baseline[col].to_numpy(), current[col].to_numpy()), 4)
        feature_stats[col] = {
            "baseline_mean": round(float(baseline[col].mean()), 4),
            "current_mean": round(float(current[col].mean()), 4),
            "baseline_std": round(float(baseline[col].std()), 4),
            "current_std": round(float(current[col].std()), 4),
        }

    max_psi = max(psi_by_feature.values()) if psi_by_feature else 0.0
    alert = max_psi >= 0.2
    summary = (
        f"Max PSI={max_psi:.3f} across {len(numeric_cols)} features; "
        f"{'ALERT' if alert else 'stable'} at drift_strength={drift_strength}"
    )
    return DriftSnapshot(
        drift_strength=drift_strength,
        sample_size=n_samples,
        feature_stats=feature_stats,
        psi_by_feature=psi_by_feature,
        alert=alert,
        summary=summary,
    )


def feature_distribution_frame(n_samples: int = 1000, drift_strength: float = 0.0) -> pd.DataFrame:
    return generate_transactions(GeneratorConfig(n_samples=n_samples, seed=11, drift_strength=drift_strength))
