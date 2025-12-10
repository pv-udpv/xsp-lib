"""VAST cache layer with TTL and LRU eviction."""

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


@dataclass
class VastCacheConfig:
    """Configuration for VAST cache."""

    max_size: int = 1000
    default_ttl_seconds: float = 300.0
    cleanup_interval_seconds: float = 60.0
    enable_stats: bool = True


@dataclass
class CacheStats:
    """Cache statistics."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


@dataclass
class CacheEntry:
    """Cache entry with TTL."""

    value: Any
    expires_at: float
    size_bytes: int = 0


class VastCacheLayer:
    """Thread-safe TTL-based cache with LRU eviction."""

    def __init__(self, config: VastCacheConfig | None = None):
        """Initialize cache layer."""
        self.config = config or VastCacheConfig()
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        self._stats = CacheStats()
        self._cleanup_task: asyncio.Task | None = None
        self.logger = logging.getLogger(__name__)

    async def start(self) -> None:
        """Start background cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    def generate_key(self, *args: Any, **kwargs: Any) -> str:
        """Generate deterministic cache key from arguments."""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()

    async def get(self, key: str) -> Any | None:
        """Get value from cache if not expired."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                if self.config.enable_stats:
                    self._stats.misses += 1
                return None

            # Check expiration
            if time.time() > entry.expires_at:
                del self._cache[key]
                if self.config.enable_stats:
                    self._stats.misses += 1
                    self._stats.size = len(self._cache)
                return None

            # Move to end (LRU)
            self._cache.move_to_end(key)

            if self.config.enable_stats:
                self._stats.hits += 1

            return entry.value

    async def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        """Set value in cache with TTL."""
        async with self._lock:
            ttl = ttl_seconds if ttl_seconds is not None else self.config.default_ttl_seconds
            expires_at = time.time() + ttl

            # Estimate size
            size_bytes = len(str(value))

            entry = CacheEntry(value=value, expires_at=expires_at, size_bytes=size_bytes)

            # Add/update entry
            self._cache[key] = entry
            self._cache.move_to_end(key)

            # Evict if over size limit
            while len(self._cache) > self.config.max_size:
                evicted_key = next(iter(self._cache))
                del self._cache[evicted_key]
                if self.config.enable_stats:
                    self._stats.evictions += 1

            if self.config.enable_stats:
                self._stats.size = len(self._cache)

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            if self.config.enable_stats:
                self._stats.size = 0

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self._stats

    async def _cleanup_loop(self) -> None:
        """Background task to cleanup expired entries."""
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval_seconds)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cache cleanup error: {e}")

    async def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        async with self._lock:
            now = time.time()
            expired_keys = [key for key, entry in self._cache.items() if now > entry.expires_at]
            for key in expired_keys:
                del self._cache[key]
            if self.config.enable_stats:
                self._stats.size = len(self._cache)
