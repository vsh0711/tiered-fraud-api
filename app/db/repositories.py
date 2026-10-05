from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Select, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApiKey, AuditLog, DriftSnapshot, Job, PasswordResetToken, ScoreEvent, User


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def get_user_by_login(db: AsyncSession, login: str) -> User | None:
    login = login.strip()
    if "@" in login:
        return await get_user_by_email(db, login)
    return await get_user_by_username(db, login)


async def create_user(
    db: AsyncSession,
    username: str,
    password_hash: str,
    email: str,
    role: str = "analyst",
) -> User:
    user = User(
        username=username,
        email=email.lower().strip(),
        password_hash=password_hash,
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_password(db: AsyncSession, user: User, password_hash: str) -> None:
    user.password_hash = password_hash
    await db.commit()


async def create_password_reset_token(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
) -> PasswordResetToken:
    row = PasswordResetToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_password_reset_token(db: AsyncSession, token_hash: str) -> PasswordResetToken | None:
    result = await db.execute(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    return result.scalar_one_or_none()


async def get_api_key_by_hash(db: AsyncSession, key_hash: str) -> ApiKey | None:
    result = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True)))
    return result.scalar_one_or_none()


async def create_api_key(
    db: AsyncSession, *, name: str, key_prefix: str, key_hash: str
) -> ApiKey:
    row = ApiKey(name=name, key_prefix=key_prefix, key_hash=key_hash)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def touch_api_key(db: AsyncSession, api_key: ApiKey) -> None:
    api_key.last_used_at = datetime.now(timezone.utc)
    await db.commit()


async def save_score_event(db: AsyncSession, event: ScoreEvent) -> ScoreEvent:
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def list_score_events(
    db: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
    decision: str | None = None,
    routing_mode: str | None = None,
    country: str | None = None,
) -> tuple[list[ScoreEvent], int]:
    filters = []
    if decision:
        filters.append(ScoreEvent.decision == decision)
    if routing_mode:
        filters.append(ScoreEvent.routing_mode == routing_mode)
    if country:
        filters.append(ScoreEvent.country == country.upper())

    count_q = select(func.count()).select_from(ScoreEvent)
    list_q: Select = select(ScoreEvent).order_by(desc(ScoreEvent.created_at)).limit(limit).offset(offset)
    for f in filters:
        count_q = count_q.where(f)
        list_q = list_q.where(f)

    total = int((await db.execute(count_q)).scalar_one())
    rows = list((await db.execute(list_q)).scalars().all())
    return rows, total


async def score_stats(db: AsyncSession) -> dict:
    total = int((await db.execute(select(func.count()).select_from(ScoreEvent))).scalar_one())
    by_mode = await db.execute(
        select(ScoreEvent.routing_mode, func.count()).group_by(ScoreEvent.routing_mode)
    )
    by_decision = await db.execute(
        select(ScoreEvent.decision, func.count()).group_by(ScoreEvent.decision)
    )
    by_tier = await db.execute(
        select(ScoreEvent.routing_mode, ScoreEvent.last_tier, func.count()).group_by(
            ScoreEvent.routing_mode, ScoreEvent.last_tier
        )
    )
    latency = await db.execute(
        select(
            ScoreEvent.routing_mode,
            func.avg(ScoreEvent.cumulative_latency_ms),
        ).group_by(ScoreEvent.routing_mode)
    )
    return {
        "requests_total": total,
        "by_mode": {m: c for m, c in by_mode.all()},
        "by_decision": {d: c for d, c in by_decision.all()},
        "by_tier_stop": {f"{m}:{t}": c for m, t, c in by_tier.all()},
        "latency_ms_avg": {m: round(float(v or 0), 3) for m, v in latency.all()},
    }


async def write_audit(db: AsyncSession, actor: str, action: str, detail: dict | None = None) -> None:
    db.add(AuditLog(actor=actor, action=action, detail=detail or {}))
    await db.commit()


async def create_job(db: AsyncSession, job_type: str, payload: dict) -> Job:
    job = Job(job_type=job_type, payload=payload, status="queued")
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job(db: AsyncSession, job_id: uuid.UUID) -> Job | None:
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def list_jobs(db: AsyncSession, limit: int = 30) -> list[Job]:
    result = await db.execute(select(Job).order_by(desc(Job.created_at)).limit(limit))
    return list(result.scalars().all())


async def update_job(db: AsyncSession, job: Job, **kwargs) -> Job:
    for k, v in kwargs.items():
        setattr(job, k, v)
    await db.commit()
    await db.refresh(job)
    return job


async def save_drift_snapshot(db: AsyncSession, snap: DriftSnapshot) -> DriftSnapshot:
    db.add(snap)
    await db.commit()
    await db.refresh(snap)
    return snap


async def list_drift_snapshots(db: AsyncSession, limit: int = 20) -> list[DriftSnapshot]:
    result = await db.execute(select(DriftSnapshot).order_by(desc(DriftSnapshot.created_at)).limit(limit))
    return list(result.scalars().all())
