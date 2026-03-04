"""
Error categorization for structured retry logic.

TransientError: retryable (network, 5xx, 429, blob I/O)
PermanentError: non-retryable (4xx, invalid data, missing resources)
"""
import logging

import httpx

LOG = logging.getLogger(__name__)


class TransientError(Exception):
    """Retryable error: network timeouts, 5xx, blob I/O failures."""
    pass


class PermanentError(Exception):
    """Non-retryable error: invalid image, 4xx API errors, missing data."""
    pass


def classify_and_raise(exc: Exception) -> None:
    """Wrap an exception as TransientError or PermanentError and raise it."""
    if isinstance(exc, (TransientError, PermanentError)):
        raise exc

    if isinstance(exc, httpx.TimeoutException):
        raise TransientError(str(exc)) from exc

    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if 400 <= status < 500 and status != 429:
            raise PermanentError(f"HTTP {status}: {exc}") from exc
        raise TransientError(f"HTTP {status}: {exc}") from exc

    if isinstance(exc, (ConnectionError, OSError)):
        raise TransientError(str(exc)) from exc

    if isinstance(exc, (ValueError, KeyError, TypeError)):
        raise PermanentError(str(exc)) from exc

    # Default to transient (safer — allows retry)
    raise TransientError(str(exc)) from exc
