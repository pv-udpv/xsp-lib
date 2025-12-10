"""Frequency capping middleware for ad delivery control.

Implements frequency capping to control how often ads are shown to users,
following IAB best practices for user experience and campaign effectiveness.

References:
    - IAB Quality Assurance Guidelines (QAG): Frequency capping recommendations
    - IAB Digital Video Ad Serving Template (VAST): Best practices for ad limits
    - OpenRTB: Frequency cap signaling in bid requests
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Protocol

from xsp.core.exceptions import FrequencyCapExceeded
from xsp.core.session import SessionContext
from xsp.core.upstream import Upstream
from xsp.middleware.base import FetchFunc


@dataclass(frozen=True)
class FrequencyCap:
    """
    Frequency cap rule definition.

    Defines limits on how often an ad can be shown to a user within
    a specific time window. Supports both per-user and per-campaign
    frequency capping.

    Attributes:
        max_impressions: Maximum number of impressions allowed
        time_window_seconds: Time window in seconds for the cap
        per_campaign: If True, apply cap per campaign_id; if False, apply globally

    Example:
        >>> # Limit to 3 impressions per user per hour
        >>> cap = FrequencyCap(
        ...     max_impressions=3,
        ...     time_window_seconds=3600,
        ...     per_campaign=False
        ... )
        >>>
        >>> # Limit to 5 impressions per campaign per day
        >>> campaign_cap = FrequencyCap(
        ...     max_impressions=5,
        ...     time_window_seconds=86400,
        ...     per_campaign=True
        ... )

    Note:
        Per IAB QAG recommendations, typical frequency caps range from
        3-10 impressions per 24-hour period to balance reach and user experience.
    """

    max_impressions: int
    time_window_seconds: int
    per_campaign: bool = False


class FrequencyStore(Protocol):
    """
    Protocol for frequency cap storage backend.

    Defines the interface for storing and retrieving frequency cap
    counters. Implementations must be thread-safe for concurrent access.

    Methods:
        get_count: Retrieve current impression count for a key
        increment: Increment impression count for a key
        reset: Reset impression count for a key

    Thread Safety:
        All methods must be thread-safe and support concurrent async access.
        Consider using asyncio.Lock or other synchronization primitives.

    Example Implementation:
        >>> class RedisFrequencyStore:
        ...     async def get_count(self, key: str) -> int:
        ...         return int(await self.redis.get(key) or 0)
        ...
        ...     async def increment(self, key: str, ttl: int) -> int:
        ...         pipe = self.redis.pipeline()
        ...         pipe.incr(key)
        ...         pipe.expire(key, ttl)
        ...         results = await pipe.execute()
        ...         return results[0]
        ...
        ...     async def reset(self, key: str) -> None:
        ...         await self.redis.delete(key)
    """

    async def get_count(self, key: str) -> int:
        """
        Get current impression count for key.

        Args:
            key: Storage key (e.g., "user:123" or "user:123:campaign:456")

        Returns:
            Current impression count (0 if key doesn't exist)
        """
        ...

    async def increment(self, key: str, ttl: int) -> int:
        """
        Increment impression count and set TTL.

        Args:
            key: Storage key
            ttl: Time-to-live in seconds for the counter

        Returns:
            New impression count after increment
        """
        ...

    async def reset(self, key: str) -> None:
        """
        Reset impression count for key.

        Args:
            key: Storage key to reset
        """
        ...


class InMemoryFrequencyStore:
    """
    In-memory frequency cap storage using dict and asyncio.Lock.

    Simple thread-safe implementation suitable for single-instance
    deployments and testing. For production distributed systems,
    use Redis or similar external storage.

    Storage Format:
        {
            "key": {
                "count": int,
                "expires_at": float  # Unix timestamp
            }
        }

    Thread Safety:
        All operations are protected by asyncio.Lock to ensure thread-safe
        concurrent access. Multiple coroutines can safely share an instance.

    Example:
        >>> store = InMemoryFrequencyStore()
        >>> count = await store.increment("user:123", ttl=3600)
        >>> count
        1
        >>> count = await store.increment("user:123", ttl=3600)
        >>> count
        2
        >>> current = await store.get_count("user:123")
        >>> current
        2
        >>> await store.reset("user:123")
        >>> await store.get_count("user:123")
        0

    Warning:
        Data is not persisted and will be lost on process restart.
        Not suitable for distributed deployments where multiple
        instances need to share frequency cap state.
    """

    def __init__(self) -> None:
        """Initialize in-memory store with empty state."""
        self._store: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get_count(self, key: str) -> int:
        """
        Get current impression count for key.

        Automatically expires stale entries based on TTL.

        Args:
            key: Storage key

        Returns:
            Current impression count (0 if expired or doesn't exist)
        """
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return 0

            # Check if expired
            if time.time() > entry["expires_at"]:
                del self._store[key]
                return 0

            return int(entry["count"])

    async def increment(self, key: str, ttl: int) -> int:
        """
        Increment impression count and update TTL.

        If the key doesn't exist, creates new entry with count=1.
        If the key exists but is expired, resets to count=1.

        Args:
            key: Storage key
            ttl: Time-to-live in seconds

        Returns:
            New impression count after increment
        """
        async with self._lock:
            now = time.time()
            entry = self._store.get(key)

            # Check if expired or doesn't exist
            if entry is None or now > entry["expires_at"]:
                self._store[key] = {
                    "count": 1,
                    "expires_at": now + ttl,
                }
                return 1

            # Increment existing non-expired entry (fixed window - TTL not reset)
            entry["count"] += 1
            # Note: TTL is NOT reset to maintain sliding window behavior
            return int(entry["count"])

    async def reset(self, key: str) -> None:
        """
        Reset impression count for key.

        Args:
            key: Storage key to reset
        """
        async with self._lock:
            self._store.pop(key, None)


class FrequencyCappingMiddleware:
    """
    Middleware for frequency capping of ad requests.

    Controls how often ads are shown to users by tracking impressions
    and enforcing configurable limits. Supports both per-user and
    per-campaign frequency caps.

    Frequency Cap Enforcement:
        1. Extract user_id from kwargs (via SessionContext)
        2. Optionally extract campaign_id from kwargs metadata
        3. Build storage key (e.g., "freq:user:123" or "freq:user:123:campaign:456")
        4. Check current count against cap limit
        5. If under limit, increment and pass to next handler
        6. If at/over limit, raise FrequencyCapExceeded

    Integration with SessionContext:
        The middleware expects kwargs to contain SessionContext with user_id.
        This can be provided via:
        - Direct SessionContext object in kwargs["context"]
        - VastSession which automatically merges context
        - Manual user_id in kwargs["user_id"]

    Thread Safety:
        Thread-safe when using thread-safe FrequencyStore implementations.
        The provided InMemoryFrequencyStore uses asyncio.Lock.

    Example:
        >>> from xsp.middleware.frequency import (
        ...     FrequencyCappingMiddleware,
        ...     FrequencyCap,
        ...     InMemoryFrequencyStore,
        ... )
        >>> from xsp.middleware.base import MiddlewareStack
        >>>
        >>> # Create frequency cap: max 3 impressions per hour
        >>> cap = FrequencyCap(
        ...     max_impressions=3,
        ...     time_window_seconds=3600,
        ...     per_campaign=False
        ... )
        >>>
        >>> # Create middleware with in-memory store
        >>> store = InMemoryFrequencyStore()
        >>> freq_middleware = FrequencyCappingMiddleware(cap, store)
        >>>
        >>> # Apply to upstream
        >>> stack = MiddlewareStack(freq_middleware)
        >>> wrapped = stack.wrap(upstream)
        >>>
        >>> # First 3 requests succeed
        >>> await wrapped.fetch(user_id="user-123")  # OK
        >>> await wrapped.fetch(user_id="user-123")  # OK
        >>> await wrapped.fetch(user_id="user-123")  # OK
        >>>
        >>> # 4th request raises exception
        >>> await wrapped.fetch(user_id="user-123")  # FrequencyCapExceeded!

    Example (per-campaign):
        >>> # Create per-campaign cap: max 5 per day
        >>> campaign_cap = FrequencyCap(
        ...     max_impressions=5,
        ...     time_window_seconds=86400,
        ...     per_campaign=True
        ... )
        >>> freq_middleware = FrequencyCappingMiddleware(campaign_cap, store)
        >>>
        >>> # Different campaigns have separate caps
        >>> await wrapped.fetch(
        ...     user_id="user-123",
        ...     context={"campaign_id": "camp-1"}
        ... )  # OK - camp-1 count: 1
        >>> await wrapped.fetch(
        ...     user_id="user-123",
        ...     context={"campaign_id": "camp-2"}
        ... )  # OK - camp-2 count: 1

    Attributes:
        cap: FrequencyCap configuration
        store: FrequencyStore implementation for persistence

    References:
        - IAB QAG: Recommends 3-10 impressions per 24 hours
        - OpenRTB 2.6 §3.2.4: Frequency cap signaling
        - VAST 4.2: User experience best practices
    """

    def __init__(self, cap: FrequencyCap, store: FrequencyStore):
        """
        Initialize frequency capping middleware.

        Args:
            cap: Frequency cap configuration
            store: Storage backend for impression tracking

        Example:
            >>> cap = FrequencyCap(max_impressions=5, time_window_seconds=3600)
            >>> store = InMemoryFrequencyStore()
            >>> middleware = FrequencyCappingMiddleware(cap, store)
        """
        self.cap = cap
        self.store = store

    def _build_key(self, user_id: str, campaign_id: str | None = None) -> str:
        """
        Build storage key for frequency tracking.

        Args:
            user_id: User identifier
            campaign_id: Optional campaign identifier (for per_campaign=True)

        Returns:
            Storage key string

        Example:
            >>> middleware._build_key("user-123")
            'freq:user:user-123'
            >>> middleware._build_key("user-123", "camp-456")
            'freq:user:user-123:campaign:camp-456'
        """
        if self.cap.per_campaign and campaign_id:
            return f"freq:user:{user_id}:campaign:{campaign_id}"
        return f"freq:user:{user_id}"

    def _extract_user_id(self, kwargs: dict[str, Any]) -> str | None:
        """
        Extract user_id from request kwargs.

        Tries multiple sources in order:
        1. Direct user_id parameter
        2. SessionContext in context parameter
        3. context dict with user_id key

        Args:
            kwargs: Request keyword arguments

        Returns:
            User ID string or None if not found

        Example:
            >>> kwargs = {"user_id": "user-123"}
            >>> middleware._extract_user_id(kwargs)
            'user-123'
            >>>
            >>> ctx = SessionContext(request_id="r1", user_id="user-456", ...)
            >>> kwargs = {"context": ctx}
            >>> middleware._extract_user_id(kwargs)
            'user-456'
        """
        # Direct user_id parameter
        if "user_id" in kwargs and kwargs["user_id"]:
            return str(kwargs["user_id"])

        # SessionContext object
        context = kwargs.get("context")
        if isinstance(context, SessionContext):
            return context.user_id

        # context dict with user_id
        if isinstance(context, dict) and "user_id" in context:
            return str(context["user_id"])

        return None

    def _extract_campaign_id(self, kwargs: dict[str, Any]) -> str | None:
        """
        Extract campaign_id from request kwargs.

        Looks for campaign_id in:
        1. Direct campaign_id parameter
        2. context dict metadata
        3. params dict

        Args:
            kwargs: Request keyword arguments

        Returns:
            Campaign ID string or None if not found

        Example:
            >>> kwargs = {"campaign_id": "camp-123"}
            >>> middleware._extract_campaign_id(kwargs)
            'camp-123'
            >>>
            >>> kwargs = {"context": {"campaign_id": "camp-456"}}
            >>> middleware._extract_campaign_id(kwargs)
            'camp-456'
        """
        # Direct campaign_id parameter
        if "campaign_id" in kwargs and kwargs["campaign_id"]:
            return str(kwargs["campaign_id"])

        # context dict
        context = kwargs.get("context")
        if isinstance(context, dict) and "campaign_id" in context:
            return str(context["campaign_id"])

        # SessionContext metadata
        if isinstance(context, SessionContext) and "campaign_id" in context.metadata:
            return str(context.metadata["campaign_id"])

        # params dict
        params = kwargs.get("params")
        if isinstance(params, dict) and "campaign_id" in params:
            return str(params["campaign_id"])

        return None

    async def __call__(
        self, upstream: Upstream[Any], next_handler: FetchFunc, **kwargs: Any
    ) -> Any:
        """
        Execute frequency cap check before passing to next handler.

        Args:
            upstream: Upstream instance
            next_handler: Next handler in middleware chain
            **kwargs: Request arguments

        Returns:
            Response from next handler

        Raises:
            FrequencyCapExceeded: If frequency cap limit is exceeded
            ValueError: If user_id cannot be extracted from request

        Example:
            >>> # Called automatically by middleware stack
            >>> result = await middleware(upstream, next_handler, user_id="user-123")
        """
        # Extract user_id
        user_id = self._extract_user_id(kwargs)
        if not user_id:
            raise ValueError(
                "Frequency capping requires user_id. "
                "Provide via kwargs['user_id'], SessionContext, or context dict."
            )

        # Extract campaign_id if per-campaign capping
        campaign_id = None
        if self.cap.per_campaign:
            campaign_id = self._extract_campaign_id(kwargs)

        # Build storage key
        key = self._build_key(user_id, campaign_id)

        # Check current count
        current_count = await self.store.get_count(key)

        # Enforce cap
        if current_count >= self.cap.max_impressions:
            raise FrequencyCapExceeded(
                f"Frequency cap exceeded for {key}: "
                f"{current_count}/{self.cap.max_impressions} impressions "
                f"in {self.cap.time_window_seconds}s window"
            )

        # Increment count before request (optimistic counting)
        await self.store.increment(key, self.cap.time_window_seconds)

        # Pass to next handler
        return await next_handler(**kwargs)
