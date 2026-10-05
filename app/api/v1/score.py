from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_engine_dep, require_api_key
from app.config import Settings, get_settings
from app.db.models import ApiKey
from app.db.session import get_db
from app.models.schemas import (
    CompareScoreResponse,
    RoutingMode,
    ScoreResponse,
    TransactionRequest,
)
from app.services.scoring import score_and_persist
from ml.inference import InferenceEngine

logger = logging.getLogger("fraud_api.score")
router = APIRouter(tags=["score"])


def _resolve_mode(
    mode_query: RoutingMode | None,
    x_routing_mode: str | None,
) -> RoutingMode:
    mode = mode_query
    if x_routing_mode:
        try:
            mode = RoutingMode(x_routing_mode.lower())
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid X-Routing-Mode") from e
    return mode or RoutingMode.optimized


@router.post(
    "/score",
    response_model=ScoreResponse,
    summary="Score a transaction",
    description="Tiered fraud score with baseline or optimized OR routing. Requires `X-API-Key`.",
)
async def score(
    body: TransactionRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    engine: InferenceEngine = Depends(get_engine_dep),
    api_key: ApiKey = Depends(require_api_key),
    mode_query: RoutingMode | None = Query(default=None, alias="mode"),
    x_routing_mode: str | None = Header(default=None, alias="X-Routing-Mode"),
):
    mode = _resolve_mode(mode_query, x_routing_mode)
    resp = await score_and_persist(
        body=body,
        mode=mode,
        engine=engine,
        settings=settings,
        db=db,
        api_key_id=api_key.id,
    )
    logger.info(
        '{"request_id":"%s","mode":"%s","decision":"%s","latency_ms":%.2f,"tiers":%d}',
        body.request_id,
        resp.routing_mode.value,
        resp.decision.value,
        resp.cumulative_latency_ms,
        len(resp.tiers_executed),
    )
    return resp


@router.post(
    "/score/compare",
    response_model=CompareScoreResponse,
    summary="Compare baseline vs optimized on the same transaction",
)
async def compare(
    body: TransactionRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    engine: InferenceEngine = Depends(get_engine_dep),
    api_key: ApiKey = Depends(require_api_key),
):
    opt = await score_and_persist(
        body=body.model_copy(update={"request_id": f"{body.request_id}-opt"}),
        mode=RoutingMode.optimized,
        engine=engine,
        settings=settings,
        db=db,
        api_key_id=api_key.id,
    )
    base = await score_and_persist(
        body=body.model_copy(update={"request_id": f"{body.request_id}-base"}),
        mode=RoutingMode.baseline,
        engine=engine,
        settings=settings,
        db=db,
        api_key_id=api_key.id,
    )
    return CompareScoreResponse(
        request=body,
        optimized=opt,
        baseline=base,
        latency_delta_ms=round(base.cumulative_latency_ms - opt.cumulative_latency_ms, 3),
        early_exit_saved_tiers=opt.early_exit,
    )
