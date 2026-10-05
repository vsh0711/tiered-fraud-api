from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Job
from app.db.repositories import create_job, update_job
from app.models.schemas import RoutingMode, TransactionRequest
from app.services.drift import compute_drift_snapshot
from app.services.scoring import score_and_persist
from app.config import Settings
from app.db.repositories import save_drift_snapshot
from ml.inference import InferenceEngine
from sim.generator import GeneratorConfig, generate_transactions, row_to_request_dict

logger = logging.getLogger("fraud_api.jobs")
QUEUE_KEY = "fraud:jobs"


async def enqueue_job(db: AsyncSession, redis: Redis | None, job_type: str, payload: dict) -> Job:
    job = await create_job(db, job_type, payload)
    if redis is not None:
        await redis.lpush(QUEUE_KEY, json.dumps({"job_id": str(job.id)}))
    return job


async def process_job(
    db: AsyncSession,
    job: Job,
    *,
    engine: InferenceEngine,
    settings: Settings,
) -> Job:
    await update_job(db, job, status="running", started_at=datetime.now(timezone.utc), error=None)
    try:
        if job.job_type == "batch_score":
            result = await _run_batch_score(db, job.payload, engine=engine, settings=settings)
        elif job.job_type == "drift_scan":
            snap = compute_drift_snapshot(
                n_samples=int(job.payload.get("n_samples", 2000)),
                drift_strength=float(job.payload.get("drift_strength", 0.35)),
            )
            saved = await save_drift_snapshot(db, snap)
            result = {
                "snapshot_id": str(saved.id),
                "alert": saved.alert,
                "summary": saved.summary,
                "psi_by_feature": saved.psi_by_feature,
            }
        else:
            raise ValueError(f"Unknown job_type: {job.job_type}")

        return await update_job(
            db,
            job,
            status="succeeded",
            result=result,
            finished_at=datetime.now(timezone.utc),
        )
    except Exception as exc:
        logger.exception("job_failed id=%s", job.id)
        return await update_job(
            db,
            job,
            status="failed",
            error=str(exc),
            finished_at=datetime.now(timezone.utc),
        )


async def _run_batch_score(
    db: AsyncSession,
    payload: dict,
    *,
    engine: InferenceEngine,
    settings: Settings,
) -> dict:
    n = int(payload.get("n_samples", 50))
    mode = RoutingMode(payload.get("routing_mode", "optimized"))
    df = generate_transactions(GeneratorConfig(n_samples=n, seed=int(payload.get("seed", 42))))
    scored = 0
    decisions: dict[str, int] = {}
    for i, row in df.iterrows():
        body = TransactionRequest(**row_to_request_dict(row, request_id=f"batch_{uuid.uuid4().hex[:10]}"))
        resp = await score_and_persist(body=body, mode=mode, engine=engine, settings=settings, db=db)
        scored += 1
        decisions[resp.decision.value] = decisions.get(resp.decision.value, 0) + 1
    return {"scored": scored, "decisions": decisions, "routing_mode": mode.value}
