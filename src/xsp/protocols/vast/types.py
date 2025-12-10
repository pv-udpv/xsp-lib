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
    
    def __lt__(self, other: object) -> bool:
        """Compare VAST versions for ordering."""
        if not isinstance(other, VastVersion):
            return NotImplemented
        version_order = [
            VastVersion.V2_0,
            VastVersion.V3_0,
            VastVersion.V4_0,
            VastVersion.V4_1,
            VastVersion.V4_2,
        ]
        return version_order.index(self) < version_order.index(other)
    
    def __le__(self, other: object) -> bool:
        """Compare VAST versions for ordering."""
        if not isinstance(other, VastVersion):
            return NotImplemented
        return self == other or self < other
    
    def __gt__(self, other: object) -> bool:
        """Compare VAST versions for ordering."""
        if not isinstance(other, VastVersion):
            return NotImplemented
        return not self <= other
    
    def __ge__(self, other: object) -> bool:
        """Compare VAST versions for ordering."""
        if not isinstance(other, VastVersion):
            return NotImplemented
        return not self < other


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
