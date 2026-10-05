from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_user
from app.db.models import User
from app.db.repositories import score_stats
from app.db.session import get_db
from app.metrics_store import json_summary, prometheus_metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def metrics(request: Request, db: AsyncSession = Depends(get_db)):
    if request.headers.get("accept") == "application/json":
        memory = json_summary()
        try:
            persisted = await score_stats(db)
            memory["persisted"] = persisted
        except Exception:
            memory["persisted"] = None
        return memory
    body, ctype = prometheus_metrics()
    return PlainTextResponse(content=body.decode(), media_type=ctype)


@router.get("/metrics/dashboard")
async def dashboard_metrics(db: AsyncSession = Depends(get_db), _: User = Depends(require_user)):
    persisted = await score_stats(db)
    memory = json_summary()
    return {"persisted": persisted, "process": memory}
