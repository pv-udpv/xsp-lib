"""VAST protocol types and enums."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class VastVersion(str, Enum):
    """Supported VAST versions."""

    V2_0 = "2.0"
    V3_0 = "3.0"
    V4_0 = "4.0"
    V4_1 = "4.1"
    V4_2 = "4.2"


class MediaType(str, Enum):
    """Media file MIME types."""

    VIDEO_MP4 = "video/mp4"
    VIDEO_WEBM = "video/webm"
    VIDEO_OGG = "video/ogg"
    VIDEO_3GPP = "video/3gpp"
    APPLICATION_JAVASCRIPT = "application/javascript"  # VPAID
    APPLICATION_X_SHOCKWAVE_FLASH = "application/x-shockwave-flash"  # VPAID Flash


@dataclass
class VastResponse:
    """Parsed VAST response."""

    xml: str
    version: VastVersion
    ad_system: str | None = None
    ad_title: str | None = None
    impressions: list[str] | None = None
    media_files: list[dict[str, Any]] | None = None
    tracking_events: dict[str, list[str]] | None = None
    error_urls: list[str] | None = None


@dataclass
class VastResolutionResult:
    """Result of VAST wrapper chain resolution.

    Contains the final resolved VAST response and metadata about
    the resolution process including chain depth, fallback usage,
    and timing information.

    Per VAST 4.2 §2.4.3.4 - Wrapper resolution follows VASTAdTagURI
    recursively until an InLine response is found or depth limit is reached.
    """

    success: bool
    vast_data: dict[str, Any] | None = None
    selected_creative: dict[str, Any] | None = None
    chain: list[str] = None  # type: ignore[assignment]
    xml: str | None = None
    error: Exception | None = None
    used_fallback: bool = False
    resolution_time_ms: float | None = None

    def __post_init__(self) -> None:
        """Initialize mutable default values."""
        if self.chain is None:
            self.chain = []
