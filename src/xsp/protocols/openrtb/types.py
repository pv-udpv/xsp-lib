"""OpenRTB 2.6 type definitions.

This module provides TypedDict definitions for OpenRTB 2.6 protocol structures.

References:
    - OpenRTB 2.6 Specification: https://www.iab.com/wp-content/uploads/2016/03/OpenRTB-API-Specification-Version-2-6-FINAL.pdf
    - IAB Tech Lab: https://iabtechlab.com/standards/openrtb/
"""

from typing import Any, NotRequired, TypedDict


# Device Type Enumeration (OpenRTB 2.6 §5.22)
class DeviceType:
    """Device type enumeration per OpenRTB 2.6 §5.22."""

    MOBILE_TABLET = 1
    PERSONAL_COMPUTER = 2
    CONNECTED_TV = 3
    PHONE = 4
    TABLET = 5
    CONNECTED_DEVICE = 6
    SET_TOP_BOX = 7


# Banner Object (OpenRTB 2.6 §3.2.6)
class Banner(TypedDict, total=False):
    """Banner object per OpenRTB 2.6 §3.2.6.

    Represents banner ad format with dimensions and placement.
    """

    w: NotRequired[int]
    """Width in pixels."""

    h: NotRequired[int]
    """Height in pixels."""

    id: NotRequired[str]
    """Banner object identifier."""

    btype: NotRequired[list[int]]
    """Blocked creative types."""

    battr: NotRequired[list[int]]
    """Blocked creative attributes."""

    pos: NotRequired[int]
    """Ad position on screen."""

    mimes: NotRequired[list[str]]
    """Supported MIME types."""

    topframe: NotRequired[int]
    """0 = not in top frame, 1 = in top frame."""

    expdir: NotRequired[list[int]]
    """Expandable ad directions."""

    api: NotRequired[list[int]]
    """Supported API frameworks."""

    ext: NotRequired[dict[str, Any]]
    """Extensions."""


# Video Object (OpenRTB 2.6 §3.2.7)
class Video(TypedDict, total=False):
    """Video object per OpenRTB 2.6 §3.2.7.

    Represents video ad format with player dimensions and protocols.
    """

    mimes: list[str]
    """Supported MIME types (required)."""

    minduration: NotRequired[int]
    """Minimum video duration in seconds."""

    maxduration: NotRequired[int]
    """Maximum video duration in seconds."""

    protocols: NotRequired[list[int]]
    """Supported video protocols."""

    w: NotRequired[int]
    """Width in pixels."""

    h: NotRequired[int]
    """Height in pixels."""

    startdelay: NotRequired[int]
    """Start delay in seconds."""

    linearity: NotRequired[int]
    """Video linearity (1=linear, 2=non-linear)."""

    api: NotRequired[list[int]]
    """Supported API frameworks."""

    ext: NotRequired[dict[str, Any]]
    """Extensions."""


# Geo Object (OpenRTB 2.6 §3.2.19)
class Geo(TypedDict, total=False):
    """Geo object per OpenRTB 2.6 §3.2.19.

    Provides geographic location information.
    """

    lat: NotRequired[float]
    """Latitude."""

    lon: NotRequired[float]
    """Longitude."""

    country: NotRequired[str]
    """Country code (ISO-3166-1-alpha-3)."""

    region: NotRequired[str]
    """Region code (ISO-3166-2)."""

    city: NotRequired[str]
    """City name."""

    zip: NotRequired[str]
    """Zip/postal code."""

    type: NotRequired[int]
    """Location type (1=GPS, 2=IP, 3=User)."""

    ext: NotRequired[dict[str, Any]]
    """Extensions."""


