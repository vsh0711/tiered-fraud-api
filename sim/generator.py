"""Synthetic transaction generator with latent fraud (~1-3%)."""

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


@dataclass
class GeneratorConfig:
    n_samples: int = 50_000
    fraud_rate_target: float = 0.02
    seed: int = 42
    drift_strength: float = 0.0


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def generate_transactions(cfg: GeneratorConfig) -> pd.DataFrame:
    rng = _rng(cfg.seed)
    n = cfg.n_samples

    amount = rng.lognormal(mean=3.8, sigma=1.1, size=n).clip(1, 50_000)
    merchant_category = rng.choice(MERCHANT_CATEGORIES, size=n)
    country = rng.choice(COUNTRIES, size=n, p=[0.35, 0.1, 0.08, 0.07, 0.12, 0.06, 0.05, 0.07, 0.05, 0.05])
    device_risk = rng.beta(2, 8, size=n) + rng.uniform(0, 0.15, size=n)
    device_risk = device_risk.clip(0, 1)
    velocity_1h = rng.poisson(1.2, size=n)
    velocity_24h = velocity_1h + rng.poisson(3.5, size=n)
    is_international = (country != "US") & (rng.random(n) < 0.35)
    hour_of_day = rng.integers(0, 24, size=n)

    drift = cfg.drift_strength
    if drift > 0:
        device_risk = (device_risk + drift * rng.uniform(0, 0.3, n)).clip(0, 1)

    cat_high = np.isin(merchant_category, list(HIGH_RISK_CATS))
    logit = (
        -3.6
        + 0.00006 * amount
        + 3.2 * device_risk
        + 0.42 * cat_high
        + 0.28 * is_international.astype(float)
        + 0.1 * np.clip(velocity_1h - 2, 0, 10)
        + 0.06 * np.clip(velocity_24h - 5, 0, 20)
        + 0.18 * (hour_of_day >= 22).astype(float)
        + drift * 0.5
    )
    if drift > 0:
        logit += drift * rng.normal(0, 0.4, n)

    p_fraud = 1 / (1 + np.exp(-logit))
    p_fraud = p_fraud * (cfg.fraud_rate_target / max(p_fraud.mean(), 1e-6))
    p_fraud = p_fraud.clip(0.001, 0.95)
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
        }
    )
    df["transaction_id"] = [f"txn_{i:08d}" for i in range(n)]
    return df


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
