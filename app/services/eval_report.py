from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np
import pandas as pd

from app.config import Settings
from app.models.schemas import Decision, RoutingMode, TransactionRequest
from ml.inference import InferenceEngine
from or_router.pipeline import score_transaction
from or_router.router import decision_from_score
from sim.generator import GeneratorConfig, generate_transactions, row_to_request_dict

REPORT_PATH = Path("artifacts/capture_report.json")
REQUIRED_COLUMNS = [
    "amount",
    "merchant_category",
    "country",
    "device_risk_score",
    "velocity_1h",
    "velocity_24h",
    "is_fraud",
]
OPTIONAL_COLUMNS = ["is_international", "hour_of_day", "request_id"]


def capture_at_fpr(scores: np.ndarray, labels: np.ndarray, target_fpr: float = 0.05) -> float:
    neg = scores[labels == 0]
    if len(neg) == 0 or labels.sum() == 0:
        return 0.0
    thresh = np.quantile(neg, 1 - target_fpr)
    return float((scores[labels == 1] >= thresh).mean())


def confusion_at_thresholds(scores: np.ndarray, labels: np.ndarray, settings: Settings) -> dict:
    """Treat review+decline as 'flagged' for operational catch-rate."""
    flagged = np.array(
        [decision_from_score(float(s), settings) != Decision.approve for s in scores],
        dtype=bool,
    )
    y = labels.astype(bool)
    tp = int((flagged & y).sum())
    fp = int((flagged & ~y).sum())
    fn = int((~flagged & y).sum())
    tn = int((~flagged & ~y).sum())
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    fpr = fp / max(fp + tn, 1)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": round(precision, 4),
        "recall_fraud_capture": round(recall, 4),
        "fpr": round(fpr, 4),
        "flag_rate": round(float(flagged.mean()), 4),
    }


def normalize_holdout_frame(df: pd.DataFrame) -> pd.DataFrame:
    cols = {c.lower().strip(): c for c in df.columns}
    rename = {}
    for needed in REQUIRED_COLUMNS + OPTIONAL_COLUMNS:
        if needed in cols:
            rename[cols[needed]] = needed
        elif needed.replace("_", "") in {k.replace("_", "") for k in cols}:
            for k, original in cols.items():
                if k.replace("_", "") == needed.replace("_", ""):
                    rename[original] = needed
                    break
    out = df.rename(columns=rename).copy()
    missing = [c for c in REQUIRED_COLUMNS if c not in out.columns]
    if missing:
        raise ValueError(
            "CSV missing required columns: "
            + ", ".join(missing)
            + ". Required: "
            + ", ".join(REQUIRED_COLUMNS)
        )
    if len(out) < 20:
        raise ValueError("Upload at least 20 labeled rows for a meaningful holdout report")
    if len(out) > 10_000:
        raise ValueError("Upload limited to 10,000 rows")

    out["amount"] = pd.to_numeric(out["amount"], errors="coerce")
    out["device_risk_score"] = pd.to_numeric(out["device_risk_score"], errors="coerce")
    out["velocity_1h"] = pd.to_numeric(out["velocity_1h"], errors="coerce")
    out["velocity_24h"] = pd.to_numeric(out["velocity_24h"], errors="coerce")
    out["is_fraud"] = pd.to_numeric(out["is_fraud"], errors="coerce")
    if "is_international" not in out.columns:
        out["is_international"] = out["country"].astype(str).str.upper().ne("US")
    else:
        out["is_international"] = out["is_international"].astype(str).str.lower().isin(
            {"1", "true", "yes", "y"}
        ) | (pd.to_numeric(out["is_international"], errors="coerce").fillna(0) > 0)
    if "hour_of_day" not in out.columns:
        out["hour_of_day"] = 12
    else:
        out["hour_of_day"] = pd.to_numeric(out["hour_of_day"], errors="coerce").fillna(12).astype(int)

    out = out.dropna(subset=REQUIRED_COLUMNS)
    out["country"] = out["country"].astype(str).str.upper().str.slice(0, 2)
    out["merchant_category"] = out["merchant_category"].astype(str)
    out["is_fraud"] = (out["is_fraud"] > 0).astype(int)
    out["device_risk_score"] = out["device_risk_score"].clip(0, 1)
    if out["is_fraud"].nunique() < 2:
        raise ValueError("Holdout CSV must include both fraud (1) and non-fraud (0) labels")
    return out.reset_index(drop=True)


