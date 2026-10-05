from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_user
from app.db.models import User
from app.db.repositories import list_score_events, score_stats
from app.db.session import get_db
from app.models.schemas import PaginatedScoreEvents, ScoreEventOut

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/scores", response_model=PaginatedScoreEvents)
async def history_scores(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    decision: str | None = None,
    routing_mode: str | None = None,
    country: str | None = None,
):
    rows, total = await list_score_events(
        db,
        limit=limit,
        offset=offset,
        decision=decision,
        routing_mode=routing_mode,
        country=country,
    )
    items = [
        ScoreEventOut(
            id=r.id,
            request_id=r.request_id,
            routing_mode=r.routing_mode,
            decision=r.decision,
            fraud_probability=r.fraud_probability,
            cumulative_latency_ms=r.cumulative_latency_ms,
            deadline_ms=r.deadline_ms,
            early_exit=r.early_exit,
            last_tier=r.last_tier,
            amount=r.amount,
            merchant_category=r.merchant_category,
            country=r.country,
            created_at=r.created_at,
            tiers_executed=r.tiers_executed or [],
            metadata=r.metadata_json or {},
        )
        for r in rows
    ]
    return PaginatedScoreEvents(items=items, total=total, limit=limit, offset=offset)


@router.get("/stats")
async def history_stats(db: AsyncSession = Depends(get_db), _: User = Depends(require_user)):
    return await score_stats(db)
