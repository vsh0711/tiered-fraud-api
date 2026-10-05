from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.security import decode_access_token, hash_api_key
from app.db.models import ApiKey, User
from app.db.repositories import get_api_key_by_hash, get_user_by_username, touch_api_key
from app.db.session import get_db
from ml.inference import InferenceEngine, get_engine

bearer_scheme = HTTPBearer(auto_error=False)


async def get_engine_dep(settings: Settings = Depends(get_settings)) -> InferenceEngine:
    eng = get_engine(settings.models_dir)
    if not eng.ready:
        raise HTTPException(status_code=503, detail="Models not loaded; run scripts/train_models.py")
    return eng


async def require_api_key(
    db: AsyncSession = Depends(get_db),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> ApiKey:
    raw = x_api_key or settings.demo_api_key
    if not raw:
        raise HTTPException(status_code=401, detail="Missing X-API-Key")
    row = await get_api_key_by_hash(db, hash_api_key(raw))
    if row is None:
        # Bootstrap race: accept configured demo key hash mismatch after seed
        if raw == settings.demo_api_key:
            raise HTTPException(status_code=401, detail="Demo API key not bootstrapped yet")
        raise HTTPException(status_code=401, detail="Invalid API key")
    await touch_api_key(db, row)
    return row


async def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    username = decode_access_token(credentials.credentials, settings)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = await get_user_by_username(db, username)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")
    return user
