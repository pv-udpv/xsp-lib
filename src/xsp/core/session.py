"""Session management abstractions for stateful ad serving.

This module provides core session abstractions for maintaining state across
ad serving workflows (e.g., VAST wrapper chain resolution, frequency capping,
budget tracking).

Core Concepts:

1. SessionContext: Immutable context shared across wrapper resolution chain
   - Contains session state: timestamp, correlator, cookies, etc.
   - Frozen dataclass prevents accidental mutation
   - Safe to pass through multiple service calls

2. UpstreamSession: Stateful protocol for ad serving
   - Request within session context (preserves cookies, correlator)
   - Frequency capping: Check before serving ad
   - Budget tracking: Track spend per campaign
   - Resource cleanup: Close session when done

Example Usage:

    import time
    from xsp.core.session import SessionContext
    from xsp.protocols.vast import VastUpstream
    from xsp.transports.http import HttpTransport

    async def serve_ad():
        # Create immutable session context
        context = SessionContext(
            timestamp=int(time.time() * 1000),
            correlator="session-abc123",
            cachebusting="rand-456789",
            cookies={"uid": "user123"},
            request_id="req-001"
        )

        # Create stateful session
        upstream = VastUpstream(
            transport=HttpTransport(),
            endpoint="https://ads.example.com/vast"
        )
        session = await upstream.create_session(context)

        try:
            # Check frequency cap
            if await session.check_frequency_cap("user123"):
                # Serve ad within session context
                ad = await session.request(
                    params={"slot": "pre-roll"},
                    headers={"X-Custom": "value"}
                )

                # Track budget
                await session.track_budget("campaign-456", 2.50)
                return ad
            else:
                return None  # Cap exceeded
        finally:
            # Always cleanup
            await session.close()
"""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SessionContext:
    """Immutable session context for stateful ad serving.

    SessionContext provides immutable state shared across the entire
    ad serving workflow (e.g., VAST wrapper chain resolution). It contains:

    - Session identification (correlator, request_id)
    - Timing information (timestamp for macros)
    - HTTP state (cookies, cache-busting)

    The frozen dataclass ensures thread-safe sharing without risk of
    accidental mutation during processing.

    Attributes:
        timestamp: Unix timestamp in milliseconds. Used for [TIMESTAMP] macro.
                  Example: 1702275840000
        correlator: Unique session identifier. Used for [CORRELATOR] macro.
                   Example: "session-abc123"
        cachebusting: Random value for cache-busting. Used for [CACHEBUSTING]
                     macro. Example: "456789123"
        cookies: HTTP cookies to preserve across requests in session.
                Example: {"uid": "user123", "session": "xyz"}
        request_id: Request tracing ID for logging/debugging.
                   Example: "req-001"

    Example:
        >>> import time
        >>> context = SessionContext(
        ...     timestamp=int(time.time() * 1000),
        ...     correlator="session-abc",
        ...     cachebusting="rand123",
        ...     cookies={"uid": "user1"},
        ...     request_id="req-1"
        ... )
        >>> print(context.timestamp)
        1702275840000
        >>> print(context.correlator)
        session-abc

    Immutability:
        The frozen=True parameter makes SessionContext immutable.
        Attempting to modify will raise FrozenInstanceError:

        >>> context.timestamp = 9999
        Traceback (most recent call last):
          ...
        dataclasses.FrozenInstanceError: cannot assign to field 'timestamp'
    """

    timestamp: int
    """Unix timestamp in milliseconds for [TIMESTAMP] macro."""

    correlator: str
    """Unique session ID for tracking across wrapper chain."""

    cachebusting: str
    """Random value for [CACHEBUSTING] macro in URLs."""

    cookies: dict[str, str]
    """HTTP cookies to preserve across session requests."""

    request_id: str
    """Request tracing ID for logging and debugging."""


