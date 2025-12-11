"""OpenRTB 2.6 Protocol Handler.

Maps protocol-agnostic AdRequest to OpenRTB BidRequest and parses
BidResponse back to AdResponse.
"""

import json
from typing import Any

from xsp.orchestrator import AdRequest, AdResponse, ProtocolHandler
from xsp.core import UpstreamSession

from .upstream import OpenRTBUpstream


class OpenRTBProtocolHandler(ProtocolHandler):
    """OpenRTB 2.6 Protocol Handler.
    
    Maps AdRequest (protocol-agnostic) to OpenRTB BidRequest
    and parses BidResponse back to AdResponse.
    
    Attributes:
        upstream: OpenRTB upstream for sending BidRequests
    """

    def __init__(self, upstream: OpenRTBUpstream) -> None:
        """Initialize OpenRTB protocol handler.
        
        Args:
            upstream: OpenRTB upstream implementation
        """
        self.upstream = upstream

    async def handle(
        self,
        request: AdRequest,
        session: UpstreamSession,
    ) -> AdResponse:
        """Handle OpenRTB bid request.
        
        Maps AdRequest to BidRequest, sends to upstream, parses response,
        and maps BidResponse back to AdResponse.
        
        Args:
            request: Protocol-agnostic AdRequest
            session: Session context
        
        Returns:
            AdResponse with bid data
        
        Raises:
            ValueError: If request is malformed or response is invalid
            RuntimeError: If upstream request fails
        """
        # 1. Map AdRequest → BidRequest parameters
        bid_params = self._map_ad_request_to_params(request, session)

        # 2. Send to upstream
        response_json = await session.request(
            params=bid_params,
            headers=None,
        )

        # 3. Parse BidResponse
        try:
            bid_response = json.loads(response_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in BidResponse: {e}") from e

        # 4. Map BidResponse → AdResponse
        ad_response = self._map_bid_response_to_ad_response(bid_response, request)

        return ad_response

    async def close(self) -> None:
        """Close handler resources."""
        await self.upstream.close()

    async def health_check(self) -> bool:
        """Check if handler is healthy.
        
        Returns:
            True if upstream endpoint is reachable
        """
        # For MVP, just verify upstream exists
        return bool(self.upstream and self.upstream.endpoint)

    def _map_ad_request_to_params(self, request: AdRequest, session: UpstreamSession) -> dict[str, Any]:
        """Map AdRequest to OpenRTB BidRequest parameters.
        
        Args:
            request: Protocol-agnostic AdRequest
            session: Session context
        
        Returns:
            Dict of BidRequest parameters
        """
        params: dict[str, Any] = {}

        # Use session correlator as bid request ID
        params["id"] = session.context.correlator

        # Dimensions
        if width := request.get("width"):
            params["width"] = width
        if height := request.get("height"):
            params["height"] = height

        # Site/domain
        if domain := request.get("domain"):
            params["domain"] = domain
        if page_url := request.get("page_url"):
            params["page_url"] = page_url
        if referrer := request.get("referrer"):
            params["referrer"] = referrer

        # Device/user agent
        if user_agent := request.get("user_agent"):
            params["user_agent"] = user_agent
        if ip_address := request.get("ip_address"):
            params["ip_address"] = ip_address

        # User
        if user_id := request.get("user_id"):
            params["user_id"] = user_id

        # Ad unit
        if tag_id := request.get("tag_id"):
            params["tag_id"] = tag_id
        if placement := request.get("placement"):
            params["placement"] = placement

        # Floor/budget
        if bidfloor := request.get("bidfloor"):
            params["bidfloor"] = bidfloor
        if bidfloorcur := request.get("bidfloorcur"):
            params["bidfloorcur"] = bidfloorcur

        # Impression count
        if num_impressions := request.get("num_impressions"):
            params["num_impressions"] = num_impressions

        # Test mode
        if test_mode := request.get("test_mode"):
            params["test_mode"] = test_mode

        # Currencies
        if currencies := request.get("currencies"):
            params["currencies"] = currencies

        return params

    def _map_bid_response_to_ad_response(self, bid_response: dict[str, Any], request: AdRequest) -> AdResponse:
        """Map BidResponse to protocol-agnostic AdResponse.
        
        Selects highest bid from all seatbids and maps to AdResponse.
        
        Args:
            bid_response: OpenRTB BidResponse dict
            request: Original AdRequest
        
        Returns:
            AdResponse with bid data
        """
        # Extract highest bid from all seatbids
        best_bid = None
        best_seatbid = None

        for seatbid in bid_response.get("seatbid", []):
            for bid in seatbid.get("bid", []):
                price = bid.get("price", 0)
                if not best_bid or price > best_bid.get("price", 0):
                    best_bid = bid
                    best_seatbid = seatbid

        # Build AdResponse
        ad_response: AdResponse = {
            "protocol": "openrtb",
            "bid_id": best_bid.get("id") if best_bid else None,
            "impid": best_bid.get("impid") if best_bid else None,
            "price": best_bid.get("price", 0) if best_bid else 0,
            "adm": best_bid.get("adm") if best_bid else None,
            "adomain": best_bid.get("adomain", []) if best_bid else [],
            "seat": best_seatbid.get("seat") if best_seatbid else None,
            "cid": best_bid.get("cid") if best_bid else None,
            "crid": best_bid.get("crid") if best_bid else None,
            "w": best_bid.get("w") if best_bid else request.get("width"),
            "h": best_bid.get("h") if best_bid else request.get("height"),
            "currency": bid_response.get("cur", "USD"),
            "bidid": bid_response.get("bidid"),
            "raw": bid_response,  # Store full response for debugging
        }

        return ad_response
