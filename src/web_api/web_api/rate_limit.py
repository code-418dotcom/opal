"""
Simple in-memory sliding-window rate limiter.
Keyed per user_id, resets on container restart (acceptable for abuse prevention).
"""
import time
from collections import defaultdict
from fastapi import HTTPException, Request, status

# Config: max requests per window
RATE_LIMIT = 60  # requests
WINDOW_SECONDS = 60  # per minute

# {user_key: [timestamp, timestamp, ...]}
_requests: dict[str, list[float]] = defaultdict(list)


def _cleanup(key: str, now: float) -> None:
    """Remove timestamps outside the current window."""
    cutoff = now - WINDOW_SECONDS
    entries = _requests[key]
    # Find first entry within window (list is sorted)
    i = 0
    while i < len(entries) and entries[i] < cutoff:
        i += 1
    if i:
        _requests[key] = entries[i:]


def check_rate_limit(user_id: str) -> None:
    """Raise 429 if user exceeds rate limit."""
    now = time.monotonic()
    key = user_id

    _cleanup(key, now)

    if len(_requests[key]) >= RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Max {RATE_LIMIT} requests per {WINDOW_SECONDS}s.",
            headers={"Retry-After": str(WINDOW_SECONDS)},
        )

    _requests[key].append(now)
