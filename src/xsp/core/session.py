"""Session abstractions for stateful ad serving."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SessionContext:
    """
    Immutable session context shared across wrapper resolution chain.

    Attributes:
        timestamp: Unix timestamp in milliseconds (for [TIMESTAMP] macro)
        correlator: Unique session ID (for [CORRELATOR] macro)
        cachebusting: Random value (for [CACHEBUSTING] macro)
        cookies: HTTP cookies to preserve across requests
        request_id: Request tracing ID

    Example:
        ```python
        context = SessionContext(
            timestamp=int(time.time() * 1000),
            correlator="session-abc123",
            cachebusting="rand-456789",
            cookies={"uid": "user123"},
            request_id="req-001"
        )

        # Immutable - this raises FrozenInstanceError
        context.timestamp = 9999  # ❌ Error
        ```
    """

    timestamp: int
    correlator: str
    cachebusting: str
    cookies: dict[str, str]
    request_id: str


class UpstreamSession(Protocol):
    """
    Stateful session for ad serving with frequency capping and budget tracking.

    Example:
        ```python
        session = await upstream.create_session(context)

        # Check frequency cap
        if await session.check_frequency_cap("user123"):
            response = await session.request(params={"slot": "pre-roll"})

            # Track budget
            await session.track_budget("campaign-456", 2.50)

        await session.close()
        ```
    """

    @property
    def context(self) -> SessionContext:
        """Get immutable session context."""
        ...

    async def request(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Send request within session context.

        SessionContext values (correlator, timestamp, cookies) are
        automatically applied to all requests in the session.

        Args:
            params: Request parameters
            headers: HTTP headers (merged with session cookies)
            **kwargs: Additional arguments

        Returns:
            Response data (e.g., VAST XML)
        """
        ...

    async def check_frequency_cap(self, user_id: str) -> bool:
        """
        Check if user has exceeded frequency cap.

        Args:
            user_id: User identifier

        Returns:
            True if ad can be served, False if cap exceeded
        """
        ...

    async def track_budget(self, campaign_id: str, amount: float) -> None:
        """
        Track budget spend for campaign.

        Args:
            campaign_id: Campaign identifier
            amount: Amount spent (e.g., CPM cost)
        """
        ...

    async def close(self) -> None:
        """Release session resources."""
        ...