# Device Object (OpenRTB 2.6 §3.2.18)
class Device(TypedDict, total=False):
    """Device object per OpenRTB 2.6 §3.2.18.

    Provides information about the user's device.
    """

    ua: NotRequired[str]
    """User agent string."""

    geo: NotRequired[Geo]
    """Geographic location."""

    dnt: NotRequired[int]
    """Do Not Track (0=tracking, 1=do not track)."""

    lmt: NotRequired[int]
    """Limit Ad Tracking (0=tracking, 1=limit tracking)."""

    ip: NotRequired[str]
    """IPv4 address."""

    ipv6: NotRequired[str]
    """IPv6 address."""

    devicetype: NotRequired[int]
    """Device type per §5.22."""

    make: NotRequired[str]
    """Device manufacturer."""

    model: NotRequired[str]
    """Device model."""

    os: NotRequired[str]
    """Operating system."""

    osv: NotRequired[str]
    """Operating system version."""

    h: NotRequired[int]
    """Physical screen height in pixels."""

    w: NotRequired[int]
    """Physical screen width in pixels."""

    language: NotRequired[str]
    """Browser language (ISO-639-1-alpha-2)."""

    carrier: NotRequired[str]
    """Carrier or ISP."""

    connectiontype: NotRequired[int]
    """Connection type per §5.24."""

    ifa: NotRequired[str]
    """Advertising identifier (IFA)."""

    ext: NotRequired[dict[str, Any]]
    """Extensions."""


# User Object (OpenRTB 2.6 §3.2.20)
class User(TypedDict, total=False):
    """User object per OpenRTB 2.6 §3.2.20.

    Provides information about the user.
    """

    id: NotRequired[str]
    """Exchange-specific user ID."""

    buyeruid: NotRequired[str]
    """Buyer-specific user ID."""

    yob: NotRequired[int]
    """Year of birth (4-digit)."""

    gender: NotRequired[str]
    """Gender ('M', 'F', 'O')."""

    keywords: NotRequired[str]
    """User interest keywords."""

    geo: NotRequired[Geo]
    """Geographic location."""

    ext: NotRequired[dict[str, Any]]
    """Extensions."""


# Site Object (OpenRTB 2.6 §3.2.13)
class Site(TypedDict, total=False):
    """Site object per OpenRTB 2.6 §3.2.13.

    Provides information about the site where the ad will be shown.
    """

    id: NotRequired[str]
    """Site ID."""

    name: NotRequired[str]
    """Site name."""

    domain: NotRequired[str]
    """Site domain."""

    cat: NotRequired[list[str]]
    """IAB content categories."""

    page: NotRequired[str]
    """URL of the page."""

    ref: NotRequired[str]
    """Referrer URL."""

    keywords: NotRequired[str]
    """Site keywords."""

    ext: NotRequired[dict[str, Any]]
    """Extensions."""


# App Object (OpenRTB 2.6 §3.2.14)
class App(TypedDict, total=False):
    """App object per OpenRTB 2.6 §3.2.14.

    Provides information about the app where the ad will be shown.
    """

    id: NotRequired[str]
    """App ID."""

    name: NotRequired[str]
    """App name."""

    bundle: NotRequired[str]
    """App bundle/package name."""

    domain: NotRequired[str]
    """App domain."""

    cat: NotRequired[list[str]]
    """IAB content categories."""

    ver: NotRequired[str]
    """App version."""

    ext: NotRequired[dict[str, Any]]
    """Extensions."""


# Impression Object (OpenRTB 2.6 §3.2.4)
class Impression(TypedDict, total=False):
    """Impression object per OpenRTB 2.6 §3.2.4.

    Represents an ad placement opportunity.
    """

    id: str
    """Impression ID (required)."""

    banner: NotRequired[Banner]
    """Banner object if banner impression."""

    video: NotRequired[Video]
    """Video object if video impression."""

    tagid: NotRequired[str]
    """Ad tag ID."""

    bidfloor: NotRequired[float]
    """Minimum bid price (CPM)."""

    bidfloorcur: NotRequired[str]
    """Bid floor currency (ISO-4217)."""

    secure: NotRequired[int]
    """0 = non-secure, 1 = secure (HTTPS)."""

    iframebuster: NotRequired[list[str]]
    """Supported iframe busters."""

    ext: NotRequired[dict[str, Any]]
    """Extensions."""


