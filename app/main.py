from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from app.config import get_settings
from app.metrics_store import json_summary, prometheus_metrics
from app.routers import health, score
from ml.inference import get_engine

logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":%(message)s}',
    stream=sys.stdout,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine = get_engine(settings.models_dir)
    if not engine.ready and (settings.models_dir / "tier1.joblib").exists():
        engine.load()
    app.state.settings = settings
    app.state.engine = engine
    yield


app = FastAPI(title="Tiered Fraud Scoring API", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(score.router)


@app.get("/metrics")
async def metrics(request: Request):
    if request.headers.get("accept") == "application/json":
        return json_summary()
    body, ctype = prometheus_metrics()
    return PlainTextResponse(content=body.decode(), media_type=ctype)
