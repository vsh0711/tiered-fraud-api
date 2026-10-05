from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_user
from app.config import Settings, get_settings
from app.core.security import (
    create_access_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_password,
)
from app.db.models import User
from app.db.repositories import (
    create_api_key,
    create_password_reset_token,
    create_user,
    get_password_reset_token,
    get_user_by_email,
    get_user_by_login,
    get_user_by_username,
    update_user_password,
    write_audit,
)
from app.db.session import get_db
from app.models.schemas import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.services.email import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["auth"])


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@router.post("/register", response_model=MessageResponse)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    username = body.username.strip()
    email = body.email.strip().lower()
    if await get_user_by_username(db, username):
        raise HTTPException(status_code=409, detail="Username already taken")
    if await get_user_by_email(db, email):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = await create_user(
        db,
        username=username,
        password_hash=hash_password(body.password),
        email=email,
        role="analyst",
    )
    await write_audit(db, user.username, "register", {"email": email})
    return MessageResponse(message="Account created. You can sign in now.")


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user = await get_user_by_login(db, body.username)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    token = create_access_token(user.username, settings)
    await write_audit(db, user.username, "login", {})
    return TokenResponse(access_token=token, expires_in_minutes=settings.jwt_expire_minutes)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    # Always return the same message to avoid account enumeration
    generic = MessageResponse(
        message="If that email is registered, a password reset link has been sent."
    )
    user = await get_user_by_email(db, body.email.strip().lower())
    if user is None or not user.is_active:
        return generic

    raw = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.password_reset_expire_minutes)
    await create_password_reset_token(
        db,
        user_id=user.id,
        token_hash=_hash_token(raw),
        expires_at=expires,
    )
    reset_url = f"{settings.frontend_base_url.rstrip('/')}/reset-password?token={raw}"
    try:
        send_password_reset_email(settings=settings, to_email=user.email, reset_url=reset_url)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Could not send reset email: {exc}") from exc
    await write_audit(db, user.username, "forgot_password", {"email": user.email})
    return generic


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    row = await get_password_reset_token(db, _hash_token(body.token))
    now = datetime.now(timezone.utc)
    if row is None or row.used_at is not None or row.expires_at < now:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    from sqlalchemy import select

    user = (await db.execute(select(User).where(User.id == row.user_id))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    await update_user_password(db, user, hash_password(body.new_password))
    row.used_at = now
    await db.commit()
    await write_audit(db, user.username, "password_reset", {})
    return MessageResponse(message="Password updated. You can sign in with your new password.")


@router.get("/me")
async def me(user: User = Depends(require_user)):
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": user.role,
    }


@router.post("/api-keys", response_model=ApiKeyCreateResponse)
async def create_key(
    body: ApiKeyCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    raw = generate_api_key()
    row = await create_api_key(db, name=body.name, key_prefix=raw[:8], key_hash=hash_api_key(raw))
    await write_audit(db, user.username, "api_key_created", {"name": body.name, "prefix": raw[:8]})
    return ApiKeyCreateResponse(
        id=row.id,
        name=row.name,
        api_key=raw,
        key_prefix=row.key_prefix,
        created_at=row.created_at,
    )
