"""
Sliding-window rate limiter with Redis backend and in-memory fallback.

Uses Redis when REDIS_URL is set (works across multiple replicas).
Falls back to in-memory dict when Redis is unavailable.
"""
import logging
import os
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

LOG = logging.getLogger(__name__)

# Config: max requests per window
RATE_LIMIT = 60  # requests
WINDOW_SECONDS = 60  # per minute

# ── Redis backend ──

_redis_client = None
_redis_checked = False


def _get_redis():
    """Lazy-init Redis connection. Returns None if unavailable."""
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True

    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        LOG.info("REDIS_URL not set — rate limiter using in-memory backend")
        return None

    try:
        import redis
        _redis_client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
        _redis_client.ping()
        LOG.info("Rate limiter connected to Redis")
    except Exception as exc:
        LOG.warning("Redis unavailable, falling back to in-memory rate limiter: %s", exc)
        _redis_client = None

    return _redis_client


def _check_redis(key: str, limit: int) -> bool:
    """Check rate limit via Redis sorted set. Returns True if allowed."""
    r = _get_redis()
    if r is None:
        return None  # signal to use fallback

    now = time.time()
    redis_key = f"rl:{key}"
    cutoff = now - WINDOW_SECONDS

    try:
        pipe = r.pipeline()
        pipe.zremrangebyscore(redis_key, 0, cutoff)
        pipe.zcard(redis_key)
        pipe.zadd(redis_key, {str(now): now})
        pipe.expire(redis_key, WINDOW_SECONDS + 1)
        results = pipe.execute()

        count = results[1]  # zcard result (before adding current request)
        if count >= limit:
            # Remove the entry we just added
            r.zrem(redis_key, str(now))
            return False
        return True
    except Exception as exc:
        LOG.warning("Redis error in rate limiter, falling back: %s", exc)
        return None  # fallback to in-memory


# ── In-memory fallback ──

_requests: dict[str, list[float]] = defaultdict(list)


def _cleanup(key: str, now: float) -> None:
    """Remove timestamps outside the current window."""
    cutoff = now - WINDOW_SECONDS
    entries = _requests[key]
    i = 0
    while i < len(entries) and entries[i] < cutoff:
        i += 1
    if i:
        _requests[key] = entries[i:]


def _check_memory(key: str, limit: int) -> bool:
    """Check rate limit via in-memory dict. Returns True if allowed."""
    now = time.monotonic()
    _cleanup(key, now)

    if len(_requests[key]) >= limit:
        return False

    _requests[key].append(now)
    return True


# ── Public API ──

def check_rate_limit(user_id: str, limit: int = RATE_LIMIT) -> None:
    """Raise 429 if user exceeds rate limit."""
    key = user_id

    result = _check_redis(key, limit)
    if result is None:
        result = _check_memory(key, limit)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Max {limit} requests per {WINDOW_SECONDS}s.",
            headers={"Retry-After": str(WINDOW_SECONDS)},
        )


def check_ip_rate_limit(request: Request, limit: int = 30) -> None:
    """Rate limit by IP for unauthenticated/public endpoints."""
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"ip:{client_ip}", limit=limit)
