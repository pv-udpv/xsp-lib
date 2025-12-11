"""OpenRTB 2.6 data models.

Based on OpenRTB 2.6 specification:
https://www.iab.com/wp-content/uploads/2016/03/OpenRTB-API-Specification-Version-2-6-final.pdf
"""

from typing_extensions import TypedDict
from typing import Any, NotRequired


class User(TypedDict, total=False):
    """OpenRTB User object.
    
    Attributes:
        id: Unique user ID from the exchange
        buyeruid: Buyer's unique user ID within the exchange
        yob: Year of birth as 4-digit integer
        gender: Gender ("M", "F", "O")
        keywords: Comma-separated list of keywords
    """

    id: str
    buyeruid: str
    yob: int
    gender: str
    keywords: str


class Device(TypedDict, total=False):
    """OpenRTB Device object.
    
    Attributes:
        ua: User agent
        ip: IPv4 address
        ipv6: IPv6 address
        os: Device OS
        osv: Device OS version
        devicetype: Device type (1=mobile, 2=personal computer, 3=connected TV, etc.)
        make: Device manufacturer
        model: Device model
        hwv: Hardware version
    """

    ua: str
    ip: str
    ipv6: str
    os: str
    osv: str
    devicetype: int
    make: str
    model: str
    hwv: str


class App(TypedDict, total=False):
    """OpenRTB App object (for in-app impressions).
    
    Attributes:
        id: App ID in the exchange
        name: App name
        bundle: App bundle name
        domain: App domain
        storeurl: App store URL
        cat: Content categories (IAB codes)
    """

    id: str
    name: str
    bundle: str
    domain: str
    storeurl: str
    cat: list[str]


class Site(TypedDict, total=False):
    """OpenRTB Site object (for web impressions).
    
    Attributes:
        id: Site ID in the exchange
        name: Site name
        domain: Site domain
        page: Page URL
        ref: HTTP referrer
        cat: Content categories (IAB codes)
    """

    id: str
    name: str
    domain: str
    page: str
    ref: str
    cat: list[str]


class Imp(TypedDict, total=False):
    """OpenRTB Impression object.
    
    Attributes:
        id: Impression ID (required)
        banner: Banner object for display
        video: Video object for video ads
        native: Native object for native ads
        instl: Interstitial flag (0 or 1)
        tagid: Ad unit tag ID
        bidfloor: Minimum bid price
        bidfloorcur: Bid floor currency (default: "USD")
        secure: Flag to indicate if HTTPS is required
    """

    id: str  # Required
    banner: dict[str, Any]
    video: dict[str, Any]
    native: dict[str, Any]
    instl: int
    tagid: str
    bidfloor: float
    bidfloorcur: str
    secure: int


class BidRequest(TypedDict, total=False):
    """OpenRTB BidRequest object.
    
    Attributes:
        id: Bid request ID (required)
        imp: List of impressions (required)
        site: Site object (for web)
        app: App object (for app)
        device: Device object
        user: User object
        cur: List of accepted currencies (default: ["USD"])
        test: Test mode flag (0 or 1)
        at: Auction type (1=first price, 2=second price)
        tmax: Maximum response time in milliseconds
    """

    id: str  # Required
    imp: list[Imp]  # Required
    site: Site
    app: App
    device: Device
    user: User
    cur: list[str]
    test: int
    at: int
    tmax: int


class Bid(TypedDict, total=False):
    """OpenRTB Bid object.
    
    Attributes:
        id: Bid ID
        impid: Impression ID being bid on (required)
        price: Bid price (required)
        adid: Ad ID
        adm: Ad markup (HTML, VAST XML, etc.)
        adomain: Advertiser domain(s)
        cid: Campaign ID
        crid: Creative ID
        h: Creative height
        w: Creative width
    """

    id: str
    impid: str  # Required
    price: float  # Required
    adid: str
    adm: str
    adomain: list[str]
    cid: str
    crid: str
    h: int
    w: int


class SeatBid(TypedDict, total=False):
    """OpenRTB SeatBid object.
    
    Attributes:
        bid: List of bids
        seat: Bidder seat ID
        group: Flag indicating if group must be used
    """

    bid: list[Bid]
    seat: str
    group: int


class BidResponse(TypedDict, total=False):
    """OpenRTB BidResponse object.
    
    Attributes:
        id: Bid request ID (required)
        seatbid: List of seat bids
        bidid: Bidder's ID
        cur: Currency of bid (default: "USD")
        nbr: No-bid reason code (if applicable)
    """

    id: str  # Required
    seatbid: list[SeatBid]
    bidid: str
    cur: str
    nbr: int
