import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from app.config import Settings, get_settings
from app.metrics_store import record
from app.models.schemas import RoutingMode, ScoreResponse, TransactionRequest
from ml.inference import InferenceEngine, get_engine
from or_router.pipeline import score_transaction

logger = logging.getLogger("fraud_api.score")
router = APIRouter(tags=["score"])


def _engine(settings: Settings = Depends(get_settings)) -> InferenceEngine:
    eng = get_engine(settings.models_dir)
    if not eng.ready:
        raise HTTPException(status_code=503, detail="Models not loaded; run scripts/train_models.py")
    return eng


@router.post("/score", response_model=ScoreResponse)
def score(
    body: TransactionRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    engine: InferenceEngine = Depends(_engine),
    mode_query: RoutingMode | None = Query(default=None, alias="mode"),
    x_routing_mode: str | None = Header(default=None, alias="X-Routing-Mode"),
):
    mode = mode_query
    if x_routing_mode:
        try:
            mode = RoutingMode(x_routing_mode.lower())
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid X-Routing-Mode") from e
    if mode is None:
        mode = RoutingMode.optimized

    resp = score_transaction(body, mode, engine, settings)
    last_tier = resp.tiers_executed[-1].tier.value if resp.tiers_executed else "none"
    record(resp.routing_mode.value, resp.decision.value, resp.cumulative_latency_ms, last_tier)
    logger.info(
        '{"request_id":"%s","mode":"%s","decision":"%s","latency_ms":%.2f,"tiers":%d}',
        body.request_id,
        resp.routing_mode.value,
        resp.decision.value,
        resp.cumulative_latency_ms,
        len(resp.tiers_executed),
    )
    return resp
