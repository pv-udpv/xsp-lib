"""OpenRTB 2.6 protocol implementation.

This package provides OpenRTB 2.6 support including data models and upstream
implementation for real-time bidding.

Example:
    >>> from xsp.protocols.openrtb import OpenRTBUpstream, BidRequest
    >>> from xsp.transports.http import HttpTransport
    >>>
    >>> transport = HttpTransport()
    >>> upstream = OpenRTBUpstream(
    ...     transport=transport,
    ...     endpoint="https://bidder.example.com/rtb"
    ... )
    >>>
    >>> response = await upstream.request(
    ...     params={
    ...         "id": "req123",
    ...         "imp": [{"id": "1", "banner": {"w": 300, "h": 250}}]
    ...     }
    ... )
"""

from .models import (
    App,
    Bid,
    BidRequest,
    BidResponse,
    Device,
    Imp,
    SeatBid,
    Site,
    User,
)
from .upstream import OpenRTBUpstream

__all__ = [
    "BidRequest",
    "BidResponse",
    "Bid",
    "SeatBid",
    "Imp",
    "User",
    "Device",
    "App",
    "Site",
    "OpenRTBUpstream",
]
