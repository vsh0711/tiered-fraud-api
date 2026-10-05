from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import ScoreEvent
from app.db.repositories import save_score_event
from app.metrics_store import record
from app.models.schemas import RoutingMode, ScoreResponse, TransactionRequest
from ml.inference import InferenceEngine
from or_router.pipeline import score_transaction


async def score_and_persist(
    *,
    body: TransactionRequest,
    mode: RoutingMode,
    engine: InferenceEngine,
    settings: Settings,
    db: AsyncSession,
    api_key_id=None,
) -> ScoreResponse:
    resp = score_transaction(body, mode, engine, settings)
    last_tier = resp.tiers_executed[-1].tier.value if resp.tiers_executed else "none"
    record(resp.routing_mode.value, resp.decision.value, resp.cumulative_latency_ms, last_tier)

    event = ScoreEvent(
        request_id=body.request_id,
        routing_mode=resp.routing_mode.value,
        decision=resp.decision.value,
        fraud_probability=resp.fraud_probability,
        cumulative_latency_ms=resp.cumulative_latency_ms,
        deadline_ms=resp.deadline_ms,
        early_exit=resp.early_exit,
        or_utility=resp.or_utility,
        last_tier=last_tier,
        amount=body.amount,
        merchant_category=body.merchant_category,
        country=body.country.upper(),
        device_risk_score=body.device_risk_score,
        velocity_1h=body.velocity_1h,
        velocity_24h=body.velocity_24h,
        payload=body.model_dump(),
        tiers_executed=[t.model_dump(mode="json") for t in resp.tiers_executed],
        metadata_json=resp.metadata,
        api_key_id=api_key_id,
    )
    try:
        saved = await save_score_event(db, event)
        resp.event_id = saved.id
    except Exception:
        await db.rollback()
        # Idempotent retry collision: still return scored response
        resp.metadata = {**resp.metadata, "persist_warning": "duplicate_or_db_error"}
    return resp
