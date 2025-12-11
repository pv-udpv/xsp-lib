"""Protocol-agnostic and protocol-specific request/response schemas.

This module defines TypedDict schemas for requests and responses across
different AdTech protocols. It uses an extension pattern to allow protocol-
specific fields while maintaining a common base structure.

Schemas:
    - AdRequest: Base request schema (protocol-agnostic)
    - AdResponse: Base response schema (protocol-agnostic)
    - VastRequest: VAST-specific request schema
    - VastResponse: VAST-specific response schema
    - VastSession: VAST session state
"""

from typing import Any, NotRequired, TypedDict
"""Protocol-agnostic request and response schemas using TypedDict."""

from typing import Any, NotRequired, Required, TypedDict


class AdRequest(TypedDict, total=False):
    """
    Protocol-agnostic ad request schema.

    This is the base schema that all protocol-specific requests extend.
    Uses the extension pattern via the 'extensions' field to allow
    protocol-specific data without polluting the base schema.

    Fields:
        endpoint: Target endpoint/URL for the request
        params: Query parameters
        headers: HTTP headers
        timeout: Request timeout in seconds
        context: Additional context data (e.g., macro substitution)
        extensions: Protocol-specific extensions
    """

    endpoint: NotRequired[str]
    params: NotRequired[dict[str, Any]]
    headers: NotRequired[dict[str, str]]
    timeout: NotRequired[float]
    context: NotRequired[dict[str, Any]]
    extensions: NotRequired[dict[str, Any]]
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

    Base schema for all protocol-specific responses.

    Fields:
        data: Response payload (protocol-specific format)
        metadata: Response metadata (headers, timing, etc.)
        extensions: Protocol-specific extensions
    """

    data: Any
    metadata: NotRequired[dict[str, Any]]
    extensions: NotRequired[dict[str, Any]]


# VAST-specific schemas


class VastRequest(AdRequest, total=False):
    """
    VAST-specific request schema.

    Extends AdRequest with VAST-specific fields.

    Inherited Fields (from AdRequest):
        endpoint: VAST ad server URL
        params: Query parameters (uid, ip, url, etc.)
        headers: HTTP headers
        timeout: Request timeout
        context: Macro substitution context
        extensions: Protocol-specific extensions

    VAST-specific Fields:
        user_id: User identifier (convenience field)
        ip_address: Client IP address (convenience field)
        url: Content URL (convenience field, may contain Cyrillic)
        version: Expected VAST version (e.g., "4.2")
        enable_macros: Enable IAB macro substitution
        validate_xml: Validate XML structure
    """

    # VAST-specific fields
    user_id: NotRequired[str]
    ip_address: NotRequired[str]
    url: NotRequired[str]
    version: NotRequired[str]
    enable_macros: NotRequired[bool]
    validate_xml: NotRequired[bool]


class VastResponse(TypedDict, total=False):
    """
    VAST-specific response schema.

    Fields:
        xml: VAST XML string
        metadata: Response metadata
        session_id: Session identifier (if session created)
    """

    xml: str
    metadata: NotRequired[dict[str, Any]]
    session_id: NotRequired[str]


class VastSession(TypedDict, total=False):
    """
    VAST session state.

    Represents an active VAST session with tracking data.

    Fields:
        session_id: Unique session identifier
        vast_xml: Current VAST XML
        wrapper_chain: List of wrapper URLs traversed
        impressions: List of impression URLs
        tracking_events: Dict of event type to tracking URLs
        creative_url: Current creative media file URL
        companion_ads: List of companion ad data
        extensions: Session-specific extensions
    """

    session_id: str
    vast_xml: NotRequired[str]
    wrapper_chain: NotRequired[list[str]]
    impressions: NotRequired[list[str]]
    tracking_events: NotRequired[dict[str, list[str]]]
    creative_url: NotRequired[str]
    companion_ads: NotRequired[list[dict[str, Any]]]
    extensions: NotRequired[dict[str, Any]]
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
