"""Unified TTL cache for API endpoints."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TTLCache:
    """Simple in-memory cache with TTL expiration.

    Thread-safe for sync contexts. For async contexts, use get_or_set_async.
    """

    def __init__(self, ttl: int = 3600, name: str = "cache"):
        self._data: dict[str, Any] = {}
        self._timestamps: dict[str, float] = {}
        self._ttl = ttl
        self._name = name
        self._lock = asyncio.Lock()

    def get(self, key: str = "default") -> Any | None:
        """Get cached value if not expired."""
        ts = self._timestamps.get(key, 0)
        if time.time() - ts > self._ttl:
            return None
        return self._data.get(key)

    def set(self, value: Any, key: str = "default") -> None:
        """Set a cached value."""
        self._data[key] = value
        self._timestamps[key] = time.time()

    def invalidate(self, key: str = "default") -> None:
        """Remove a cached entry."""
        self._data.pop(key, None)
        self._timestamps.pop(key, None)

    def get_or_set(self, key: str, factory: Callable[[], T], ttl: int | None = None) -> T:
        """Get cached value or compute it via factory function (sync)."""
        effective_ttl = ttl if ttl is not None else self._ttl
        ts = self._timestamps.get(key, 0)
        if time.time() - ts <= effective_ttl and key in self._data:
            return self._data[key]
        value = factory()
        self._data[key] = value
        self._timestamps[key] = time.time()
        return value

    async def get_or_set_async(
        self, key: str, factory: Callable[[], T], ttl: int | None = None
    ) -> T:
        """Async version with lock to prevent thundering herd."""
        effective_ttl = ttl if ttl is not None else self._ttl
        # Check without lock first (fast path)
        ts = self._timestamps.get(key, 0)
        if time.time() - ts <= effective_ttl and key in self._data:
            return self._data[key]
        # Acquire lock for computation
        async with self._lock:
            # Double-check after acquiring lock
            ts = self._timestamps.get(key, 0)
            if time.time() - ts <= effective_ttl and key in self._data:
                return self._data[key]
            value = factory()
            self._data[key] = value
            self._timestamps[key] = time.time()
            return value
