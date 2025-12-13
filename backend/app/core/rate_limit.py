"""Simple Redis-based rate limiter for auth endpoints."""

from typing import Callable

from fastapi import HTTPException, Request, status
from redis import Redis

from app.core.config import settings

_redis: Redis | None = None


def _get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


def rate_limit(
    max_requests: int = 10,
    window_seconds: int = 60,
    key_func: Callable[[Request], str] | None = None,
):
    """
    Rate limit dependency factory.

    Usage:
        @router.post("/login", dependencies=[Depends(rate_limit(max_requests=5, window_seconds=60))])

    Args:
        max_requests: Maximum requests allowed in the window.
        window_seconds: Window size in seconds.
        key_func: Optional function to extract a key from the request.
                  Defaults to client IP + path.
    """

    async def _rate_limit_dep(request: Request) -> None:
        if key_func:
            identifier = key_func(request)
        else:
            client_ip = request.client.host if request.client else "unknown"
            identifier = f"{client_ip}:{request.url.path}"

        redis_key = f"rate_limit:{identifier}"

        try:
            r = _get_redis()
            current = r.get(redis_key)

            if current is not None and int(current) >= max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Try again in {window_seconds} seconds.",
                )

            pipe = r.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, window_seconds)
            pipe.execute()
        except HTTPException:
            raise
        except Exception:
            # If Redis is down, allow the request through
            pass

    return _rate_limit_dep
