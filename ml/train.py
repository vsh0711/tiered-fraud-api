from __future__ import annotations

from pathlib import Path

import joblib
from sklearn.ensemble import HistGradientBoostingClassifier
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.features import build_feature_frame
from sim.generator import GeneratorConfig, generate_transactions


def train_and_persist(models_dir: Path, n_samples: int = 40_000) -> dict:
    models_dir.mkdir(parents=True, exist_ok=True)
    df = generate_transactions(GeneratorConfig(n_samples=n_samples, seed=42))
    y = df["is_fraud"].values

    X_fast = build_feature_frame(df, feature_set="fast")
    X_full = build_feature_frame(df, feature_set="full")

    Xf_tr, Xf_te, y_tr, y_te = train_test_split(X_fast, y, test_size=0.2, random_state=42, stratify=y)
    Xfull_tr, Xfull_te, _, _ = train_test_split(X_full, y, test_size=0.2, random_state=42, stratify=y)

    t1_base = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=500, class_weight="balanced", random_state=42)),
        ]
    )
    t1_cal = CalibratedClassifierCV(t1_base, method="isotonic", cv=3)
    t1_cal.fit(Xf_tr, y_tr)
    t1_proba = t1_cal.predict_proba(Xf_te)[:, 1]

    t2_base = HistGradientBoostingClassifier(
        max_depth=6,
        max_iter=180,
        learning_rate=0.06,
        min_samples_leaf=30,
        random_state=42,
    )
    t2_cal = CalibratedClassifierCV(t2_base, method="isotonic", cv=3)
    t2_cal.fit(Xfull_tr, y_tr)
    t2_proba = t2_cal.predict_proba(Xfull_te)[:, 1]

    artifacts = {
        "t1": {
            "model": t1_cal,
            "feature_columns": list(X_fast.columns),
            "feature_set": "fast",
        },
        "t2": {
            "model": t2_cal,
            "feature_columns": list(X_full.columns),
            "feature_set": "full",
        },
        "metrics": {
            "t1_auc": float(roc_auc_score(y_te, t1_proba)),
            "t1_ap": float(average_precision_score(y_te, t1_proba)),
            "t2_auc": float(roc_auc_score(y_te, t2_proba)),
            "t2_ap": float(average_precision_score(y_te, t2_proba)),
            "fraud_rate_train": float(y.mean()),
            "n_train": int(len(y_tr)),
        },
    }

    joblib.dump(artifacts["t1"], models_dir / "tier1.joblib")
    joblib.dump(artifacts["t2"], models_dir / "tier2.joblib")
    joblib.dump(artifacts["metrics"], models_dir / "training_metrics.joblib")
    return artifacts["metrics"]
