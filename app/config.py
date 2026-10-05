from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    # Optional one-time bootstrap only when FRAUD_BOOTSTRAP_ADMIN=true
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
    # Tuned for stronger synthetic fraud signal + calibrated models
    approve_threshold: float = 0.22
    decline_threshold: float = 0.55
    cascade_safe_upper: float = 0.08
    cascade_fraud_lower: float = 0.70
    auto_apply_trained_thresholds: bool = True
    chance_constraint_max_miss_rate: float = 0.02


@lru_cache
def get_settings() -> Settings:
    return Settings()
