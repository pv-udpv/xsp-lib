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
