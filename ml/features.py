from __future__ import annotations

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


def _one_hot_category(series: pd.Series) -> pd.DataFrame:
    return pd.get_dummies(series, prefix="cat", dtype=float).reindex(
        columns=[f"cat_{c}" for c in MERCHANT_CATEGORIES], fill_value=0.0
    )


def build_feature_frame(df: pd.DataFrame, feature_set: str = "full") -> pd.DataFrame:
    base = pd.DataFrame(
        {
            "amount_log": np.log1p(df["amount"].astype(float)),
            "device_risk_score": df["device_risk_score"].astype(float),
            "velocity_1h": df["velocity_1h"].astype(float),
            "velocity_24h": df["velocity_24h"].astype(float),
            "is_international": df["is_international"].astype(float),
            "hour_sin": np.sin(2 * np.pi * df["hour_of_day"].astype(float) / 24),
            "hour_cos": np.cos(2 * np.pi * df["hour_of_day"].astype(float) / 24),
        },
        index=df.index,
    )
    if feature_set == "fast":
        return base[["amount_log", "device_risk_score", "velocity_1h", "is_international"]]

    cats = _one_hot_category(df["merchant_category"])
    country_risk = df["country"].map(_country_risk_map()).fillna(0.3)
    extra = pd.DataFrame({"country_risk": country_risk}, index=df.index)
    return pd.concat([base, cats, extra], axis=1)


def _country_risk_map() -> dict[str, float]:
    return {
        "US": 0.15,
        "GB": 0.2,
        "DE": 0.18,
        "FR": 0.19,
        "IN": 0.35,
        "BR": 0.32,
        "NG": 0.45,
        "CA": 0.17,
        "AU": 0.16,
        "SG": 0.14,
    }


def request_to_feature_row(req: dict, feature_set: str = "full") -> pd.DataFrame:
    df = pd.DataFrame([req])
    return build_feature_frame(df, feature_set=feature_set)
