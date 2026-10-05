"""Redis list worker for batch_score and drift_scan jobs."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

from redis.asyncio import Redis
from redis.exceptions import TimeoutError as RedisTimeoutError

from app.config import get_settings
from app.core.logging import configure_logging
from app.db.repositories import get_job
from app.db.session import async_session_factory, init_db
from app.services.bootstrap import ensure_bootstrap_data
from app.services.jobs import QUEUE_KEY, process_job
from ml.inference import get_engine

logger = logging.getLogger("fraud_worker")


async def run_worker() -> None:
    configure_logging()
    settings = get_settings()
    await init_db()
    await ensure_bootstrap_data(settings)
    engine = get_engine(settings.models_dir)
    if not engine.ready and (settings.models_dir / "tier1.joblib").exists():
        engine.load()

    # socket_timeout must be None (or > block timeout) for BRPOP
    redis = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=None,
    )
    logger.info('{"event":"worker_started","queue":"%s"}', QUEUE_KEY)
    while True:
        try:
            item = await redis.brpop(QUEUE_KEY, timeout=5)
        except (asyncio.TimeoutError, RedisTimeoutError, TimeoutError):
            continue
        if item is None:
            continue
        _, payload = item
        try:
            data = json.loads(payload)
            job_id = uuid.UUID(data["job_id"])
        except Exception:
            logger.exception("invalid_queue_payload")
            continue
        async with async_session_factory() as db:
            job = await get_job(db, job_id)
            if job is None:
                continue
            await process_job(db, job, engine=engine, settings=settings)
            logger.info('{"event":"job_done","id":"%s","status":"%s"}', job.id, job.status)


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
