"""OpenRTB 2.6 data models.

This module provides TypedDict-based models for OpenRTB 2.6 protocol objects.
All models follow the IAB OpenRTB 2.6 specification.

References:
    - OpenRTB 2.6 Specification: https://www.iab.com/wp-content/uploads/2016/03/OpenRTB-API-Specification-Version-2-6-FINAL.pdf
"""

from typing import Any, TypedDict


class User(TypedDict, total=False):
    """OpenRTB User object (§3.2.20).

    This object contains information about the user (human) as the end consumer
    of the media. The user information includes demographics and privacy controls.

    Attributes:
        id: Exchange-specific ID for the user
        buyeruid: Buyer-specific ID for the user as mapped by exchange
    """

    id: str
    buyeruid: str


class Device(TypedDict, total=False):
    """OpenRTB Device object (§3.2.18).

    This object provides information pertaining to the device through which the
    user is interacting. Device information includes its hardware, platform,
    location, and carrier.

    Attributes:
        ua: Browser user agent string
        ip: IPv4 address closest to device
        ipv6: IPv6 address closest to device
        os: Device operating system (e.g., "iOS", "Android")
        osv: Device operating system version (e.g., "10.1")
    """

    ua: str
    ip: str
    ipv6: str
    os: str
    osv: str


class App(TypedDict, total=False):
    """OpenRTB App object (§3.2.14).

    This object should be included if the ad supported content is a non-browser
    application (typically in mobile).

    Attributes:
        id: Exchange-specific app ID
        name: App name (may be aliased at publisher's request)
        domain: Domain of the app (e.g., "mygame.foo.com")
    """

    id: str
    name: str
    domain: str


class Site(TypedDict, total=False):
    """OpenRTB Site object (§3.2.13).

    This object should be included if the ad supported content is a website as
    opposed to a non-browser application.

    Attributes:
        id: Exchange-specific site ID
        name: Site name (may be aliased at publisher's request)
        domain: Domain of the site (e.g., "mysite.foo.com")
        page: URL of the page where the impression will be shown
    """

    id: str
    name: str
    domain: str
    page: str


class Imp(TypedDict, total=False):
    """OpenRTB Impression object (§3.2.4).

    This object describes an ad placement or impression being auctioned. A single
    bid request can include multiple Imp objects, a use case for which might be
    an exchange that supports selling all ad positions on a given page.

    Attributes:
        id: A unique identifier for this impression within the context of the bid request (required)
        banner: Banner object (§3.2.6) if this impression is offered as a banner ad opportunity
        video: Video object (§3.2.7) if this impression is offered as a video ad opportunity
        native: Native object (§3.2.9) if this impression is offered as a native ad opportunity
        instl: 1 = the ad is interstitial or full screen, 0 = not interstitial
        tagid: Identifier for specific ad placement or ad tag
        bidfloor: Minimum bid for this impression expressed in CPM
        bidfloorcur: Currency for bid floor using ISO-4217 alpha codes (default: "USD")
    """

    id: str
    banner: dict[str, Any]
    video: dict[str, Any]
    native: dict[str, Any]
    instl: int
    tagid: str
    bidfloor: float
    bidfloorcur: str


class BidRequest(TypedDict, total=False):
    """OpenRTB BidRequest object (§3.2.1).

    The top-level bid request object contains a globally unique bid request or
    auction ID. This id attribute is required as is at least one impression object
    (i.e., imp array must contain at least one object). Other attributes are
    optional.

    Attributes:
        id: Unique ID of the bid request (required)
        imp: Array of Imp objects representing the impressions offered (required, at least 1)
        site: Site object; recommended if this is a website impression
        app: App object; recommended if this is a non-browser app impression
        device: Device object with info about the user's device
        user: User object with info about the human user
        cur: Array of allowed currencies for bids (ISO-4217 codes). Default: ["USD"]
        test: Indicator of test mode: 0 = live mode, 1 = test mode
    """

    id: str
    imp: list[Imp]
    site: Site
    app: App
    device: Device
    user: User
    cur: list[str]
    test: int


class Bid(TypedDict, total=False):
    """OpenRTB Bid object (§4.2.3).

    A SeatBid object contains one or more Bid objects, each of which relates to a
    specific impression in the bid request via the impid attribute and constitutes
    an offer to buy that impression for a given price.

    Attributes:
        id: Bidder generated bid ID to assist with logging/tracking
        impid: ID of the Imp object in the related bid request (required)
        price: Bid price expressed as CPM (required)
        adid: ID of a preloaded ad to be served if the bid wins
        adm: Optional means of conveying ad markup (e.g., VAST XML, HTML)
        adomain: Advertiser domain for block list checking (e.g., ["ford.com"])
    """

    id: str
    impid: str
    price: float
    adid: str
    adm: str
    adomain: list[str]


class SeatBid(TypedDict, total=False):
    """OpenRTB SeatBid object (§4.2.2).

    A bid response can contain multiple SeatBid objects, each on behalf of a
    different bidder seat. A seat is a buyer's account with the exchange.

    Attributes:
        bid: Array of 1+ Bid objects each related to an impression
        seat: ID of the buyer seat on whose behalf this bid is made
    """

    bid: list[Bid]
    seat: str


class BidResponse(TypedDict, total=False):
    """OpenRTB BidResponse object (§4.2.1).

    This object is the top-level bid response object. The id attribute is a
    reflection of the bid request ID for logging purposes. A bid response can
    contain multiple SeatBid objects, each on behalf of a different bidder seat.

    Attributes:
        id: ID of the bid request to which this is a response (required)
        seatbid: Array of seatbid objects; 1+ required if a bid is to be made
        cur: Bid currency using ISO-4217 alpha codes (default: "USD")
    """

    id: str
    seatbid: list[SeatBid]
    cur: str
