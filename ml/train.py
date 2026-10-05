from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.features import build_feature_frame
from sim.generator import GeneratorConfig, generate_transactions


def _threshold_at_fpr(scores: np.ndarray, labels: np.ndarray, target_fpr: float = 0.05) -> float:
    neg = scores[labels == 0]
    if len(neg) == 0:
        return 0.5
    return float(np.quantile(neg, 1 - target_fpr))


def _decision_thresholds(scores: np.ndarray, labels: np.ndarray) -> dict[str, float]:
    """Derive approve/review/decline cutpoints from holdout score distribution."""
    decline = _threshold_at_fpr(scores, labels, target_fpr=0.025)
    neg = scores[labels == 0]
    approve = float(np.quantile(neg, 0.80)) if len(neg) else 0.2
    approve = min(approve, decline - 0.1)
    approve = float(np.clip(approve, 0.15, 0.4))
    decline = float(np.clip(max(decline, approve + 0.18), 0.4, 0.85))
    return {
        "approve_threshold": round(approve, 4),
        "decline_threshold": round(decline, 4),
        "cascade_safe_upper": round(max(0.06, approve * 0.4), 4),
        "cascade_fraud_lower": round(min(0.9, decline + 0.08), 4),
    }


def train_and_persist(models_dir: Path, n_samples: int = 60_000) -> dict:
    models_dir.mkdir(parents=True, exist_ok=True)
    df = generate_transactions(GeneratorConfig(n_samples=n_samples, seed=42, fraud_rate_target=0.05))
    y = df["is_fraud"].to_numpy()

    X_fast = build_feature_frame(df, feature_set="fast")
    X_full = build_feature_frame(df, feature_set="full")

    Xf_tr, Xf_te, y_tr, y_te = train_test_split(
        X_fast, y, test_size=0.2, random_state=42, stratify=y
    )
    Xfull_tr, Xfull_te, _, _ = train_test_split(
        X_full, y, test_size=0.2, random_state=42, stratify=y
    )

    t1 = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    C=1.0,
                    random_state=42,
                ),
            ),
        ]
    )
    t1.fit(Xf_tr, y_tr)
    # Softmax/sigmoid style calibration without nested sample_weight issues
    t1_cal = CalibratedClassifierCV(t1, method="sigmoid", cv=3)
    t1_cal.fit(Xf_tr, y_tr)
    t1_proba = t1_cal.predict_proba(Xf_te)[:, 1]

    t2 = HistGradientBoostingClassifier(
        max_depth=6,
        max_iter=200,
        learning_rate=0.06,
        min_samples_leaf=40,
        l2_regularization=0.05,
        random_state=42,
        class_weight="balanced",
    )
    t2.fit(Xfull_tr, y_tr)
    t2_cal = CalibratedClassifierCV(t2, method="sigmoid", cv=3)
    t2_cal.fit(Xfull_tr, y_tr)
    t2_proba = t2_cal.predict_proba(Xfull_te)[:, 1]

    thresholds = _decision_thresholds(t2_proba, y_te)
    metrics = {
        "t1_auc": float(roc_auc_score(y_te, t1_proba)),
        "t1_ap": float(average_precision_score(y_te, t1_proba)),
        "t2_auc": float(roc_auc_score(y_te, t2_proba)),
        "t2_ap": float(average_precision_score(y_te, t2_proba)),
        "fraud_rate_train": float(y.mean()),
        "fraud_rate_holdout": float(y_te.mean()),
        "n_train": int(len(y_tr)),
        "n_holdout": int(len(y_te)),
        "recommended_thresholds": thresholds,
        "score_quantiles_t2": {
            "p50": float(np.quantile(t2_proba, 0.5)),
            "p90": float(np.quantile(t2_proba, 0.9)),
            "p95": float(np.quantile(t2_proba, 0.95)),
            "p99": float(np.quantile(t2_proba, 0.99)),
        },
    }

    joblib.dump(
        {"model": t1_cal, "feature_columns": list(X_fast.columns), "feature_set": "fast"},
        models_dir / "tier1.joblib",
    )
    joblib.dump(
        {"model": t2_cal, "feature_columns": list(X_full.columns), "feature_set": "full"},
        models_dir / "tier2.joblib",
    )
    joblib.dump(metrics, models_dir / "training_metrics.joblib")
    joblib.dump(thresholds, models_dir / "thresholds.joblib")
    return metrics
