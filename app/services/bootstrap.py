from __future__ import annotations

import logging

from sqlalchemy import select

from app.config import Settings
from app.core.security import generate_api_key, hash_api_key, hash_password
from app.db.models import ApiKey, User
from app.db.repositories import create_api_key, create_user
from app.db.session import async_session_factory

logger = logging.getLogger("fraud_api.bootstrap")


async def ensure_bootstrap_data(settings: Settings) -> None:
    async with async_session_factory() as db:
        if settings.bootstrap_admin and settings.admin_username and settings.admin_password:
            user = (
                await db.execute(select(User).where(User.username == settings.admin_username))
            ).scalar_one_or_none()
            if user is None:
                email = settings.admin_email or f"{settings.admin_username}@localhost.local"
                await create_user(
                    db,
                    settings.admin_username,
                    hash_password(settings.admin_password),
                    email=email,
                    role="admin",
                )
                logger.info(
                    '{"event":"bootstrap_admin_created","username":"%s"}',
                    settings.admin_username,
                )

        existing = (
            await db.execute(select(ApiKey).where(ApiKey.key_hash == hash_api_key(settings.demo_api_key)))
        ).scalar_one_or_none()
        if existing is None and settings.demo_api_key:
            raw = settings.demo_api_key or generate_api_key()
            await create_api_key(
                db,
                name="service-default",
                key_prefix=raw[:8],
                key_hash=hash_api_key(raw),
            )
            logger.info('{"event":"bootstrap_api_key_ready","prefix":"%s"}', raw[:8])
