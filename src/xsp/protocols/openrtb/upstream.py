"""OpenRTB 2.6 upstream implementation.

This module provides upstream implementations for OpenRTB 2.6 bidding protocol.
"""

import json
from typing import Any

from xsp.core.base import BaseUpstream
from xsp.core.session import SessionContext
from xsp.core.transport import Transport

from .models import BidRequest


class OpenRTBUpstream(BaseUpstream[str]):
    """OpenRTB 2.6 upstream for real-time bidding.

    This upstream handles OpenRTB bid requests and responses, converting
    parameters to BidRequest objects and parsing BidResponse JSON.

    Example:
        >>> from xsp.transports.http import HttpTransport
        >>> transport = HttpTransport()
        >>> upstream = OpenRTBUpstream(
        ...     transport=transport,
        ...     endpoint="https://bidder.example.com/rtb"
        ... )
        >>> response = await upstream.request(
        ...     params={
        ...         "id": "abc123",
        ...         "imp": [{"id": "1", "banner": {"w": 300, "h": 250}}]
        ...     }
        ... )
    """

    def __init__(
        self,
        transport: Transport,
        endpoint: str,
        **kwargs: Any,
    ) -> None:
        """Initialize OpenRTB upstream.

        Args:
            transport: Transport implementation for HTTP requests
            endpoint: Bidder endpoint URL
            **kwargs: Additional arguments passed to BaseUpstream
        """
        super().__init__(
            transport=transport,
            decoder=lambda b: b.decode("utf-8"),
            encoder=lambda data: json.dumps(data).encode("utf-8"),
            endpoint=endpoint,
            **kwargs,
        )

    async def request(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any
    ) -> str:
        """Send OpenRTB bid request.

        Args:
            params: Dict with OpenRTB request parameters (will be converted to BidRequest)
            headers: HTTP headers
            **kwargs: Additional arguments passed to BaseUpstream.request()

        Returns:
            JSON string of BidResponse

        Raises:
            ValueError: If params is missing or invalid

        Example:
            >>> response_json = await upstream.request(
            ...     params={
            ...         "id": "req123",
            ...         "imp": [{"id": "imp1", "banner": {"w": 728, "h": 90}}],
            ...         "site": {"domain": "example.com"},
            ...         "device": {"ua": "Mozilla/5.0..."}
            ...     }
            ... )
        """
        if not params:
            raise ValueError("params dict is required for OpenRTB requests")

        # Build BidRequest from params
        bid_request = self._build_bid_request(params)

        # Set Content-Type header for JSON
        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)

        # Send request via parent with JSON payload
        response = await super().request(
            payload=bid_request,
            headers=request_headers,
            **kwargs
        )

        return response

    def _build_bid_request(self, params: dict[str, Any]) -> BidRequest:
        """Build BidRequest from parameter dict.

        Args:
            params: Dictionary of BidRequest fields

        Returns:
            BidRequest TypedDict object

        Raises:
            ValueError: If required fields (id, imp) are missing
        """
        if "id" not in params:
            raise ValueError("BidRequest must have 'id' field")
        if "imp" not in params or not params["imp"]:
            raise ValueError("BidRequest must have at least one impression in 'imp' array")

        # Build BidRequest - TypedDict so we can just cast the params
        bid_request: BidRequest = {
            "id": params["id"],
            "imp": params["imp"],
        }

        # Add optional fields if present
        if "site" in params:
            bid_request["site"] = params["site"]
        if "app" in params:
            bid_request["app"] = params["app"]
        if "device" in params:
            bid_request["device"] = params["device"]
        if "user" in params:
            bid_request["user"] = params["user"]
        if "cur" in params:
            bid_request["cur"] = params["cur"]
        if "test" in params:
            bid_request["test"] = params["test"]

        return bid_request

    async def create_session(self, context: SessionContext) -> "OpenRTBSession":
        """Create OpenRTB session with context.

        Args:
            context: Immutable session context

        Returns:
            OpenRTBSession instance

        Example:
            >>> context = SessionContext(
            ...     timestamp=1702275840000,
            ...     correlator="sess-123",
            ...     cachebusting="rand456",
            ...     cookies={"uid": "user789"},
            ...     request_id="req-001"
            ... )
            >>> session = await upstream.create_session(context)
        """
        return OpenRTBSession(upstream=self, context=context)


class OpenRTBSession:
    """OpenRTB session for stateful bidding.

    Maintains session context across multiple bid requests and implements
    frequency capping and budget tracking.
    """

    def __init__(self, upstream: OpenRTBUpstream, context: SessionContext) -> None:
        """Initialize session.

        Args:
            upstream: OpenRTB upstream instance
            context: Immutable session context
        """
        self._upstream = upstream
        self._context = context
        self._closed = False

    @property
    def context(self) -> SessionContext:
        """Get immutable session context."""
        return self._context

    async def request(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any
    ) -> str:
        """Send bid request within session context.

        Args:
            params: BidRequest parameters
            headers: HTTP headers (cookies from context are merged)
            **kwargs: Additional arguments

        Returns:
            BidResponse JSON string

        Raises:
            RuntimeError: If session is closed
        """
        if self._closed:
            raise RuntimeError("Cannot request on closed session")

        # Merge session cookies into headers
        session_headers = dict(headers) if headers else {}
        if self._context.cookies:
            # Convert cookies dict to Cookie header
            cookie_str = "; ".join(f"{k}={v}" for k, v in self._context.cookies.items())
            session_headers["Cookie"] = cookie_str

        return await self._upstream.request(
            params=params,
            headers=session_headers,
            **kwargs
        )

    async def check_frequency_cap(
        self,
        user_id: str,
        limit: int | None = None,
        window_seconds: int | None = None
    ) -> bool:
        """Check if user has exceeded frequency cap.

        MVP implementation: Always returns True (no cap enforced).

        Args:
            user_id: User identifier
            limit: Maximum ads per window (unused in MVP)
            window_seconds: Time window in seconds (unused in MVP)

        Returns:
            Always True in MVP implementation
        """
        # MVP: No frequency capping
        return True

    async def track_budget(
        self,
        campaign_id: str,
        amount: float,
        currency: str = "USD"
    ) -> None:
        """Track budget spend for campaign.

        MVP implementation: No-op.

        Args:
            campaign_id: Campaign identifier (unused in MVP)
            amount: Amount spent (unused in MVP)
            currency: Currency code (unused in MVP)
        """
        # MVP: No budget tracking
        pass

    async def close(self) -> None:
        """Close session and release resources."""
        self._closed = True
