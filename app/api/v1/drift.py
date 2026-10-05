from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_user
from app.db.models import User
from app.db.repositories import list_drift_snapshots, save_drift_snapshot
from app.db.session import get_db
from app.models.schemas import DriftRunRequest, DriftSnapshotOut, JobOut
from app.services.drift import compute_drift_snapshot
from app.services.jobs import enqueue_job

router = APIRouter(prefix="/drift", tags=["drift"])


@router.get("/snapshots", response_model=list[DriftSnapshotOut])
async def snapshots(db: AsyncSession = Depends(get_db), _: User = Depends(require_user)):
    return await list_drift_snapshots(db)


@router.post("/run", response_model=DriftSnapshotOut)
async def run_drift_sync(
    body: DriftRunRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_user),
):
    snap = compute_drift_snapshot(n_samples=body.n_samples, drift_strength=body.drift_strength)
    return await save_drift_snapshot(db, snap)


@router.post("/enqueue", response_model=JobOut)
async def enqueue_drift(
    body: DriftRunRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_user),
):
    redis = getattr(request.app.state, "redis", None)
    return await enqueue_job(
        db,
        redis,
        "drift_scan",
        {"n_samples": body.n_samples, "drift_strength": body.drift_strength},
    )
