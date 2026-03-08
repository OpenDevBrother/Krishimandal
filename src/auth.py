"""
KrishiMandal — Simple API key authentication and rate limiting.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, List, Tuple

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from src.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(request: Request, api_key: str = Security(api_key_header)):
    """FastAPI dependency: verify API key if auth is enabled."""
    if not settings.API_KEY_ENABLED:
        return "anonymous"

    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key. Provide X-API-Key header.")

    valid_keys = [k.strip() for k in settings.API_KEYS.split(",") if k.strip()]
    if api_key not in valid_keys:
        raise HTTPException(status_code=401, detail="Invalid API key.")

    # Rate limiting
    _check_rate_limit(api_key)
    return api_key


# ── In-memory sliding window rate limiter ────────────────────────────────────

_request_log: Dict[str, List[float]] = defaultdict(list)


def _check_rate_limit(api_key: str):
    """Simple sliding window rate limiter."""
    now = time.time()
    window = 60.0  # 1 minute
    limit = settings.RATE_LIMIT_PER_MINUTE

    # Remove expired entries
    _request_log[api_key] = [t for t in _request_log[api_key] if now - t < window]

    if len(_request_log[api_key]) >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {limit} requests per minute.",
        )

    _request_log[api_key].append(now)
