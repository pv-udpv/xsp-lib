"""OpenRTB 2.6 upstream implementation.

This module provides the OpenRTBUpstream class for communicating with
OpenRTB 2.6 bidders via HTTP/HTTPS transport.

References:
    - OpenRTB 2.6 Specification: https://www.iab.com/wp-content/uploads/2016/03/OpenRTB-API-Specification-Version-2-6-FINAL.pdf
    - IAB Tech Lab OpenRTB: https://iabtechlab.com/standards/openrtb/
"""

import json
from typing import Any

from xsp.core.base import BaseUpstream
from xsp.core.configurable import configurable
from xsp.core.exceptions import (
    OpenRTBHttpError,
    OpenRTBNetworkError,
    OpenRTBParseError,
    OpenRTBTimeoutError,
    TransportConnectionError,
    TransportError,
    TransportTimeoutError,
    UpstreamTimeout,
)
from xsp.core.transport import Transport

from .types import BidRequest, BidResponse


@configurable(namespace="openrtb", description="OpenRTB 2.6 protocol upstream for RTB bidding")
class OpenRTBUpstream(BaseUpstream[str]):
    """OpenRTB 2.6 upstream for real-time bidding.

    Supports:
    - OpenRTB 2.6 bid request/response protocol
    - JSON serialization/deserialization
    - HTTP/HTTPS transport with configurable timeout
    - Flexible bidder-specific parameters via extensions

    The upstream returns the raw JSON string response from the bidder,
    allowing the handler to parse and process the bid response.

    Example:
        >>> from xsp.transports.http import HttpTransport
        >>> transport = HttpTransport()
        >>> upstream = OpenRTBUpstream(
        ...     transport=transport,
        ...     endpoint="https://bidder.example.com/bid",
        ... )
        >>> bid_request = {
        ...     "id": "req-123",
        ...     "imp": [{"id": "imp-1", "banner": {"w": 728, "h": 90}}],
        ...     "device": {"ip": "203.0.113.1"},
        ...     "user": {"id": "user-456"},
        ... }
        >>> response = await upstream.request(payload=bid_request)
        >>> print(response)  # JSON string with bid response

    References:
        OpenRTB 2.6 §3 - Bid Request/Response Specification
    """

    def __init__(
        self,
        transport: Transport,
        endpoint: str,
        *,
        currency: str = "USD",
        test_mode: bool = False,
        auction_type: int = 2,
        timeout_ms: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize OpenRTB upstream.

        Args:
            transport: Transport implementation (usually HTTP)
            endpoint: Bidder endpoint URL
            currency: Default currency code (ISO-4217, default "USD")
            test_mode: Enable test mode (test=1 in bid requests)
            auction_type: Auction type (1=first price, 2=second price, default 2)
            timeout_ms: Bidder timeout in milliseconds (for tmax field)
            **kwargs: Passed to BaseUpstream

        Note:
            OpenRTB 2.6 uses JSON over HTTP POST. The transport must support
            POST requests with Content-Type: application/json.
        """
        super().__init__(
            transport=transport,
            decoder=lambda b: b.decode("utf-8"),
            encoder=lambda obj: json.dumps(obj).encode("utf-8"),
            endpoint=endpoint,
            **kwargs,
        )
        self.currency = currency
        self.test_mode = test_mode
        self.auction_type = auction_type
        self.timeout_ms = timeout_ms

    async def request(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        context: dict[str, Any] | None = None,
        timeout: float | None = None,
        payload: BidRequest | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """Send OpenRTB bid request and receive bid response.

        Args:
            params: Query parameters (rarely used in OpenRTB)
            headers: HTTP headers (e.g., x-openrtb-version: 2.6)
            context: Additional context (unused in base implementation)
            timeout: Request timeout in seconds
            payload: BidRequest dict to send to bidder
            **kwargs: Additional arguments

        Returns:
            Raw JSON string containing BidResponse

        Raises:
            OpenRTBTimeoutError: If request times out
            OpenRTBNetworkError: If network/connection error occurs
            OpenRTBHttpError: If HTTP error status returned
            OpenRTBParseError: If response JSON is invalid

        Example:
            >>> bid_request = {
            ...     "id": "req-123",
            ...     "imp": [{
            ...         "id": "imp-1",
            ...         "banner": {"w": 300, "h": 250},
            ...         "bidfloor": 0.50
            ...     }],
            ...     "site": {"page": "https://example.com"},
            ...     "device": {"ip": "203.0.113.1", "ua": "Mozilla/5.0 ..."},
            ...     "user": {"id": "user-456"},
            ... }
            >>> response_json = await upstream.request(payload=bid_request)

        Note:
            Per OpenRTB 2.6 §3.1, bid requests must be sent via HTTP POST
            with Content-Type: application/json.
        """
        if payload is None:
            raise ValueError("payload (BidRequest) is required for OpenRTB requests")

        # Set OpenRTB headers
        merged_headers = headers.copy() if headers else {}
        merged_headers.setdefault("Content-Type", "application/json")
        merged_headers.setdefault("x-openrtb-version", "2.6")

        # Apply default fields to bid request
        if isinstance(payload, dict):
            payload.setdefault("test", 1 if self.test_mode else 0)
            payload.setdefault("at", self.auction_type)
            if self.timeout_ms:
                payload.setdefault("tmax", self.timeout_ms)

        # Send request via parent with error mapping
        try:
            json_response = await super().request(
                params=params,
                headers=merged_headers,
                context=context,
                timeout=timeout,
                payload=payload,
                **kwargs,
            )
        except TransportTimeoutError as e:
            raise OpenRTBTimeoutError(str(e)) from e
        except UpstreamTimeout as e:
            raise OpenRTBTimeoutError(str(e)) from e
        except TransportConnectionError as e:
            raise OpenRTBNetworkError(str(e)) from e
        except TransportError as e:
            if e.status_code is not None:
                raise OpenRTBHttpError(str(e), e.status_code) from e
            else:
                raise OpenRTBNetworkError(str(e)) from e

        # Validate JSON response
        try:
            # Parse to validate JSON structure
            parsed: BidResponse = json.loads(json_response)

            # Validate required fields per OpenRTB 2.6 §4.2.1
            if "id" not in parsed:
                raise OpenRTBParseError("Invalid BidResponse: missing required field 'id'")

            return json_response
        except json.JSONDecodeError as e:
            raise OpenRTBParseError(f"Invalid JSON response: {e}") from e

    async def send_bid_request(
        self,
        bid_request: BidRequest | dict[str, Any],
        *,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> BidResponse:
        """Send bid request and parse response.

        Convenience method that sends a bid request and returns the parsed
        BidResponse dict (instead of raw JSON string).

        Args:
            bid_request: BidRequest dict to send
            timeout: Request timeout in seconds
            **kwargs: Additional arguments passed to request()

        Returns:
            Parsed BidResponse dict

        Raises:
            OpenRTBTimeoutError: If request times out
            OpenRTBNetworkError: If network/connection error occurs
            OpenRTBHttpError: If HTTP error status returned
            OpenRTBParseError: If response JSON is invalid

        Example:
            >>> bid_request = {
            ...     "id": "req-123",
            ...     "imp": [{"id": "imp-1", "banner": {"w": 728, "h": 90}}],
            ...     "user": {"id": "user-456"},
            ... }
            >>> bid_response = await upstream.send_bid_request(bid_request)
            >>> print(bid_response["seatbid"][0]["bid"][0]["price"])
            2.50
        """
        json_response = await self.request(payload=bid_request, timeout=timeout, **kwargs)
        parsed: BidResponse = json.loads(json_response)
        return parsed
