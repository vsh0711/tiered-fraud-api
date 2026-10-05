from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.api.v1.router import api_router
from app.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import RateLimitMiddleware, RequestIdMiddleware
from app.db.session import async_session_factory, engine, init_db
from app.services.bootstrap import ensure_bootstrap_data
from app.services.thresholds import apply_trained_thresholds
from ml.inference import get_engine, reset_engine

# Backward-compatible aliases
from app.api.v1 import health as health_routes
from app.api.v1 import score as score_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = apply_trained_thresholds(get_settings())
    await init_db()
    await ensure_bootstrap_data(settings)

    reset_engine()
    engine_ml = get_engine(settings.models_dir)
    if not engine_ml.ready and (settings.models_dir / "tier1.joblib").exists():
        engine_ml.load()


    redis: Redis | None = None
    try:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        await redis.ping()
    except Exception:
        redis = None

    app.state.settings = settings
    app.state.engine = engine_ml
    app.state.redis = redis
    app.state.session_factory = async_session_factory
    yield
    if redis is not None:
        await redis.aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        description=(
            "Enterprise-style tiered fraud scoring with OR routing, Postgres persistence, "
            "API keys, JWT dashboard auth, Redis jobs, and drift monitoring."
        ),
        openapi_tags=[
            {"name": "health", "description": "Liveness/readiness"},
            {"name": "auth", "description": "Dashboard login and API key management"},
            {"name": "score", "description": "Transaction scoring"},
            {"name": "history", "description": "Persisted decision history"},
            {"name": "jobs", "description": "Async batch / drift jobs"},
            {"name": "drift", "description": "Concept drift monitoring"},
            {"name": "eval", "description": "Holdout capture / decision-mix reports"},
            {"name": "metrics", "description": "Prometheus and JSON metrics"},
        ],
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIdMiddleware)

    app.include_router(api_router)
    # Legacy unversioned routes for existing scripts / demos
    app.include_router(health_routes.router)
    app.include_router(score_routes.router)
    return app


app = create_app()
