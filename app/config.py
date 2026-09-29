from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FRAUD_", env_file=".env", extra="ignore")

    app_name: str = "Tiered Fraud Scoring API"
    models_dir: Path = Path("data/models")
    default_deadline_ms: float = 100.0
    safety_margin_ms: float = 5.0
    tier0_latency_ms: float = 0.5
    tier1_latency_ms: float = 8.0
    tier2_latency_ms: float = 45.0
    fraud_value: float = 100.0
    latency_penalty_per_ms: float = 0.15
    review_cost: float = 12.0
    approve_threshold: float = 0.35
    decline_threshold: float = 0.72
    cascade_safe_upper: float = 0.12
    cascade_fraud_lower: float = 0.88
    chance_constraint_max_miss_rate: float = 0.02
    request_timeout_ms: float = 200.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
