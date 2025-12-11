"""OpenRTB 2.6 Upstream implementation."""

import json
from typing import Any

from xsp.core import BaseUpstream, SessionContext, UpstreamSession
from xsp.transports import Transport

from .models import BidRequest, BidResponse


class OpenRTBUpstream(BaseUpstream):
    """OpenRTB 2.6 Upstream implementation.
    
    Handles BidRequest assembly and submission to OpenRTB endpoints,
    plus BidResponse parsing and processing.
    
    Attributes:
        transport: HTTP transport for sending requests
        endpoint: OpenRTB endpoint URL
    """

    def __init__(self, transport: Transport, endpoint: str) -> None:
        """Initialize OpenRTB upstream.
        
        Args:
            transport: HTTP transport
            endpoint: OpenRTB endpoint URL (e.g., "https://ads.example.com/openrtb")
        """
        self.transport = transport
        self.endpoint = endpoint

    async def request(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any
    ) -> str:
        """Send OpenRTB BidRequest and receive BidResponse.
        
        Args:
            params: Dict with BidRequest parameters
            headers: HTTP headers to include
            **kwargs: Additional arguments (unused)
        
        Returns:
            JSON string of BidResponse
        
        Raises:
            ValueError: If params don't contain required BidRequest fields
            RuntimeError: If upstream request fails
        """
        if not params:
            params = {}

        # Build BidRequest from params
        bid_request = self._build_bid_request(params)

        # Send to endpoint
        request_json = json.dumps(bid_request)
        response_text = await self.transport.request(
            method="POST",
            url=self.endpoint,
            data=request_json,
            headers=headers or {},
        )

        # Validate response is valid JSON
        try:
            json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in bid response: {e}") from e

        return response_text

    async def create_session(self, context: SessionContext) -> UpstreamSession:
        """Create OpenRTB session.
        
        Args:
            context: Session context
        
        Returns:
            UpstreamSession with OpenRTB session management
        """
        # For MVP, return basic session
        # TODO: Implement full OpenRTB session management
        return OpenRTBSession(self, context)

    async def close(self) -> None:
        """Close upstream resources."""
        await self.transport.close()

    def _build_bid_request(self, params: dict[str, Any]) -> BidRequest:
        """Build OpenRTB BidRequest from parameters.
        
        Args:
            params: Dict with request parameters
        
        Returns:
            BidRequest dict
        
        Raises:
            ValueError: If required fields are missing
        """
        # Extract or generate required fields
        bid_request_id = params.get("id", "bid-req-001")

        # Build impression object
        impressions = []
        num_impressions = params.get("num_impressions", 1)
        for i in range(num_impressions):
            imp: dict[str, Any] = {
                "id": params.get("imp_id") or f"imp-{i}",
            }

            # Banner
            if width := params.get("width"):
                imp["banner"] = {
                    "w": width,
                    "h": params.get("height", 250),
                }

            # Optional fields
            if tag_id := params.get("tag_id"):
                imp["tagid"] = tag_id
            if bidfloor := params.get("bidfloor"):
                imp["bidfloor"] = float(bidfloor)
            if bidfloorcur := params.get("bidfloorcur"):
                imp["bidfloorcur"] = bidfloorcur

            impressions.append(imp)

        # Build request
        bid_request: BidRequest = {
            "id": bid_request_id,
            "imp": impressions,
        }

        # Site object
        if domain := params.get("domain"):
            bid_request["site"] = {"domain": domain}
            if page_url := params.get("page_url"):
                bid_request["site"]["page"] = page_url

        # Device object
        if user_agent := params.get("user_agent"):
            bid_request["device"] = {"ua": user_agent}
            if ip := params.get("ip_address"):
                bid_request["device"]["ip"] = ip

        # User object
        if user_id := params.get("user_id"):
            bid_request["user"] = {"id": user_id}

        # Currencies
        bid_request["cur"] = params.get("currencies", ["USD"])

        # Test mode
        if test_mode := params.get("test_mode"):
            bid_request["test"] = 1

        return bid_request


class OpenRTBSession(UpstreamSession):
    """OpenRTB session implementation.
    
    Maintains session context across multiple bid requests.
    """

    def __init__(self, upstream: OpenRTBUpstream, context: SessionContext) -> None:
        """Initialize OpenRTB session.
        
        Args:
            upstream: OpenRTB upstream
            context: Session context
        """
        self._upstream = upstream
        self._context = context
        self._closed = False

    @property
    def context(self) -> SessionContext:
        """Get session context."""
        return self._context

    async def request(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any
    ) -> str:
        """Send bid request within session.
        
        Args:
            params: Request parameters
            headers: HTTP headers
            **kwargs: Additional arguments
        
        Returns:
            BidResponse JSON string
        
        Raises:
            RuntimeError: If session is closed
        """
        if self._closed:
            raise RuntimeError("Session is closed")

        if params is None:
            params = {}

        # Add session context to request
        params.setdefault("id", self._context.correlator)

        return await self._upstream.request(
            params=params,
            headers=headers,
            **kwargs
        )

    async def check_frequency_cap(self, user_id: str) -> bool:
        """Check frequency cap (MVP: always returns True).
        
        Args:
            user_id: User ID
        
        Returns:
            True if ad can be served
        """
        # TODO: Implement frequency capping with StateBackend
        return True

    async def track_budget(self, campaign_id: str, amount: float) -> None:
        """Track budget spend (MVP: no-op).
        
        Args:
            campaign_id: Campaign ID
            amount: Amount spent
        """
        # TODO: Implement budget tracking with StateBackend
        pass

    async def close(self) -> None:
        """Close session."""
        self._closed = True
