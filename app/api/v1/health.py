from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text

from app.config import Settings, get_settings
from app.models.schemas import HealthResponse, ReadyResponse
from ml.inference import InferenceEngine, get_engine

router = APIRouter(tags=["health"])


def _engine(settings: Settings = Depends(get_settings)) -> InferenceEngine:
    return get_engine(settings.models_dir)


@router.get("/health", response_model=HealthResponse)
async def health(request: Request, settings: Settings = Depends(get_settings), engine: InferenceEngine = Depends(_engine)):
    db_status = "unknown"
    redis_status = "unknown"
    try:
        session_factory = request.app.state.session_factory
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    redis = getattr(request.app.state, "redis", None)
    if redis is not None:
        try:
            await redis.ping()
            redis_status = "ok"
        except Exception:
            redis_status = "error"
    else:
        redis_status = "disabled"
    return HealthResponse(
        status="ok" if engine.ready else "degraded",
        models_loaded=engine.ready,
        version=settings.app_version,
        database=db_status,
        redis=redis_status,
    )


@router.get("/ready", response_model=ReadyResponse)
async def ready(request: Request, engine: InferenceEngine = Depends(_engine)):
    checks: dict[str, str] = {"models": "ok" if engine.ready else "not_ready"}
    try:
        session_factory = request.app.state.session_factory
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "not_ready"
    redis = getattr(request.app.state, "redis", None)
    if redis is not None:
        try:
            await redis.ping()
            checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "not_ready"
    status = "ready" if all(v == "ok" for v in checks.values()) else "not_ready"
    return ReadyResponse(status=status, checks=checks)


@router.get("/live")
async def live():
    return {"status": "alive"}
