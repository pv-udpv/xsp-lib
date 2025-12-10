"""Protocol-agnostic request and response schemas using TypedDict."""

from typing import Any, NotRequired, Required, TypedDict


class AdRequest(TypedDict, total=False):
    """
    Protocol-agnostic ad request schema.

    Flexible schema that works across VAST, VMAP, OpenRTB, and custom protocols.

    Required fields:
        slot_id: Ad slot identifier (e.g., 'pre-roll', 'banner-top')
        user_id: User identifier for targeting and frequency capping

    Optional common fields:
        ip_address: Client IP address for geo-targeting
        device_type: Device type ('desktop', 'mobile', 'tablet', 'tv')
        content_url: URL of content being played
        content_duration: Total content duration in seconds
        playhead_position: Current playback position in seconds
        player_size: Player dimensions (width, height) as tuple
        geo: Geographic information dict

    Protocol-specific extensions:
        extensions: Dictionary for protocol-specific fields

    Examples:
        VAST request:
            AdRequest(
                slot_id="pre-roll",
                user_id="user123",
                device_type="mobile",
                playhead_position=0.0,
            )

        OpenRTB request:
            AdRequest(
                slot_id="banner-top",
                user_id="user123",
                player_size=(728, 90),
                geo={"country": "US", "region": "CA"},
            )
    """

    # Required fields
    slot_id: Required[str]
    """Ad slot identifier."""

    user_id: Required[str]
    """User identifier."""

    # Optional common fields
    ip_address: NotRequired[str]
    """Client IP address."""

    device_type: NotRequired[str]
    """Device type: 'desktop', 'mobile', 'tablet', 'tv'."""

    content_url: NotRequired[str]
    """URL of content being played."""

    content_duration: NotRequired[float]
    """Total content duration in seconds."""

    playhead_position: NotRequired[float]
    """Current playback position in seconds."""

    player_size: NotRequired[tuple[int, int]]
    """Player dimensions (width, height)."""

    geo: NotRequired[dict[str, Any]]
    """Geographic information (lat, lon, country, region, etc.)."""

    # Protocol-specific extensions
    extensions: NotRequired[dict[str, Any]]
    """Protocol-specific extensions."""


class AdResponse(TypedDict, total=False):
    """
    Protocol-agnostic ad response schema.

    Flexible schema that works across VAST, VMAP, OpenRTB, and custom protocols.

    Required fields:
        success: Whether ad fetch was successful
        slot_id: Ad slot identifier (echoed from request)

    Optional common fields:
        ad_id: Ad or creative identifier
        creative_url: URL of creative (video, image, etc.)
        creative_type: Creative type ('video/linear', 'display/banner', etc.)
        format: Creative format ('mp4', 'webm', 'hls', 'jpeg', etc.)
        duration: Creative duration in seconds (for video)
        bitrate: Creative bitrate in kbps
        dimensions: Creative dimensions (width, height)

    Tracking:
        tracking_urls: Tracking URLs by event type dict

    Metadata:
        ad_system: Ad system identifier
        advertiser: Advertiser name
        campaign_id: Campaign identifier

    Resolution metadata:
        resolution_chain: List of upstream URLs used
        used_fallback: Whether fallback upstream was used
        cached: Whether response came from cache
        resolution_time_ms: Resolution time in milliseconds

    Error information:
        error: Error message if success=False
        error_code: Error code if success=False

    Protocol-specific:
        extensions: Protocol-specific data
        raw_response: Raw protocol response (for debugging)

    Examples:
        VAST response:
            AdResponse(
                success=True,
                slot_id="pre-roll",
                ad_id="ad-123",
                creative_url="https://cdn.example.com/video.mp4",
                creative_type="video/linear",
                format="mp4",
                duration=30.0,
                tracking_urls={"impression": [...], "complete": [...]},
            )

        OpenRTB response:
            AdResponse(
                success=True,
                slot_id="banner-top",
                extensions={"bid_price": 2.50, "adm": "<html>..."},
            )
    """

    # Required fields
    success: Required[bool]
    """Whether ad fetch was successful."""

    slot_id: Required[str]
    """Ad slot identifier (echoed from request)."""

    # Optional common fields
    ad_id: NotRequired[str]
    """Ad or creative identifier."""

    creative_url: NotRequired[str]
    """URL of creative (video, image, etc.)."""

    creative_type: NotRequired[str]
    """Creative type: 'video/linear', 'display/banner', etc."""

    format: NotRequired[str]
    """Creative format: 'mp4', 'webm', 'hls', 'jpeg', etc."""

    duration: NotRequired[float]
    """Creative duration in seconds (for video)."""

    bitrate: NotRequired[int]
    """Creative bitrate in kbps."""

    dimensions: NotRequired[tuple[int, int]]
    """Creative dimensions (width, height)."""

    # Tracking
    tracking_urls: NotRequired[dict[str, list[str]]]
    """Tracking URLs by event type: {'impression': [...], 'click': [...]}."""

    # Metadata
    ad_system: NotRequired[str]
    """Ad system identifier."""

    advertiser: NotRequired[str]
    """Advertiser name."""

    campaign_id: NotRequired[str]
    """Campaign identifier."""

    # Resolution metadata
    resolution_chain: NotRequired[list[str]]
    """Upstream chain used for resolution."""

    used_fallback: NotRequired[bool]
    """Whether fallback upstream was used."""

    cached: NotRequired[bool]
    """Whether response came from cache."""

    resolution_time_ms: NotRequired[float]
    """Resolution time in milliseconds."""

    # Error information
    error: NotRequired[str]
    """Error message if success=False."""

    error_code: NotRequired[str]
    """Error code if success=False."""

    # Protocol-specific extensions
    extensions: NotRequired[dict[str, Any]]
    """Protocol-specific data."""

    # Raw protocol response (for debugging)
    raw_response: NotRequired[Any]
    """Raw protocol response (VAST XML, OpenRTB JSON, etc.)."""
