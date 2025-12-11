"""OpenRTB 2.6 protocol implementation.

This module provides OpenRTB 2.6 (Real-Time Bidding) protocol support for
xsp-lib, enabling integration with programmatic advertising exchanges and
demand-side platforms.

Components:
    - OpenRTBUpstream: Upstream implementation for bidders
    - OpenRTBProtocolHandler: Protocol handler for orchestrator integration
    - Type definitions for BidRequest, BidResponse, and related objects

Example:
    Basic OpenRTB upstream usage:
        >>> from xsp.protocols.openrtb import OpenRTBUpstream
        >>> from xsp.transports.http import HttpTransport
        >>>
        >>> transport = HttpTransport()
        >>> upstream = OpenRTBUpstream(
        ...     transport=transport,
        ...     endpoint="https://bidder.example.com/bid",
        ... )
        >>>
        >>> bid_request = {
        ...     "id": "req-123",
        ...     "imp": [{"id": "imp-1", "banner": {"w": 728, "h": 90}}],
        ...     "user": {"id": "user-456"},
        ...     "device": {"ip": "203.0.113.1"},
        ... }
        >>>
        >>> bid_response = await upstream.send_bid_request(bid_request)
        >>> print(bid_response)

    Using with orchestrator:
        >>> from xsp.protocols.openrtb import OpenRTBProtocolHandler
        >>> from xsp.orchestrator import Orchestrator
        >>> from xsp.orchestrator.schemas import AdRequest
        >>>
        >>> handler = OpenRTBProtocolHandler(upstream=upstream)
        >>> orchestrator = Orchestrator(protocol_handler=handler)
        >>>
        >>> response = await orchestrator.fetch_ad(
        ...     AdRequest(
        ...         slot_id="banner-top",
        ...         user_id="user123",
        ...         player_size=(728, 90),
        ...         ip_address="203.0.113.1",
        ...     )
        ... )

References:
    - OpenRTB 2.6 Specification: https://www.iab.com/wp-content/uploads/2016/03/OpenRTB-API-Specification-Version-2-6-FINAL.pdf
    - IAB Tech Lab OpenRTB: https://iabtechlab.com/standards/openrtb/
"""

from xsp.protocols.openrtb.handler import OpenRTBProtocolHandler
from xsp.protocols.openrtb.types import (
    DEVICE_TYPE_MAP,
    App,
    Banner,
    Bid,
    BidRequest,
    BidResponse,
    Device,
    DeviceType,
    Geo,
    Impression,
    SeatBid,
    Site,
    User,
    Video,
)
from xsp.protocols.openrtb.upstream import OpenRTBUpstream

__all__ = [
    "OpenRTBUpstream",
    "OpenRTBProtocolHandler",
    "BidRequest",
    "BidResponse",
    "Impression",
    "Banner",
    "Video",
    "Device",
    "User",
    "Site",
    "App",
    "Geo",
    "Bid",
    "SeatBid",
    "DeviceType",
    "DEVICE_TYPE_MAP",
]
