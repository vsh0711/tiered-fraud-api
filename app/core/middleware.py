from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{(time.perf_counter() - started) * 1000:.2f}"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis sliding-window rate limit; fails open if Redis is unavailable."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in {"/health", "/ready", "/live", "/metrics", "/docs", "/openapi.json", "/redoc"}:
            return await call_next(request)
        if request.url.path.startswith("/v1/health") or request.url.path.startswith("/v1/ready"):
            return await call_next(request)

        settings = get_settings()
        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            return await call_next(request)

        identity = (
            request.headers.get("X-API-Key")
            or request.client.host
            if request.client
            else "anonymous"
        )
        key = f"rl:{identity}:{int(time.time() // 60)}"
        try:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, 70)
            if count > settings.rate_limit_per_minute:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded", "limit": settings.rate_limit_per_minute},
                )
        except Exception:
            pass
        return await call_next(request)
