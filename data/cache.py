"""TTL cache for market data to eliminate redundant yfinance calls."""

import time
import logging
from typing import Any, Optional

logger = logging.getLogger("stock_agent")


class TTLCache:
    """Simple in-memory TTL cache. Thread-safe enough for single-process use."""

    def __init__(self, ttl_seconds: int = 300):
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if time.time() - ts > self._ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.time(), value)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    @property
    def size(self) -> int:
        return len(self._store)


# Module-level singleton
_cache = TTLCache()


def get_cache(ttl_seconds: int = 300) -> TTLCache:
    """Return the global cache instance, reconfiguring TTL if needed."""
    global _cache
    if _cache._ttl != ttl_seconds:
        _cache = TTLCache(ttl_seconds)
    return _cache
