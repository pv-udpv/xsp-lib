"""OpenRTB protocol handler for orchestrator.

This module provides OpenRTBProtocolHandler for integrating OpenRTB 2.6
bidding with the xsp-lib orchestrator framework.

References:
    - OpenRTB 2.6 Specification: https://www.iab.com/wp-content/uploads/2016/03/OpenRTB-API-Specification-Version-2-6-FINAL.pdf
"""

import uuid
from typing import Any

from xsp.core.exceptions import OpenRTBNoBidError
from xsp.orchestrator.protocol import ProtocolHandler
from xsp.orchestrator.schemas import AdRequest, AdResponse

from .types import DEVICE_TYPE_MAP, BidRequest, BidResponse, Impression
from .upstream import OpenRTBUpstream


class OpenRTBProtocolHandler(ProtocolHandler):
    """OpenRTB 2.6 protocol handler.

    Maps protocol-agnostic AdRequest/AdResponse to OpenRTB-specific
    bid requests and responses using OpenRTBUpstream.

    The handler performs the following mappings:
    - AdRequest → OpenRTB BidRequest (§3.2.1)
    - OpenRTB BidResponse (§4.2.1) → AdResponse
    - Selects highest-priced bid from seatbid array
    - Extracts creative markup (adm) and metadata

    Example:
        >>> from xsp.protocols.openrtb import OpenRTBUpstream
        >>> from xsp.transports.http import HttpTransport
        >>>
        >>> transport = HttpTransport()
        >>> upstream = OpenRTBUpstream(
        ...     transport=transport,
        ...     endpoint="https://bidder.example.com/bid",
        ... )
        >>> handler = OpenRTBProtocolHandler(upstream=upstream)
        >>>
        >>> # Use with orchestrator
        >>> from xsp.orchestrator import Orchestrator
        >>> orchestrator = Orchestrator(protocol_handler=handler)
        >>> response = await orchestrator.fetch_ad(
        ...     AdRequest(
        ...         slot_id="banner-top",
        ...         user_id="user123",
        ...         player_size=(728, 90),
        ...         ip_address="203.0.113.1",
        ...     )
        ... )

    References:
        OpenRTB 2.6 §3 - Bid Request Specification
        OpenRTB 2.6 §4 - Bid Response Specification
    """

    def __init__(self, upstream: OpenRTBUpstream):
        """Initialize OpenRTB protocol handler.

        Args:
            upstream: OpenRTBUpstream instance for RTB operations
        """
        self.upstream = upstream

    async def fetch(
        self,
        request: AdRequest,
        **context: object,
    ) -> AdResponse:
        """Fetch ad via OpenRTB bidding.

        Maps AdRequest → BidRequest → BidResponse → AdResponse

        Args:
            request: Protocol-agnostic ad request
            **context: Additional context (unused)

        Returns:
            Protocol-agnostic ad response with bid details

        Flow:
            1. Build OpenRTB BidRequest from AdRequest
            2. Send bid request via OpenRTBUpstream
            3. Parse BidResponse and select winning bid
            4. Map bid to AdResponse

        Raises:
            OpenRTBError: If bidding fails or no bid received

        Note:
            Per OpenRTB 2.6 §4.2.1, a BidResponse with no seatbid array
            or empty seatbid indicates no bid.
        """
        try:
            # Build OpenRTB bid request
            bid_request = self._build_bid_request(request)

            # Send bid request
            bid_response = await self.upstream.send_bid_request(bid_request)

            # Build ad response from bid response
            return self._build_ad_response(request, bid_response)

        except OpenRTBNoBidError as e:
            # No bid is not an error - return unsuccessful response
            return AdResponse(
                success=False,
                slot_id=request["slot_id"],
                error=str(e),
                error_code="NO_BID",
            )
        except Exception as e:
            # Other errors
            return AdResponse(
                success=False,
                slot_id=request["slot_id"],
                error=str(e),
                error_code="OPENRTB_ERROR",
            )

    async def track(
        self,
        event: str,
        response: AdResponse,
        **context: object,
    ) -> None:
        """Track OpenRTB event.

        Fires win notice URL (nurl) for impression events.

        Args:
            event: Event type ('impression', 'click', etc.)
            response: Ad response containing tracking data
            **context: Additional context

        Note:
            Per OpenRTB 2.6 §4.2.3, the nurl (win notice URL) should be
            fired when the impression is served. Other tracking is typically
            handled by the creative markup (adm).
        """
        # In a full implementation:
        # - Fire nurl on impression event
        # - Extract and fire tracking URLs from adm if present
        # - Handle click tracking if applicable

        if event == "impression":
            # Extract nurl from extensions
            nurl = response.get("extensions", {}).get("nurl")
            if nurl:
                # Fire win notice URL
                # await self._fire_tracking_url(nurl)
                pass

    def validate_request(self, request: AdRequest) -> bool:
        """Validate request has required fields for OpenRTB.

        OpenRTB requires:
        - slot_id: Mapped to impression tagid
        - user_id: Required for user targeting
        - player_size OR banner dimensions for banner ads

        Args:
            request: Ad request to validate

        Returns:
            True if request is valid for OpenRTB protocol
        """
        return "slot_id" in request and "user_id" in request

    def _build_bid_request(self, request: AdRequest) -> BidRequest:
        """Build OpenRTB BidRequest from AdRequest.

        Maps AdRequest fields to OpenRTB 2.6 bid request structure.

        Args:
            request: Protocol-agnostic ad request

        Returns:
            OpenRTB BidRequest dict

        Field Mappings:
            - slot_id → imp[].tagid
            - player_size → imp[].banner.w/h
            - user_id → user.id
            - ip_address → device.ip
            - device_type → device.devicetype (mapped to int)
            - content_url → site.page
            - geo → device.geo

        References:
            OpenRTB 2.6 §3.2 - Object Model
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Build impression object
        impression = self._build_impression(request)

        # Build device object
        device = self._build_device(request)

        # Build user object
        user = self._build_user(request)

        # Build site object (if content_url provided)
        site = self._build_site(request)

        # Construct bid request
        bid_request: BidRequest = {
            "id": request_id,
            "imp": [impression],
        }

        if device:
            bid_request["device"] = device

        if user:
            bid_request["user"] = user

        if site:
            bid_request["site"] = site

        # Add test flag if in extensions
        if request.get("extensions", {}).get("test_mode"):
            bid_request["test"] = 1

        return bid_request

    def _build_impression(self, request: AdRequest) -> Impression:
        """Build impression object from AdRequest.

        Args:
            request: Ad request

        Returns:
            OpenRTB Impression object

        References:
            OpenRTB 2.6 §3.2.4 - Impression Object
        """
        # Generate unique impression ID
        imp_id = str(uuid.uuid4())

        impression: Impression = {
            "id": imp_id,
        }

        # Add tagid from slot_id
        impression["tagid"] = request["slot_id"]

        # Add banner dimensions if player_size provided
        if "player_size" in request:
            width, height = request["player_size"]
            impression["banner"] = {
                "w": width,
                "h": height,
            }

        # Add bid floor if provided in extensions
        if "bid_floor" in request.get("extensions", {}):
            impression["bidfloor"] = request["extensions"]["bid_floor"]

        # Add secure flag if HTTPS
        if request.get("content_url", "").startswith("https://"):
            impression["secure"] = 1

        return impression

    def _build_device(self, request: AdRequest) -> dict[str, Any] | None:
        """Build device object from AdRequest.

        Args:
            request: Ad request

        Returns:
            OpenRTB Device object or None

        References:
            OpenRTB 2.6 §3.2.18 - Device Object
        """
        device: dict[str, Any] = {}

        # IP address
        if "ip_address" in request:
            device["ip"] = request["ip_address"]

        # Device type (map string to int)
        if "device_type" in request:
            device_type_str = request["device_type"].lower()
            device["devicetype"] = DEVICE_TYPE_MAP.get(device_type_str, DEVICE_TYPE_MAP["desktop"])

        # User agent from extensions
        if "user_agent" in request.get("extensions", {}):
            device["ua"] = request["extensions"]["user_agent"]

        # Geographic location
        if "geo" in request:
            geo_data = request["geo"]
            device["geo"] = {}

            if "lat" in geo_data:
                device["geo"]["lat"] = geo_data["lat"]
            if "lon" in geo_data:
                device["geo"]["lon"] = geo_data["lon"]
            if "country" in geo_data:
                device["geo"]["country"] = geo_data["country"]
            if "region" in geo_data:
                device["geo"]["region"] = geo_data["region"]
            if "city" in geo_data:
                device["geo"]["city"] = geo_data["city"]
            if "zip" in geo_data:
                device["geo"]["zip"] = geo_data["zip"]

        return device if device else None

    def _build_user(self, request: AdRequest) -> dict[str, Any] | None:
        """Build user object from AdRequest.

        Args:
            request: Ad request

        Returns:
            OpenRTB User object or None

        References:
            OpenRTB 2.6 §3.2.20 - User Object
        """
        user: dict[str, Any] = {}

        # User ID
        if "user_id" in request:
            user["id"] = request["user_id"]

        # Additional user fields from extensions
        extensions = request.get("extensions", {})
        if "buyer_uid" in extensions:
            user["buyeruid"] = extensions["buyer_uid"]
        if "user_keywords" in extensions:
            user["keywords"] = extensions["user_keywords"]

        return user if user else None

    def _build_site(self, request: AdRequest) -> dict[str, Any] | None:
        """Build site object from AdRequest.

        Args:
            request: Ad request

        Returns:
            OpenRTB Site object or None

        References:
            OpenRTB 2.6 §3.2.13 - Site Object
        """
        site: dict[str, Any] = {}

        # Content URL → page
        if "content_url" in request:
            site["page"] = request["content_url"]

            # Extract domain from URL
            from urllib.parse import urlparse

            parsed = urlparse(request["content_url"])
            if parsed.netloc:
                site["domain"] = parsed.netloc

        # Additional site fields from extensions
        extensions = request.get("extensions", {})
        if "site_name" in extensions:
            site["name"] = extensions["site_name"]
        if "site_categories" in extensions:
            site["cat"] = extensions["site_categories"]

        return site if site else None

    def _build_ad_response(self, request: AdRequest, bid_response: BidResponse) -> AdResponse:
        """Build AdResponse from OpenRTB BidResponse.

        Selects the highest-priced bid and maps to AdResponse format.

        Args:
            request: Original ad request
            bid_response: OpenRTB bid response from bidder

        Returns:
            Protocol-agnostic ad response

        Raises:
            OpenRTBNoBidError: If no bids in response

        References:
            OpenRTB 2.6 §4.2 - Bid Response Specification
        """
        # Check for bids
        seatbid = bid_response.get("seatbid", [])
        if not seatbid:
            raise OpenRTBNoBidError("No seatbid in bid response")

        # Collect all bids from all seats
        all_bids = []
        for seat in seatbid:
            all_bids.extend(seat.get("bid", []))

        if not all_bids:
            raise OpenRTBNoBidError("No bids in seatbid array")

        # Select highest-priced bid
        winning_bid = max(all_bids, key=lambda b: b.get("price", 0.0))

        # Extract bid details
        price = winning_bid.get("price", 0.0)
        ad_markup = winning_bid.get("adm", "")
        ad_id = winning_bid.get("adid") or winning_bid.get("id")
        creative_id = winning_bid.get("crid")
        campaign_id = winning_bid.get("cid")
        advertiser_domains = winning_bid.get("adomain", [])
        nurl = winning_bid.get("nurl")

        # Determine creative type from ad markup
        creative_type = "display/banner"
        if ad_markup.startswith("<VAST") or "<VAST" in ad_markup:
            creative_type = "video/vast"
        elif ad_markup.startswith("<!DOCTYPE") or ad_markup.startswith("<html"):
            creative_type = "display/html"

        # Build ad response
        response: AdResponse = {
            "success": True,
            "slot_id": request["slot_id"],
            "ad_id": ad_id or "unknown",
            "creative_type": creative_type,
            "raw_response": ad_markup,
        }

        # Add dimensions if present
        if "w" in winning_bid and "h" in winning_bid:
            response["dimensions"] = (winning_bid["w"], winning_bid["h"])

        # Add metadata
        if advertiser_domains:
            response["advertiser"] = advertiser_domains[0]

        if campaign_id:
            response["campaign_id"] = campaign_id

        # Add OpenRTB-specific extensions
        response["extensions"] = {
            "bid_price": price,
            "currency": bid_response.get("cur", "USD"),
            "creative_id": creative_id,
            "nurl": nurl,
            "adm": ad_markup,
            "bid_id": bid_response.get("bidid"),
        }

        return response

    async def close(self) -> None:
        """Release resources used by the handler."""
        await self.upstream.close()

    async def health_check(self) -> bool:
        """Check handler health status.

        Returns:
            True if upstream is healthy, False otherwise
        """
        return await self.upstream.health_check()