def parse_holdout_csv(content: bytes, filename: str = "upload.csv") -> pd.DataFrame:
    name = filename.lower()
    bio = io.BytesIO(content)
    if name.endswith(".parquet"):
        df = pd.read_parquet(bio)
    else:
        df = pd.read_csv(bio)
    return normalize_holdout_frame(df)


def evaluate_holdout_frame(
    df: pd.DataFrame,
    engine: InferenceEngine,
    settings: Settings,
    *,
    source: str,
    source_name: str | None = None,
) -> dict:
    labels = df["is_fraud"].to_numpy()
    base_scores: list[float] = []
    opt_scores: list[float] = []
    base_lat: list[float] = []
    opt_lat: list[float] = []
    opt_tiers: list[str] = []
    base_decisions: list[str] = []
    opt_decisions: list[str] = []

    for i, row in df.iterrows():
        rid = str(row["request_id"]) if "request_id" in df.columns and pd.notna(row.get("request_id")) else f"holdout_{i}"
        req = TransactionRequest(**row_to_request_dict(row, rid))
        b = score_transaction(req, RoutingMode.baseline, engine, settings)
        o = score_transaction(req, RoutingMode.optimized, engine, settings)
        base_scores.append(b.fraud_probability)
        opt_scores.append(o.fraud_probability)
        base_lat.append(b.cumulative_latency_ms)
        opt_lat.append(o.cumulative_latency_ms)
        base_decisions.append(b.decision.value)
        opt_decisions.append(o.decision.value)
        opt_tiers.append(o.tiers_executed[-1].tier.value if o.tiers_executed else "none")

    base_a = np.array(base_scores)
    opt_a = np.array(opt_scores)
    labels_a = labels

    return {
        "source": source,
        "source_name": source_name,
        "n_samples": int(len(df)),
        "fraud_rate_holdout": round(float(labels_a.mean()), 4),
        "thresholds": {
            "approve_threshold": settings.approve_threshold,
            "decline_threshold": settings.decline_threshold,
            "cascade_safe_upper": settings.cascade_safe_upper,
            "cascade_fraud_lower": settings.cascade_fraud_lower,
        },
        "fraud_capture_at_5pct_fpr": {
            "baseline": round(capture_at_fpr(base_a, labels_a, 0.05), 4),
            "optimized": round(capture_at_fpr(opt_a, labels_a, 0.05), 4),
        },
        "operational_flagging": {
            "baseline": confusion_at_thresholds(base_a, labels_a, settings),
            "optimized": confusion_at_thresholds(opt_a, labels_a, settings),
        },
        "decision_mix_pct": {
            "baseline": {
                k: round(100 * v / max(len(base_decisions), 1), 2)
                for k, v in pd.Series(base_decisions).value_counts().to_dict().items()
            },
            "optimized": {
                k: round(100 * v / max(len(opt_decisions), 1), 2)
                for k, v in pd.Series(opt_decisions).value_counts().to_dict().items()
            },
        },
        "latency_ms_mean": {
            "baseline": round(float(np.mean(base_lat)), 3),
            "optimized": round(float(np.mean(opt_lat)), 3),
            "savings_pct": round(
                100 * (1 - float(np.mean(opt_lat)) / max(float(np.mean(base_lat)), 1e-6)), 2
            ),
        },
        "optimized_tier_stop_pct": pd.Series(opt_tiers)
        .value_counts(normalize=True)
        .mul(100)
        .round(2)
        .to_dict(),
    }


def build_capture_report(
    engine: InferenceEngine,
    settings: Settings,
    *,
    n_samples: int = 1200,
    seed: int = 17,
) -> dict:
    df = generate_transactions(
        GeneratorConfig(n_samples=n_samples, seed=seed, fraud_rate_target=0.045)
    )
    report = evaluate_holdout_frame(
        df,
        engine,
        settings,
        source="synthetic_generator",
        source_name=f"sim/generator seed={seed}",
    )
    return report


def build_capture_report_from_upload(
    content: bytes,
    filename: str,
    engine: InferenceEngine,
    settings: Settings,
) -> dict:
    df = parse_holdout_csv(content, filename)
    return evaluate_holdout_frame(
        df,
        engine,
        settings,
        source="uploaded_file",
        source_name=filename,
    )


def sample_holdout_csv(n_samples: int = 100, seed: int = 99) -> str:
    df = generate_transactions(GeneratorConfig(n_samples=n_samples, seed=seed, fraud_rate_target=0.08))
    cols = REQUIRED_COLUMNS + ["is_international", "hour_of_day"]
    return df[cols].to_csv(index=False)


def persist_capture_report(report: dict, path: Path = REPORT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2))
    return path


def load_capture_report(path: Path = REPORT_PATH) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())
