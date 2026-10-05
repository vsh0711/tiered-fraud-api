"""Synthetic transaction generator with separable fraud signal (~4%)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
import pandas as pd

MERCHANT_CATEGORIES = [
    "grocery",
    "electronics",
    "travel",
    "gambling",
    "digital_goods",
    "fuel",
    "restaurant",
    "luxury",
]
COUNTRIES = ["US", "GB", "DE", "FR", "IN", "BR", "NG", "CA", "AU", "SG"]
HIGH_RISK_CATS = {"gambling", "digital_goods", "luxury"}
HIGH_RISK_COUNTRIES = {"NG", "BR", "IN"}


@dataclass
class GeneratorConfig:
    n_samples: int = 50_000
    fraud_rate_target: float = 0.04
    seed: int = 42
    drift_strength: float = 0.0


def _rng(seed: int) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(seed))


def generate_transactions(cfg: GeneratorConfig) -> pd.DataFrame:
    rng = _rng(cfg.seed)
    n = cfg.n_samples

    # Mixture: mostly normal traffic + a risky cluster that drives fraud
    risky_cluster = rng.random(n) < 0.12
    amount = np.where(
        risky_cluster,
        rng.lognormal(mean=6.2, sigma=0.7, size=n).clip(200, 50_000),
        rng.lognormal(mean=3.5, sigma=0.9, size=n).clip(1, 8_000),
    )
    merchant_category = np.where(
        risky_cluster,
        rng.choice(list(HIGH_RISK_CATS), size=n),
        rng.choice(MERCHANT_CATEGORIES, size=n),
    )
    country = np.where(
        risky_cluster,
        rng.choice(list(HIGH_RISK_COUNTRIES) + ["US"], size=n, p=[0.35, 0.25, 0.25, 0.15]),
        rng.choice(
            COUNTRIES,
            size=n,
            p=[0.4, 0.1, 0.08, 0.07, 0.1, 0.05, 0.04, 0.07, 0.05, 0.04],
        ),
    )
    device_risk = np.where(
        risky_cluster,
        rng.beta(5, 2, size=n),
        rng.beta(2, 9, size=n),
    )
    device_risk = (device_risk + rng.uniform(0, 0.05, size=n)).clip(0, 1)
    velocity_1h = np.where(risky_cluster, rng.poisson(4.5, size=n), rng.poisson(0.8, size=n))
    velocity_24h = velocity_1h + np.where(
        risky_cluster, rng.poisson(10, size=n), rng.poisson(2.5, size=n)
    )
    is_international = (country != "US") & ((risky_cluster) | (rng.random(n) < 0.25))
    hour_of_day = np.where(
        risky_cluster,
        rng.choice(np.arange(24), size=n, p=_night_heavy_hours()),
        rng.integers(0, 24, size=n),
    )

    drift = cfg.drift_strength
    if drift > 0:
        device_risk = (device_risk + drift * rng.uniform(0, 0.35, n)).clip(0, 1)

    cat_high = np.isin(merchant_category, list(HIGH_RISK_CATS)).astype(float)
    country_high = np.isin(country, list(HIGH_RISK_COUNTRIES)).astype(float)
    night = (hour_of_day >= 22).astype(float) + (hour_of_day <= 4).astype(float)

    # Strong, mostly linear signal so calibrated models can separate classes
    logit = (
        -4.8
        + 1.15 * np.log1p(amount) / 8.0
        + 4.8 * device_risk
        + 1.35 * cat_high
        + 0.95 * country_high
        + 0.85 * is_international.astype(float)
        + 0.55 * np.clip(velocity_1h / 6.0, 0, 1.5)
        + 0.35 * np.clip(velocity_24h / 20.0, 0, 1.5)
        + 0.7 * night
        + 1.6 * risky_cluster.astype(float)
        + drift * 0.8
    )
    if drift > 0:
        logit += drift * rng.normal(0, 0.35, n)

    p_fraud = 1 / (1 + np.exp(-logit))
    # Soft rescale toward target rate without crushing ranking
    scale = cfg.fraud_rate_target / max(float(p_fraud.mean()), 1e-6)
    p_fraud = (p_fraud * np.clip(scale, 0.6, 1.4)).clip(0.0005, 0.95)
    is_fraud = rng.random(n) < p_fraud

    df = pd.DataFrame(
        {
            "amount": amount,
            "merchant_category": merchant_category,
            "country": country,
            "device_risk_score": device_risk,
            "velocity_1h": velocity_1h,
            "velocity_24h": velocity_24h,
            "is_international": is_international,
            "hour_of_day": hour_of_day,
            "is_fraud": is_fraud.astype(int),
            "p_fraud_latent": p_fraud,
        }
    )
    df["transaction_id"] = [f"txn_{i:08d}" for i in range(n)]
    return df


def _night_heavy_hours() -> np.ndarray:
    p = np.ones(24)
    p[22:] = 3.5
    p[:5] = 3.0
    return p / p.sum()


def row_to_request_dict(row: pd.Series, request_id: str | None = None) -> dict:
    rid = request_id or hashlib.sha256(str(row.name).encode()).hexdigest()[:16]
    return {
        "request_id": rid,
        "amount": float(row["amount"]),
        "merchant_category": str(row["merchant_category"]),
        "country": str(row["country"]),
        "device_risk_score": float(row["device_risk_score"]),
        "velocity_1h": int(row["velocity_1h"]),
        "velocity_24h": int(row["velocity_24h"]),
        "is_international": bool(row["is_international"]),
        "hour_of_day": int(row["hour_of_day"]),
    }
