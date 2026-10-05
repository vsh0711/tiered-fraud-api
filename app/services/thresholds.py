from __future__ import annotations

import logging
from pathlib import Path

import joblib

from app.config import Settings, get_settings

logger = logging.getLogger("fraud_api.thresholds")


def apply_trained_thresholds(settings: Settings | None = None) -> Settings:
    """Optionally overlay approve/decline/cascade cutpoints from training artifacts."""
    settings = settings or get_settings()
    if not settings.auto_apply_trained_thresholds:
        return settings
    path = Path(settings.models_dir) / "thresholds.joblib"
    if not path.exists():
        return settings
    try:
        t = joblib.load(path)
        settings.approve_threshold = float(t.get("approve_threshold", settings.approve_threshold))
        settings.decline_threshold = float(t.get("decline_threshold", settings.decline_threshold))
        settings.cascade_safe_upper = float(t.get("cascade_safe_upper", settings.cascade_safe_upper))
        settings.cascade_fraud_lower = float(t.get("cascade_fraud_lower", settings.cascade_fraud_lower))
        logger.info(
            '{"event":"thresholds_applied","approve":%.4f,"decline":%.4f,"safe":%.4f,"fraud":%.4f}',
            settings.approve_threshold,
            settings.decline_threshold,
            settings.cascade_safe_upper,
            settings.cascade_fraud_lower,
        )
    except Exception:
        logger.exception("failed_to_apply_trained_thresholds")
    return settings
