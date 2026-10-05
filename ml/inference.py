from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np

from ml.features import request_to_feature_row

HIGH_RISK_CATS = {"gambling", "digital_goods", "luxury"}
HIGH_RISK_COUNTRIES = {"NG", "BR", "IN"}


@dataclass
class ModelBundle:
    t1: dict
    t2: dict
    loaded_at: float


class InferenceEngine:
    def __init__(self, models_dir: Path) -> None:
        self.models_dir = models_dir
        self._bundle: ModelBundle | None = None

    def load(self) -> None:
        t1 = joblib.load(self.models_dir / "tier1.joblib")
        t2 = joblib.load(self.models_dir / "tier2.joblib")
        self._bundle = ModelBundle(t1=t1, t2=t2, loaded_at=time.time())

    def reload(self) -> None:
        self.load()

    @property
    def ready(self) -> bool:
        return self._bundle is not None

    def score_t0_rules(self, req: dict) -> float:
        """Rules tier aligned with synthetic fraud generative process."""
        amount = float(req["amount"])
        device = float(req["device_risk_score"])
        v1 = int(req["velocity_1h"])
        v24 = int(req["velocity_24h"])
        cat = str(req["merchant_category"])
        country = str(req.get("country", "US")).upper()
        international = bool(req.get("is_international", False))
        hour = int(req.get("hour_of_day", 12))

        score = 0.03
        score += min(np.log1p(amount) / 12.0, 0.28)
        score += device * 0.48
        score += min(max(v1 - 1, 0) * 0.055, 0.22)
        score += min(max(v24 - 4, 0) * 0.015, 0.12)
        if cat in HIGH_RISK_CATS:
            score += 0.14
        if country in HIGH_RISK_COUNTRIES:
            score += 0.1
        if international:
            score += 0.07
        if hour >= 22 or hour <= 4:
            score += 0.08
        if amount >= 2500 and device >= 0.55:
            score += 0.12
        if v1 >= 5 and cat in HIGH_RISK_CATS:
            score += 0.1
        return float(np.clip(score, 0.01, 0.99))

    def score_t1(self, req: dict) -> tuple[float, int]:
        bundle = self._require()
        X = request_to_feature_row(req, feature_set="fast")
        cols = bundle.t1["feature_columns"]
        X = X.reindex(columns=cols, fill_value=0.0)
        proba = float(bundle.t1["model"].predict_proba(X)[0, 1])
        return proba, len(cols)

    def score_t2(self, req: dict) -> tuple[float, int]:
        bundle = self._require()
        X = request_to_feature_row(req, feature_set="full")
        cols = bundle.t2["feature_columns"]
        X = X.reindex(columns=cols, fill_value=0.0)
        proba = float(bundle.t2["model"].predict_proba(X)[0, 1])
        return proba, len(cols)

    def _require(self) -> ModelBundle:
        if self._bundle is None:
            raise RuntimeError("Models not loaded")
        return self._bundle


_engine: InferenceEngine | None = None


def get_engine(models_dir: Path) -> InferenceEngine:
    global _engine
    if _engine is None:
        _engine = InferenceEngine(models_dir)
        if (models_dir / "tier1.joblib").exists():
            _engine.load()
    return _engine


def reset_engine() -> None:
    global _engine
    _engine = None
