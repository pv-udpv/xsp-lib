"""Tests for AdCOM media objects."""

import pytest

from xsp.standards.adcom.enums import (
    AuditStatusCode,
    CreativeAttribute,
    EventTrackingMethod,
    EventType,
    LinearityMode,
    NativeDataAssetType,
)
from xsp.standards.adcom.media import (
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
)


def test_event_creation() -> None:
    """Test Event object creation."""
    event = Event(
        type=EventType.IMPRESSION,
        method=EventTrackingMethod.IMAGE_PIXEL,
        url="https://tracker.example.com/impression",
    )
    assert event.type == EventType.IMPRESSION
    assert event.method == EventTrackingMethod.IMAGE_PIXEL
    assert event.url == "https://tracker.example.com/impression"


def test_audit_creation() -> None:
    """Test Audit object creation."""
    audit = Audit(
        status=AuditStatusCode.APPROVED,
        feedback=["Approved for all audiences"],
        init=1234567890,
    )
    assert audit.status == AuditStatusCode.APPROVED
    assert audit.feedback == ["Approved for all audiences"]
    assert audit.init == 1234567890


def test_banner_creation() -> None:
    """Test Banner object creation."""
    banner = Banner(
        img="https://example.com/banner.jpg",
        w=300,
        h=250,
        link="https://advertiser.example.com",
    )
    assert banner.img == "https://example.com/banner.jpg"
    assert banner.w == 300
    assert banner.h == 250
    assert banner.link == "https://advertiser.example.com"


def test_native_asset_creation() -> None:
    """Test Native asset creation."""
    title = TitleAsset(text="Great Product", len=13)
    image = ImageAsset(url="https://example.com/image.jpg", w=1200, h=627)
    data = DataAsset(value="Sponsored", type=NativeDataAssetType.SPONSORED)
    link = LinkAsset(url="https://example.com/landing")

    asset = Asset(
        id=1,
        req=1,
        title=title,
        img=image,
        data=data,
        link=link,
    )

    assert asset.id == 1
    assert asset.req == 1
    assert asset.title.text == "Great Product"
    assert asset.img.url == "https://example.com/image.jpg"
    assert asset.data.value == "Sponsored"
    assert asset.link.url == "https://example.com/landing"


def test_native_creation() -> None:
    """Test Native object creation."""
    link = LinkAsset(url="https://example.com/landing")
    title_asset = Asset(id=1, req=1, title=TitleAsset(text="Title"))

    native = Native(link=link, assets=[title_asset])

    assert native.link.url == "https://example.com/landing"
    assert len(native.assets) == 1
    assert native.assets[0].title.text == "Title"


def test_display_creation() -> None:
    """Test Display object creation."""
    banner = Banner(img="https://example.com/banner.jpg", w=300, h=250)
    event = Event(
        type=EventType.IMPRESSION,
        method=EventTrackingMethod.IMAGE_PIXEL,
        url="https://tracker.example.com/impression",
    )

    display = Display(
        mime="image/jpeg",
        w=300,
        h=250,
        banner=banner,
        event=[event],
    )

    assert display.mime == "image/jpeg"
    assert display.w == 300
    assert display.h == 250
    assert display.banner.img == "https://example.com/banner.jpg"
    assert len(display.event) == 1


def test_video_creation() -> None:
    """Test Video object creation."""
    video = Video(
        mime=["video/mp4"],
        dur=30,
        w=1920,
        h=1080,
        linear=LinearityMode.LINEAR,
        adm="<VAST version='4.0'>...</VAST>",
    )

    assert video.mime == ["video/mp4"]
    assert video.dur == 30
    assert video.w == 1920
    assert video.h == 1080
    assert video.linear == LinearityMode.LINEAR
    assert "<VAST" in video.adm


def test_audio_creation() -> None:
    """Test Audio object creation."""
    audio = Audio(
        mime=["audio/mp3"],
        dur=30,
        bitrate=128,
    )

    assert audio.mime == ["audio/mp3"]
    assert audio.dur == 30
    assert audio.bitrate == 128


def test_ad_with_display() -> None:
    """Test Ad object with display subtype."""
    display = Display(mime="image/jpeg", w=300, h=250)
    ad = Ad(
        id="ad-123",
        adomain=["advertiser.example.com"],
        display=display,
    )

    assert ad.id == "ad-123"
    assert ad.adomain == ["advertiser.example.com"]
    assert ad.display.w == 300
    assert ad.cattax == 2  # Default value


def test_ad_with_video() -> None:
    """Test Ad object with video subtype."""
    video = Video(mime=["video/mp4"], dur=30)
    ad = Ad(id="ad-video-123", video=video)

    assert ad.id == "ad-video-123"
    assert ad.video.dur == 30


def test_ad_with_audio() -> None:
    """Test Ad object with audio subtype."""
    audio = Audio(mime=["audio/mp3"], dur=30)
    ad = Ad(id="ad-audio-123", audio=audio)

    assert ad.id == "ad-audio-123"
    assert ad.audio.dur == 30


def test_ad_requires_one_media_subtype() -> None:
    """Test that Ad requires exactly one media subtype."""
    # No media subtype
    with pytest.raises(ValueError, match="exactly one media subtype"):
        Ad(id="ad-123")

    # Multiple media subtypes
    display = Display(mime="image/jpeg")
    video = Video(mime=["video/mp4"])
    with pytest.raises(ValueError, match="exactly one media subtype"):
        Ad(id="ad-123", display=display, video=video)


def test_ad_with_audit() -> None:
    """Test Ad with audit information."""
    display = Display(mime="image/jpeg")
    audit = Audit(status=AuditStatusCode.APPROVED)
    ad = Ad(id="ad-123", display=display, audit=audit)

    assert ad.audit.status == AuditStatusCode.APPROVED


def test_ad_with_creative_attributes() -> None:
    """Test Ad with creative attributes."""
    display = Display(mime="image/jpeg")
    ad = Ad(
        id="ad-123",
        display=display,
        attr=[CreativeAttribute.AUDIO_AD_AUTO_PLAY, CreativeAttribute.EXPANDABLE_AUTOMATIC],
    )

    assert len(ad.attr) == 2
    assert CreativeAttribute.AUDIO_AD_AUTO_PLAY in ad.attr


def test_ad_secure_field() -> None:
    """Test Ad secure field validation."""
    display = Display(mime="image/jpeg")
    ad = Ad(id="ad-123", display=display, secure=1)

    assert ad.secure == 1


def test_ad_with_extension() -> None:
    """Test Ad with extension field."""
    display = Display(mime="image/jpeg")
    ad = Ad(id="ad-123", display=display, ext={"custom": "value"})

    assert ad.ext["custom"] == "value"


def test_asset_req_validation() -> None:
    """Test Asset req field validation."""
    # Valid values
    asset = Asset(id=1, req=0)
    assert asset.req == 0

    asset = Asset(id=1, req=1)
    assert asset.req == 1

    # Invalid value should raise error
    with pytest.raises(ValueError, match="req must be 0 or 1"):
        Asset(id=1, req=2)


def test_ad_cattax_default() -> None:
    """Test Ad cattax defaults to 2."""
    display = Display(mime="image/jpeg")
    ad = Ad(id="ad-123", display=display)

    assert ad.cattax == 2

    # Can override default
    ad = Ad(id="ad-123", display=display, cattax=1)
    assert ad.cattax == 1
