from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RoutingMode(str, Enum):
    baseline = "baseline"
    optimized = "optimized"


class Decision(str, Enum):
    approve = "approve"
    review = "review"
    decline = "decline"


class TierName(str, Enum):
    t0_rules = "T0"
    t1_fast = "T1"
    t2_full = "T2"


class TransactionRequest(BaseModel):
    request_id: str = Field(..., min_length=1, max_length=128)
    amount: float = Field(..., gt=0)
    merchant_category: str
    country: str = Field(..., min_length=2, max_length=2)
    device_risk_score: float = Field(..., ge=0, le=1)
    velocity_1h: int = Field(..., ge=0)
    velocity_24h: int = Field(..., ge=0)
    is_international: bool = False
    hour_of_day: int = Field(default=12, ge=0, le=23)
    deadline_ms: float | None = None
    merchant_tier: str = "standard"


class TierResult(BaseModel):
    tier: TierName
    score: float
    latency_ms: float
    features_used: int


class ScoreResponse(BaseModel):
    request_id: str
    routing_mode: RoutingMode
    decision: Decision
    fraud_probability: float
    tiers_executed: list[TierResult]
    cumulative_latency_ms: float
    deadline_ms: float
    early_exit: bool
    or_utility: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    models_loaded: bool
    version: str = "0.1.0"


class MetricsSummary(BaseModel):
    requests_total: int
    by_mode: dict[str, int]
    by_decision: dict[str, int]
    by_tier_stop: dict[str, int]
    latency_ms_avg: float
    latency_ms_p99: float
