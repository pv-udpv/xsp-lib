"""Session management for tracking request context and state."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, TypeVar

from xsp.protocols.vast.upstream import VastUpstream

T = TypeVar("T", covariant=True)


@dataclass(frozen=True)
class SessionContext:
    """
    Immutable session context for request tracking.

    Stores request metadata that should not change during the session lifecycle.
    Immutability is enforced via @dataclass(frozen=True).

    Attributes:
        request_id: Unique identifier for the request
        user_id: User identifier (e.g., cookie ID, device ID)
        ip_address: Client IP address
        timestamp: Request creation timestamp
        metadata: Additional context data (immutable after creation)

    Example:
        >>> from datetime import datetime
        >>> ctx = SessionContext(
        ...     request_id="req-123",
        ...     user_id="user-456",
        ...     ip_address="192.168.1.1",
        ...     timestamp=datetime.now(),
        ...     metadata={"platform": "web", "device": "desktop"}
        ... )
        >>> ctx.request_id
        'req-123'
        >>> ctx.metadata["platform"]
        'web'

    Note:
        While the dataclass is frozen, the metadata dict itself is mutable.
        For true immutability, avoid modifying metadata after creation.
    """

    request_id: str
    user_id: str | None
    ip_address: str | None
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


class UpstreamSession(Protocol[T]):
    """
    Protocol for session-aware upstream services.

    Extends the base Upstream protocol with session state tracking capabilities.
    Implementations maintain immutable SessionContext and mutable state dict.

    Attributes:
        context: Immutable session context
        state: Mutable session state dictionary (implementation-specific)

    Methods:
        fetch: Fetch data from upstream with session context
        close: Release resources and cleanup session
        health_check: Check upstream health

    Thread Safety:
        Implementations must ensure thread-safe state updates when used
        concurrently. Consider using asyncio.Lock for state modifications.

    Example:
        >>> session: UpstreamSession[str] = VastSession(...)
        >>> session.context.request_id
        'req-123'
        >>> result = await session.fetch(params={"w": "640"})
        >>> session.state["request_count"]
        1
    """

    @property
    def context(self) -> SessionContext:
        """Get immutable session context."""
        ...

    @property
    def state(self) -> dict[str, Any]:
        """Get mutable session state."""
        ...

    async def fetch(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        context: dict[str, Any] | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> T:
        """
        Fetch data from upstream.

        Args:
            params: Query parameters
            headers: HTTP headers
            context: Additional context data
            timeout: Request timeout in seconds
            **kwargs: Additional arguments

        Returns:
            Fetched data of type T

        Raises:
            UpstreamError: If fetch fails
            UpstreamTimeout: If request times out
        """
        ...

    async def close(self) -> None:
        """Release resources and cleanup session."""
        ...

    async def health_check(self) -> bool:
        """
        Check upstream health.

        Returns:
            True if healthy, False otherwise
        """
        ...


class VastSession:
    """
    VAST upstream session with state tracking.

    Wraps VastUpstream to provide session-aware request handling with
    immutable context and mutable state tracking. Maintains statistics
    about requests, errors, and timing.

    State Tracking:
        - request_count: Total number of requests made
        - last_request_time: Timestamp of most recent request
        - errors: List of error messages encountered
        - total_bytes: Total bytes fetched (if trackable)

    Thread Safety:
        State updates are protected by asyncio.Lock to ensure thread-safe
        concurrent access. Multiple coroutines can safely share a VastSession.

    Example:
        >>> from datetime import datetime
        >>> from xsp.core.transport import Transport
        >>> from xsp.protocols.vast.upstream import VastUpstream
        >>>
        >>> # Create session context
        >>> ctx = SessionContext(
        ...     request_id="req-789",
        ...     user_id="user-123",
        ...     ip_address="10.0.0.1",
        ...     timestamp=datetime.now(),
        ...     metadata={"campaign_id": "camp-456"}
        ... )
        >>>
        >>> # Create VAST upstream
        >>> transport = ...  # Your transport implementation
        >>> vast = VastUpstream(transport, endpoint="https://ads.example.com/vast")
        >>>
        >>> # Wrap in session
        >>> session = VastSession(vast, ctx)
        >>>
        >>> # Fetch with automatic state tracking
        >>> vast_xml = await session.fetch(params={"w": "640", "h": "480"})
        >>> session.state["request_count"]
        1
        >>> session.state["last_request_time"]
        datetime(...)

    Attributes:
        upstream: Underlying VastUpstream instance
        context: Immutable session context
        state: Mutable state dictionary
    """

    def __init__(self, upstream: VastUpstream, context: SessionContext) -> None:
        """
        Initialize VAST session.

        Args:
            upstream: VastUpstream instance to wrap
            context: Immutable session context

        Example:
            >>> ctx = SessionContext(
            ...     request_id="req-001",
            ...     user_id="user-001",
            ...     ip_address="192.168.1.100",
            ...     timestamp=datetime.now()
            ... )
            >>> vast_upstream = VastUpstream(...)
            >>> session = VastSession(vast_upstream, ctx)
        """
        self.upstream = upstream
        self._context = context
        self._state: dict[str, Any] = {
            "request_count": 0,
            "last_request_time": None,
            "errors": [],
            "total_bytes": 0,
        }
        self._lock = asyncio.Lock()

    @property
    def context(self) -> SessionContext:
        """
        Get immutable session context.

        Returns:
            SessionContext instance

        Example:
            >>> session.context.request_id
            'req-001'
            >>> session.context.user_id
            'user-001'
        """
        return self._context

    @property
    def state(self) -> dict[str, Any]:
        """
        Get mutable session state.

        Returns:
            State dictionary with request statistics

        Warning:
            Direct modifications to this dict are not protected by the lock.
            Use the provided methods for thread-safe updates.

        Example:
            >>> session.state["request_count"]
            5
            >>> session.state["errors"]
            []
        """
        return self._state

    async def fetch(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        context: dict[str, Any] | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Fetch VAST XML from upstream with session state tracking.

        Automatically updates session state including request count,
        last request time, and error tracking. Thread-safe for concurrent
        requests.

        Args:
            params: Query parameters for VAST request
            headers: HTTP headers
            context: Additional context for macro substitution
            timeout: Request timeout in seconds
            **kwargs: Additional arguments passed to upstream

        Returns:
            VAST XML string

        Raises:
            UpstreamError: If upstream fetch fails
            UpstreamTimeout: If request times out
            TransportError: If transport operation fails

        Example:
            >>> # Basic fetch
            >>> xml = await session.fetch(params={"w": "1920", "h": "1080"})
            >>>
            >>> # With context for macro substitution
            >>> xml = await session.fetch(
            ...     params={"w": "640"},
            ...     context={"PLAYHEAD": "00:01:30"}
            ... )
            >>>
            >>> # Check state after fetch
            >>> session.state["request_count"]
            1
            >>> session.state["last_request_time"]
            datetime(...)
        """
        # Merge session context into request context
        merged_context = {
            "request_id": self._context.request_id,
            "user_id": self._context.user_id,
            "ip_address": self._context.ip_address,
            **(self._context.metadata or {}),
            **(context or {}),
        }

        try:
            # Fetch from upstream
            result = await self.upstream.fetch(
                params=params,
                headers=headers,
                context=merged_context,
                timeout=timeout,
                **kwargs,
            )

            # Update state (thread-safe)
            async with self._lock:
                self._state["request_count"] += 1
                self._state["last_request_time"] = datetime.now()
                # Track approximate response size
                if isinstance(result, str):
                    self._state["total_bytes"] += len(result.encode("utf-8"))

            return result

        except Exception as e:
            # Track errors (thread-safe)
            async with self._lock:
                self._state["errors"].append(
                    {
                        "timestamp": datetime.now(),
                        "error": str(e),
                        "type": type(e).__name__,
                    }
                )
            raise

    async def close(self) -> None:
        """
        Close upstream and cleanup session resources.

        Delegates to underlying VastUpstream.close(). State is preserved
        but no further requests should be made after closing.

        Example:
            >>> await session.close()
            >>> # session.state is still accessible
            >>> session.state["request_count"]
            10
        """
        await self.upstream.close()

    async def health_check(self) -> bool:
        """
        Check upstream health.

        Delegates to underlying VastUpstream.health_check() without
        updating session state.

        Returns:
            True if upstream is healthy, False otherwise

        Example:
            >>> is_healthy = await session.health_check()
            >>> if is_healthy:
            ...     print("Upstream is operational")
        """
        return await self.upstream.health_check()
