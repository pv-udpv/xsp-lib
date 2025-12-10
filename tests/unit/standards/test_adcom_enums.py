"""Tests for AdCOM enumerations."""

import pytest

from xsp.standards.adcom.enums import (
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


def test_api_framework_enum() -> None:
    """Test ApiFramework enumeration values."""
    assert ApiFramework.VPAID_1_0 == 1
    assert ApiFramework.VPAID_2_0 == 2
    assert ApiFramework.MRAID_1 == 3
    assert ApiFramework.MRAID_2 == 5
    assert ApiFramework.MRAID_3 == 6
    assert ApiFramework.OMID_1 == 7
    assert ApiFramework.SIMID_1_0 == 8
    assert ApiFramework.SIMID_1_1 == 9


def test_creative_attribute_enum() -> None:
    """Test CreativeAttribute enumeration values."""
    assert CreativeAttribute.AUDIO_AD_AUTO_PLAY == 1
    assert CreativeAttribute.AUDIO_AD_USER_INITIATED == 2
    assert CreativeAttribute.EXPANDABLE_AUTOMATIC == 3
    assert CreativeAttribute.POP == 8
    assert CreativeAttribute.AD_CAN_BE_SKIPPED == 16
    assert CreativeAttribute.FLASH == 17


def test_event_type_enum() -> None:
    """Test EventType enumeration values."""
    assert EventType.IMPRESSION == 1
    assert EventType.VIEWABLE_MRC_50 == 2
    assert EventType.VIEWABLE_MRC_100 == 3
    assert EventType.VIEWABLE_VIDEO_50 == 4


def test_ad_position_enum() -> None:
    """Test AdPosition enumeration values."""
    assert AdPosition.UNKNOWN == 0
    assert AdPosition.ABOVE_THE_FOLD == 1
    assert AdPosition.BELOW_THE_FOLD == 3
    assert AdPosition.HEADER == 4
    assert AdPosition.FOOTER == 5
    assert AdPosition.SIDEBAR == 6
    assert AdPosition.FULLSCREEN == 7


def test_video_placement_type_enum() -> None:
    """Test VideoPlacementType enumeration values."""
    assert VideoPlacementType.IN_STREAM == 1
    assert VideoPlacementType.IN_BANNER == 2
    assert VideoPlacementType.IN_ARTICLE == 3
    assert VideoPlacementType.IN_FEED == 4
    assert VideoPlacementType.INTERSTITIAL_SLIDER_FLOATING == 5


def test_playback_method_enum() -> None:
    """Test PlaybackMethod enumeration values."""
    assert PlaybackMethod.PAGE_LOAD_SOUND_ON == 1
    assert PlaybackMethod.PAGE_LOAD_SOUND_OFF == 2
    assert PlaybackMethod.CLICK_SOUND_ON == 3
    assert PlaybackMethod.ENTERING_VIEWPORT_SOUND_ON == 5
    assert PlaybackMethod.ENTERING_VIEWPORT_SOUND_OFF == 6


def test_category_taxonomy_enum() -> None:
    """Test CategoryTaxonomy enumeration values."""
    assert CategoryTaxonomy.IAB_CONTENT_CATEGORY_1_0 == 1
    assert CategoryTaxonomy.IAB_CONTENT_CATEGORY_2_0 == 2
    assert CategoryTaxonomy.IAB_AD_PRODUCT_TAXONOMY_1_0 == 3
    assert CategoryTaxonomy.IAB_CONTENT_TAXONOMY_3_0 == 6


def test_content_context_enum() -> None:
    """Test ContentContext enumeration values."""
    assert ContentContext.VIDEO == 1
    assert ContentContext.GAME == 2
    assert ContentContext.MUSIC == 3
    assert ContentContext.APPLICATION == 4
    assert ContentContext.TEXT == 5
    assert ContentContext.OTHER == 6
    assert ContentContext.UNKNOWN == 7


def test_device_type_enum() -> None:
    """Test DeviceType enumeration values."""
    assert DeviceType.MOBILE_TABLET == 1
    assert DeviceType.PERSONAL_COMPUTER == 2
    assert DeviceType.CONNECTED_TV == 3
    assert DeviceType.PHONE == 4
    assert DeviceType.TABLET == 5
    assert DeviceType.SET_TOP_BOX == 7


def test_connection_type_enum() -> None:
    """Test ConnectionType enumeration values."""
    assert ConnectionType.UNKNOWN == 0
    assert ConnectionType.ETHERNET == 1
    assert ConnectionType.WIFI == 2
    assert ConnectionType.CELLULAR_2G == 4
    assert ConnectionType.CELLULAR_3G == 5
    assert ConnectionType.CELLULAR_4G == 6


def test_dooh_venue_type_enum() -> None:
    """Test DOOHVenueType enumeration values."""
    assert DOOHVenueType.AIRBORNE == 1
    assert DOOHVenueType.AIRPORT_GENERAL == 2
    assert DOOHVenueType.CINEMA == 16
    assert DOOHVenueType.GAS_STATION == 26
    assert DOOHVenueType.MALL_GENERAL == 33
    assert DOOHVenueType.OTHER == 64


def test_linearity_mode_enum() -> None:
    """Test LinearityMode enumeration values."""
    assert LinearityMode.LINEAR == 1
    assert LinearityMode.NON_LINEAR == 2


def test_native_data_asset_type_enum() -> None:
    """Test NativeDataAssetType enumeration values."""
    assert NativeDataAssetType.SPONSORED == 1
    assert NativeDataAssetType.DESC == 2
    assert NativeDataAssetType.RATING == 3
    assert NativeDataAssetType.PRICE == 6
    assert NativeDataAssetType.CTATEXT == 12


def test_audit_status_code_enum() -> None:
    """Test AuditStatusCode enumeration values."""
    assert AuditStatusCode.PENDING_AUDIT == 1
    assert AuditStatusCode.PRE_APPROVED == 2
    assert AuditStatusCode.APPROVED == 3
    assert AuditStatusCode.DENIED == 4
    assert AuditStatusCode.CHANGED_RESUBMIT == 5
