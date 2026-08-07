"""Redis-backed rate limiting for paid AI interview endpoints."""

import hashlib

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings


def api_key_bucket(request: Request) -> str:
    """Return a non-sensitive, stable limiter identity for an API key."""
    api_key = request.headers.get("X-API-Key", "")
    if not api_key:
        client_host = request.client.host if request.client else "unknown"
        api_key = f"missing:{client_host}"
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


limiter = Limiter(
    key_func=api_key_bucket,
    storage_uri=settings.REDIS_URL,
    headers_enabled=True,
    in_memory_fallback_enabled=False,
    swallow_errors=False,
    key_prefix="gigbridge-ai",
)


def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Return the service's standard envelope without leaking limiter internals."""
    default_response = _rate_limit_exceeded_handler(request, exc)
    limiter_headers = {
        key: value
        for key, value in default_response.headers.items()
        if key.lower() not in {"content-length", "content-type"}
    }
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "message": "Rate limit exceeded",
            "data": None,
            "errors": [],
        },
        headers=limiter_headers,
    )
