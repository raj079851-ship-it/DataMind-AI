# -*- coding: utf-8 -*-
"""
Rate Limiter Module
- Sliding-window in-memory rate limiter per IP or API key
- Protects authentication endpoints against brute force and API abuse
- Returns remaining allowances and retry-after periods
"""

import time
from collections import defaultdict
from typing import Dict, List, Tuple, Optional


class RateLimitResult:
    """Result object supporting both boolean tests and tuple unpacking."""
    def __init__(self, allowed: bool, remaining: int, retry_after: int):
        self.allowed = bool(allowed)
        self.remaining = int(remaining)
        self.retry_after = int(retry_after)

    def __bool__(self) -> bool:
        return self.allowed

    def __iter__(self):
        return iter((self.allowed, self.remaining, self.retry_after))

    def __getitem__(self, index):
        return (self.allowed, self.remaining, self.retry_after)[index]

    def __repr__(self) -> str:
        return f"RateLimitResult(allowed={self.allowed}, remaining={self.remaining}, retry_after={self.retry_after})"


class RateLimiter:
    """Sliding-window rate limiter."""

    def __init__(
        self,
        default_limit: int = 60,
        default_window: int = 60,
        max_requests: Optional[int] = None,
        window_seconds: Optional[int] = None
    ):
        self.default_limit = max_requests if max_requests is not None else default_limit
        self.default_window = window_seconds if window_seconds is not None else default_window
        # Map key -> list of timestamps
        self.history: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(
        self,
        key: str,
        limit: Optional[int] = None,
        window_seconds: Optional[int] = None
    ) -> RateLimitResult:
        """
        Evaluates whether a request with 'key' is allowed within the window.
        Returns: RateLimitResult(allowed, remaining, retry_after)
        """
        lim = limit or self.default_limit
        win = window_seconds or self.default_window
        now = time.time()
        cutoff = now - win

        # Filter out timestamps older than cutoff
        recent = [t for t in self.history[key] if t > cutoff]
        self.history[key] = recent

        if len(recent) >= lim:
            earliest = recent[0]
            retry_after = max(1, int(earliest + win - now))
            return RateLimitResult(False, 0, retry_after)

        self.history[key].append(now)
        remaining = max(0, lim - len(self.history[key]))
        return RateLimitResult(True, remaining, 0)

    def reset(self, key: Optional[str] = None):
        """Resets rate limit counter for a specific key or all keys."""
        if key:
            self.history.pop(key, None)
        else:
            self.history.clear()


# Global singleton instances
default_api_rate_limiter = RateLimiter(default_limit=120, default_window=60)
auth_rate_limiter = RateLimiter(default_limit=10, default_window=60)  # Strict for auth
