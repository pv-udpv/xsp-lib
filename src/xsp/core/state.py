"""State backend abstraction for session and cache management."""

from typing import Any, Protocol


class StateBackend(Protocol):
    """
    State backend protocol.

    Provides key-value storage for session data, caching,
    and other stateful operations in ad serving workflows.
    """

    async def get(self, key: str) -> Any | None:
        """
        Get value for key.

        Args:
            key: Key to retrieve

        Returns:
            Value if exists, None otherwise
        """
        ...

    async def set(
        self,
        key: str,
        value: Any,
        *,
        ttl: float | None = None,
    ) -> None:
        """
        Set value for key.

        Args:
            key: Key to set
            value: Value to store
            ttl: Optional time-to-live in seconds
        """
        ...

    async def delete(self, key: str) -> None:
        """
        Delete key.

        Args:
            key: Key to delete
        """
        ...

    async def exists(self, key: str) -> bool:
        """
        Check if key exists.

        Args:
            key: Key to check

        Returns:
            True if key exists, False otherwise
        """
        ...

    async def close(self) -> None:
        """Release resources."""
        ...


class InMemoryStateBackend:
    """
    In-memory state backend.

    Simple implementation using a dictionary. Suitable for testing
    and single-process applications. Does not support TTL expiration.
    """

    def __init__(self) -> None:
        """Initialize in-memory state backend."""
        self._store: dict[str, Any] = {}

    async def get(self, key: str) -> Any | None:
        """Get value for key."""
        return self._store.get(key)

    async def set(
        self,
        key: str,
        value: Any,
        *,
        ttl: float | None = None,
    ) -> None:
        """
        Set value for key.

        Note: TTL is not supported in the in-memory backend.
        """
        self._store[key] = value

    async def delete(self, key: str) -> None:
        """Delete key."""
        self._store.pop(key, None)

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return key in self._store

    async def close(self) -> None:
        """Clear all data."""
        self._store.clear()


class RedisStateBackend:
    """
    Redis-based state backend.

    Production-ready backend with TTL support and distributed caching.
    Requires redis package: pip install redis[hiredis]
    """

    def __init__(self, redis_client: Any) -> None:
        """
        Initialize Redis state backend.

        Args:
            redis_client: Redis client instance (redis.asyncio.Redis)

        Example:
            ```python
            import redis.asyncio as redis
            client = await redis.from_url("redis://localhost")
            backend = RedisStateBackend(client)
            ```
        """
        self._client = redis_client

    async def get(self, key: str) -> Any | None:
        """Get value for key."""
        import pickle

        raw = await self._client.get(key)
        if raw is None:
            return None
        return pickle.loads(raw)

    async def set(
        self,
        key: str,
        value: Any,
        *,
        ttl: float | None = None,
    ) -> None:
        """Set value for key with optional TTL."""
        import pickle

        raw = pickle.dumps(value)
        if ttl is not None:
            await self._client.setex(key, int(ttl), raw)
        else:
            await self._client.set(key, raw)

    async def delete(self, key: str) -> None:
        """Delete key."""
        await self._client.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        result = await self._client.exists(key)
        return bool(result > 0)

    async def close(self) -> None:
        """Close Redis connection."""
        await self._client.close()
