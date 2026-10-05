from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FRAUD_", env_file=".env", extra="ignore")

    app_name: str = "Tiered Fraud Scoring API"
    app_version: str = "1.0.0"
    environment: str = "development"
    models_dir: Path = Path("data/models")

    database_url: str = "postgresql+asyncpg://fraud:fraud@localhost:5432/fraud"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me-in-production-use-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12
    bootstrap_admin: bool = False
    admin_username: str = "admin"
    admin_password: str = ""
    admin_email: str = ""
    demo_api_key: str = "tf_demo_key_change_me"

    frontend_base_url: str = "http://127.0.0.1:3000"
    password_reset_expire_minutes: int = 30
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@tiered-fraud.local"
    smtp_use_tls: bool = True

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    rate_limit_per_minute: int = 600
    request_timeout_ms: float = 200.0

    default_deadline_ms: float = 100.0
    safety_margin_ms: float = 5.0
    tier0_latency_ms: float = 0.5
    tier1_latency_ms: float = 8.0
    tier2_latency_ms: float = 45.0
    fraud_value: float = 100.0
    latency_penalty_per_ms: float = 0.15
    review_cost: float = 12.0
    approve_threshold: float = 0.22
    decline_threshold: float = 0.55
    cascade_safe_upper: float = 0.08
    cascade_fraud_lower: float = 0.70
    auto_apply_trained_thresholds: bool = True
    chance_constraint_max_miss_rate: float = 0.02

    @model_validator(mode="after")
    def normalize_runtime_urls(self) -> Settings:
        db = os.getenv("FRAUD_DATABASE_URL") or os.getenv("DATABASE_URL") or self.database_url
        redis = os.getenv("FRAUD_REDIS_URL") or os.getenv("REDIS_URL") or self.redis_url
        self.database_url = _normalize_database_url(db)
        self.redis_url = redis
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
