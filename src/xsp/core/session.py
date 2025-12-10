"""Session management for xsp-lib.

This module provides session abstractions for stateful ad serving:
- SessionContext: Immutable request context for correlation and cachebusting
- UpstreamSession: Protocol for frequency capping and budget tracking

Per xsp-lib architecture documentation on session management.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Protocol


@dataclass(frozen=True)
class SessionContext:
    """Immutable request context for session management.

    Used for:
    - VAST macro substitution (CACHEBUSTING, TIMESTAMP, CORRELATOR)
    - Request correlation across services
    - Cookie management for frequency capping
    - Analytics and debugging

    Example:
        >>> context = SessionContext.create()
        >>> context.correlator
        '550e8400-e29b-41d4-a716-446655440000'
        >>> context.timestamp
        1702224000000

        >>> context_with_cookies = SessionContext.create(
        ...     cookies={"user_id": "abc123", "session_id": "xyz789"}
        ... )
    """

    timestamp: int  # Unix timestamp in milliseconds
    correlator: str  # UUID for request correlation (VAST macro)
    cachebusting: str  # Random value for cache prevention (VAST macro)
    cookies: dict[str, str]  # HTTP cookies for user identification
    request_id: str  # Unique request identifier

    @classmethod
    def create(
        cls,
        cookies: dict[str, str] | None = None,
    ) -> SessionContext:
        """Create a new SessionContext with auto-generated values.

        Args:
            cookies: Optional HTTP cookies (default: empty dict)

        Returns:
            SessionContext with generated timestamp, correlator, cachebusting, and request_id

        Example:
            >>> context = SessionContext.create()
            >>> context.timestamp > 0
            True
            >>> context.correlator
            '...'  # UUID v4
        """
        now = datetime.now(timezone.utc)
        return cls(
            timestamp=int(now.timestamp() * 1000),  # milliseconds
            correlator=str(uuid.uuid4()),
            cachebusting=str(uuid.uuid4()),
            cookies=cookies or {},
            request_id=f"req-{uuid.uuid4()}",
        )


class UpstreamSession(Protocol):
    """Protocol for stateful ad serving session.

    Provides:
    - Frequency capping (limit impressions per user per campaign)
    - Budget tracking (monitor campaign spend in real-time)
    - Session-aware requests (context propagation)

    Implementations must be thread-safe and async-compatible.

    Example:
        >>> # Implementation example (not included in core)
        >>> session = RedisUpstreamSession(upstream=vast_upstream, redis_client=redis)
        >>> can_serve = await session.check_frequency_cap("user123", "campaign456")
        >>> if can_serve:
        ...     response = await session.request(context, params={...})
        ...     await session.track_budget("campaign456", Decimal("0.50"))

    See Also:
        - docs/architecture/session-management.md
        - docs/guides/session-management.md
        - docs/guides/stateful-ad-serving.md
    """

    async def request(
        self,
        context: SessionContext,
        **kwargs: Any,
    ) -> Any:
        """Execute request with session state.

        Args:
            context: Request context (correlation, cachebusting, cookies)
            **kwargs: Additional parameters for upstream.fetch()

        Returns:
            Response from upstream service

        Raises:
            FrequencyCapExceeded: User exceeded frequency cap
            BudgetExceeded: Campaign budget exhausted
        """
        ...

    async def check_frequency_cap(
        self,
        user_id: str,
        campaign_id: str,
    ) -> bool:
        """Check if user has exceeded frequency cap.

        Args:
            user_id: User identifier (from cookies or device ID)
            campaign_id: Campaign identifier

        Returns:
            True if user can receive ad, False if cap exceeded
        """
        ...

    async def track_budget(
        self,
        campaign_id: str,
        cost: Decimal,
    ) -> bool:
        """Track campaign spend and check budget.

        Args:
            campaign_id: Campaign identifier
            cost: Cost of ad impression (CPM, CPC, etc.)

        Returns:
            True if budget sufficient, False if exhausted

        Raises:
            BudgetExceeded: Campaign budget exhausted
        """
        ...