# Bid Request (OpenRTB 2.6 §3.2.1)
class BidRequest(TypedDict, total=False):
    """Bid request per OpenRTB 2.6 §3.2.1.

    Top-level bid request object sent to bidders.

    References:
        OpenRTB 2.6 §3.2.1 - Bid Request Specification
    """

    id: str
    """Unique bid request ID (required)."""

    imp: list[Impression]
    """Array of impression objects (required)."""

    site: NotRequired[Site]
    """Site object (mobile web or desktop)."""

    app: NotRequired[App]
    """App object (mobile app)."""

    device: NotRequired[Device]
    """Device object."""

    user: NotRequired[User]
    """User object."""

    test: NotRequired[int]
    """0 = live, 1 = test mode."""

    at: NotRequired[int]
    """Auction type (1=first price, 2=second price)."""

    tmax: NotRequired[int]
    """Maximum time in ms to submit bid."""

    wseat: NotRequired[list[str]]
    """Whitelist of buyer seats."""

    bseat: NotRequired[list[str]]
    """Blocked buyer seats."""

    allimps: NotRequired[int]
    """All impressions flag."""

    cur: NotRequired[list[str]]
    """Allowed currencies (ISO-4217)."""

    bcat: NotRequired[list[str]]
    """Blocked advertiser categories."""

    badv: NotRequired[list[str]]
    """Blocked advertiser domains."""

    bapp: NotRequired[list[str]]
    """Blocked app bundles."""

    ext: NotRequired[dict[str, Any]]
    """Extensions."""


# Bid Object (OpenRTB 2.6 §4.2.3)
class Bid(TypedDict, total=False):
    """Bid object per OpenRTB 2.6 §4.2.3.

    Represents a bid for an impression.
    """

    id: str
    """Bid ID (required)."""

    impid: str
    """Impression ID being bid on (required)."""

    price: float
    """Bid price (CPM) (required)."""

    adid: NotRequired[str]
    """Ad ID to be served if won."""

    nurl: NotRequired[str]
    """Win notice URL."""

    adm: NotRequired[str]
    """Ad markup (HTML, VAST XML, etc.)."""

    adomain: NotRequired[list[str]]
    """Advertiser domains."""

    bundle: NotRequired[str]
    """App bundle for deep linking."""

    iurl: NotRequired[str]
    """Image URL for content checking."""

    cid: NotRequired[str]
    """Campaign ID."""

    crid: NotRequired[str]
    """Creative ID."""

    cat: NotRequired[list[str]]
    """IAB content categories."""

    attr: NotRequired[list[int]]
    """Creative attributes."""

    dealid: NotRequired[str]
    """Deal ID if applicable."""

    w: NotRequired[int]
    """Width in pixels."""

    h: NotRequired[int]
    """Height in pixels."""

    ext: NotRequired[dict[str, Any]]
    """Extensions."""


# Seat Bid Object (OpenRTB 2.6 §4.2.2)
class SeatBid(TypedDict, total=False):
    """Seat bid object per OpenRTB 2.6 §4.2.2.

    Collection of bids from a single seat.
    """

    bid: list[Bid]
    """Array of bid objects (required)."""

    seat: NotRequired[str]
    """Seat ID."""

    group: NotRequired[int]
    """0 = impressions can be won individually, 1 = all-or-nothing."""

    ext: NotRequired[dict[str, Any]]
    """Extensions."""


# Bid Response (OpenRTB 2.6 §4.2.1)
class BidResponse(TypedDict, total=False):
    """Bid response per OpenRTB 2.6 §4.2.1.

    Top-level bid response object returned by bidders.

    References:
        OpenRTB 2.6 §4.2.1 - Bid Response Specification
    """

    id: str
    """Bid request ID (required, echoed from request)."""

    seatbid: NotRequired[list[SeatBid]]
    """Array of seat bid objects."""

    bidid: NotRequired[str]
    """Bid ID for logging/tracking."""

    cur: NotRequired[str]
    """Bid currency (ISO-4217, default USD)."""

    customdata: NotRequired[str]
    """Custom data."""

    nbr: NotRequired[int]
    """No-bid reason code."""

    ext: NotRequired[dict[str, Any]]
    """Extensions."""


# Device Type Mapping
DEVICE_TYPE_MAP: dict[str, int] = {
    "mobile": DeviceType.PHONE,
    "tablet": DeviceType.TABLET,
    "desktop": DeviceType.PERSONAL_COMPUTER,
    "tv": DeviceType.CONNECTED_TV,
    "connected_device": DeviceType.CONNECTED_DEVICE,
    "set_top_box": DeviceType.SET_TOP_BOX,
}
"""Map string device types to OpenRTB integer codes."""


__all__ = [
    "Banner",
    "Video",
    "Geo",
    "Device",
    "User",
    "Site",
    "App",
    "Impression",
    "BidRequest",
    "Bid",
    "SeatBid",
    "BidResponse",
    "DeviceType",
    "DEVICE_TYPE_MAP",
]