class UpstreamSession(Protocol):
    """Protocol for stateful ad serving sessions.

    UpstreamSession provides a stateful interface for ad serving workflows
    that need to maintain state across multiple requests (e.g., wrapper
    resolution, frequency capping, budget tracking).

    Key responsibilities:
    - Maintain immutable SessionContext
    - Send requests within session context (preserves cookies, correlator)
    - Check frequency caps before serving ads
    - Track budget spend per campaign
    - Cleanup resources when done

    Implementations should:
    - Preserve session context across all requests
    - Integrate with StateBackend for persistence
    - Support frequency cap checking
    - Support budget tracking
    - Handle session lifecycle (creation, maintenance, cleanup)

    Example Implementation:

        class VastSession:
            def __init__(self, context: SessionContext, upstream: VastUpstream):
                self._context = context
                self._upstream = upstream

            @property
            def context(self) -> SessionContext:
                return self._context

            async def request(self, *, params: dict | None = None) -> str:
                # Merge session context with request params
                merged_params = {**params or {}}
                merged_params["correlator"] = self._context.correlator
                merged_params["timestamp"] = self._context.timestamp
                return await self._upstream.fetch(params=merged_params)

            async def check_frequency_cap(self, user_id: str) -> bool:
                # Check with state backend
                count = await self._state_backend.get_count(user_id)
                return count < MAX_ADS_PER_USER

            async def track_budget(self, campaign_id: str, amount: float) -> None:
                # Track spend
                await self._state_backend.add_spend(campaign_id, amount)

            async def close(self) -> None:
                # Cleanup
                pass
    """

    @property
    def context(self) -> SessionContext:
        """Get immutable session context.

        Returns:
            SessionContext: Immutable session context with timestamp, correlator,
                          cachebusting, cookies, and request_id.

        Example:
            >>> context = session.context
            >>> print(context.correlator)
            session-abc123
        """
        ...

    async def request(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any
    ) -> str:
        """Send request within session context.

        Sends a request to the upstream service with session context applied.
        The session context (correlator, timestamp, cookies) should be
        automatically merged with request parameters.

        Args:
            params: Request-specific parameters. These will be merged with
                   session parameters (session params take precedence).
                   Example: {"slot": "pre-roll", "uid": "user123"}
            headers: HTTP headers. Session cookies should be included.
                    Example: {"X-Custom": "value"}
            **kwargs: Additional arguments (transport-specific, timeout, etc.)

        Returns:
            str: Response data (e.g., VAST XML for video ads)

        Raises:
            UpstreamError: If request to upstream fails
            TimeoutError: If request exceeds timeout
            DecodeError: If response cannot be decoded

        Example:
            >>> xml = await session.request(
            ...     params={"slot": "pre-roll"},
            ...     headers={"User-Agent": "MyPlayer/1.0"}
            ... )
            >>> print(len(xml))
            1024
        """
        ...

    async def check_frequency_cap(
        self,
        user_id: str,
        limit: int | None = None,
        window_seconds: int | None = None
    ) -> bool:
        """Check if user has exceeded frequency cap.

        Checks whether the user has exceeded the configured frequency cap
        (max ads per user per time window). Should check with a state backend
        (Redis, database, or in-memory store).

        Args:
            user_id: User identifier to check cap for.
                    Example: "user123" or "device-456"
            limit: Maximum number of ads (None for default). Default: 3
            window_seconds: Time window in seconds (None for default).
                           Default: 3600 (1 hour)

        Returns:
            bool: True if ad can be served (cap not exceeded),
                  False if cap is exceeded

        Raises:
            StateBackendError: If state backend is unavailable

        Example:
            >>> if await session.check_frequency_cap("user123"):
            ...     ad = await session.request(params={...})
            ... else:
            ...     ad = await fallback_upstream.request(params={...})
        """
        ...

    async def track_budget(
        self,
        campaign_id: str,
        amount: float,
        currency: str = "USD"
    ) -> None:
        """Track budget spend for campaign.

        Records budget spend for a campaign (e.g., CPM cost). Should
        store in state backend with campaign lifetime scope.

        Args:
            campaign_id: Campaign identifier.
                        Example: "campaign-456"
            amount: Amount spent (e.g., CPM cost in currency).
                   Example: 2.50
            currency: Currency code (default: USD).
                     Example: "USD", "EUR", "GBP"

        Raises:
            StateBackendError: If state backend is unavailable
            ValueError: If amount is negative

        Example:
            >>> await session.track_budget("campaign-456", 2.50)
            >>> remaining = await session.get_remaining_budget("campaign-456")
            >>> print(remaining)
            97.50
        """
        ...

    async def close(self) -> None:
        """Release session resources.

        Cleanup method called when session is finished. Should:
        - Close connections
        - Flush any pending state changes
        - Release memory/handles
        - Log session metrics

        Should be idempotent (safe to call multiple times).

        Example:
            >>> session = await upstream.create_session(context)
            >>> try:
            ...     ad = await session.request(params={...})
            ... finally:
            ...     await session.close()
        """
        ...
