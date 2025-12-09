"""AdCOM 1.0 - Advertising Common Object Model.

Layer-4 domain model for IAB programmatic standards (OpenRTB 3.0, CATS, OpenDirect).
Provides structured, reusable representations of ads, placements, users, devices, and contexts.

Reference: https://github.com/InteractiveAdvertisingBureau/AdCOM/blob/main/AdCOM%20v1.0%20FINAL.md
"""

# Enumerations
from .enums import (
    AdPosition,
    ApiFramework,
    AuditStatusCode,
    CategoryTaxonomy,
    ClickType,
    CompanionType,
    ConnectionType,
    ContentContext,
    CreativeAttribute,
    DOOHVenueType,
    DeliveryMethod,
    DeviceType,
    EventTrackingMethod,
    EventType,
    ExpandableDirection,
    FeedType,
    LinearityMode,
    LocationType,
    MediaRating,
    NativeDataAssetType,
    PlaybackCessationMode,
    PlaybackMethod,
    ProductionQuality,
    QAGMediaRating,
    VideoPlacementType,
    VolumeNormalizationMode,
)

# Common types
from .types import AdComModel, Metric

# Media objects
from .media import (
    Ad,
    Asset,
    Audio,
    Audit,
    Banner,
    DataAsset,
    Display,
    Event,
    ImageAsset,
    LinkAsset,
    Native,
    TitleAsset,
    Video,
    VideoAsset,
)

# Placement objects
from .placement import (
    AssetFormat,
    AudioPlacement,
    Companion,
    DataAssetFormat,
    DisplayFormat,
    DisplayPlacement,
    EventSpec,
    ImageAssetFormat,
    NativeFormat,
    Placement,
    TitleAssetFormat,
    VideoAssetFormat,
    VideoPlacement,
)

# Context objects
from .context import (
    App,
    BrandVersion,
    Channel,
    Content,
    Data,
    Device,
    Dooh,
    ExtendedIdentifiers,
    Geo,
    Network,
    Producer,
    Publisher,
    Regs,
    Restrictions,
    Segment,
    Site,
    User,
    UserAgent,
)

# Validation functions
from .validation import (
    validate_ad,
    validate_context,
    validate_device,
    validate_placement,
    validate_regs,
    validate_user,
)

# Utilities
from .utils import get_ext, has_ext, merge_ext, set_ext

__version__ = "1.0"

__all__ = [
    # Enumerations
    "AdPosition",
    "ApiFramework",
    "AuditStatusCode",
    "CategoryTaxonomy",
    "ClickType",
    "CompanionType",
    "ConnectionType",
    "ContentContext",
    "CreativeAttribute",
    "DOOHVenueType",
    "DeliveryMethod",
    "DeviceType",
    "EventTrackingMethod",
    "EventType",
    "ExpandableDirection",
    "FeedType",
    "LinearityMode",
    "LocationType",
    "MediaRating",
    "NativeDataAssetType",
    "PlaybackCessationMode",
    "PlaybackMethod",
    "ProductionQuality",
    "QAGMediaRating",
    "VideoPlacementType",
    "VolumeNormalizationMode",
    # Types
    "AdComModel",
    "Metric",
    # Media objects
    "Ad",
    "Asset",
    "Audio",
    "Audit",
    "Banner",
    "DataAsset",
    "Display",
    "Event",
    "ImageAsset",
    "LinkAsset",
    "Native",
    "TitleAsset",
    "Video",
    "VideoAsset",
    # Placement objects
    "AssetFormat",
    "AudioPlacement",
    "Companion",
    "DataAssetFormat",
    "DisplayFormat",
    "DisplayPlacement",
    "EventSpec",
    "ImageAssetFormat",
    "NativeFormat",
    "Placement",
    "TitleAssetFormat",
    "VideoAssetFormat",
    "VideoPlacement",
    # Context objects
    "App",
    "BrandVersion",
    "Channel",
    "Content",
    "Data",
    "Device",
    "Dooh",
    "ExtendedIdentifiers",
    "Geo",
    "Network",
    "Producer",
    "Publisher",
    "Regs",
    "Restrictions",
    "Segment",
    "Site",
    "User",
    "UserAgent",
    # Validation
    "validate_ad",
    "validate_context",
    "validate_device",
    "validate_placement",
    "validate_regs",
    "validate_user",
    # Utilities
    "get_ext",
    "has_ext",
    "merge_ext",
    "set_ext",
]
