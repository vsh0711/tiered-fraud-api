from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_user
from app.db.models import User
from app.db.repositories import get_job, list_jobs
from app.db.session import get_db
from app.models.schemas import JobCreateRequest, JobOut
from app.services.jobs import enqueue_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobOut)
async def create_job_endpoint(
    body: JobCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    if body.job_type not in {"batch_score", "drift_scan"}:
        raise HTTPException(status_code=400, detail="job_type must be batch_score or drift_scan")
    redis = getattr(request.app.state, "redis", None)
    job = await enqueue_job(db, redis, body.job_type, body.payload)
    return job


@router.get("", response_model=list[JobOut])
async def jobs_list(db: AsyncSession = Depends(get_db), _: User = Depends(require_user)):
    return await list_jobs(db)


@router.get("/{job_id}", response_model=JobOut)
async def job_detail(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_user),
):
    job = await get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
