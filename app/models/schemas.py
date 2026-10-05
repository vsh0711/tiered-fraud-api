from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


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
    request_id: str = Field(..., min_length=1, max_length=128, examples=["demo-1"])
    amount: float = Field(..., gt=0, examples=[420.5])
    merchant_category: str = Field(..., examples=["electronics"])
    country: str = Field(..., min_length=2, max_length=2, examples=["US"])
    device_risk_score: float = Field(..., ge=0, le=1, examples=[0.15])
    velocity_1h: int = Field(..., ge=0, examples=[1])
    velocity_24h: int = Field(..., ge=0, examples=[3])
    is_international: bool = False
    hour_of_day: int = Field(default=12, ge=0, le=23)
    deadline_ms: float | None = Field(default=None, examples=[100])
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
    event_id: UUID | None = None


class CompareScoreResponse(BaseModel):
    request: TransactionRequest
    optimized: ScoreResponse
    baseline: ScoreResponse
    latency_delta_ms: float
    early_exit_saved_tiers: bool


class HealthResponse(BaseModel):
    status: str
    models_loaded: bool
    version: str = "1.0.0"
    database: str = "unknown"
    redis: str = "unknown"


class ReadyResponse(BaseModel):
    status: str
    checks: dict[str, str]


class MetricsSummary(BaseModel):
    requests_total: int
    by_mode: dict[str, int]
    by_decision: dict[str, int]
    by_tier_stop: dict[str, int]
    latency_ms_avg: dict[str, float]
    latency_ms_p99: dict[str, float] = Field(default_factory=dict)


class LoginRequest(BaseModel):
    username: str = Field(..., description="Username or email")
    password: str


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=20)
    new_password: str = Field(..., min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)


class ApiKeyCreateResponse(BaseModel):
    id: UUID
    name: str
    api_key: str
    key_prefix: str
    created_at: datetime


class ScoreEventOut(BaseModel):
    id: UUID
    request_id: str
    routing_mode: str
    decision: str
    fraud_probability: float
    cumulative_latency_ms: float
    deadline_ms: float
    early_exit: bool
    last_tier: str
    amount: float
    merchant_category: str
    country: str
    created_at: datetime
    tiers_executed: list[Any] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class PaginatedScoreEvents(BaseModel):
    items: list[ScoreEventOut]
    total: int
    limit: int
    offset: int


class JobCreateRequest(BaseModel):
    job_type: str = Field(..., examples=["batch_score", "drift_scan"])
    payload: dict[str, Any] = Field(default_factory=dict)


class JobOut(BaseModel):
    id: UUID
    job_type: str
    status: str
    payload: dict[str, Any]
    result: dict[str, Any]
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class DriftSnapshotOut(BaseModel):
    id: UUID
    drift_strength: float
    sample_size: int
    feature_stats: dict[str, Any]
    psi_by_feature: dict[str, float]
    alert: bool
    summary: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DriftRunRequest(BaseModel):
    n_samples: int = Field(default=2000, ge=100, le=20_000)
    drift_strength: float = Field(default=0.35, ge=0, le=1)
