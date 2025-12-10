"""Tests for AdCOM placement objects."""

import pytest

from xsp.standards.adcom.enums import (
    AdPosition,
    EventTrackingMethod,
    EventType,
    LinearityMode,
    NativeDataAssetType,
    PlaybackMethod,
    VideoPlacementType,
)
from xsp.standards.adcom.placement import (
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
    VideoPlacement,
)


def test_event_spec_creation() -> None:
    """Test EventSpec object creation."""
    event_spec = EventSpec(
        type=EventType.IMPRESSION,
        method=[EventTrackingMethod.IMAGE_PIXEL],
        pxtrk=["https://tracker.example.com/pixel"],
    )

    assert event_spec.type == EventType.IMPRESSION
    assert EventTrackingMethod.IMAGE_PIXEL in event_spec.method
    assert event_spec.pxtrk[0] == "https://tracker.example.com/pixel"


def test_display_format_creation() -> None:
    """Test DisplayFormat object creation."""
    display_fmt = DisplayFormat(w=300, h=250)

    assert display_fmt.w == 300
    assert display_fmt.h == 250


def test_native_format_creation() -> None:
    """Test NativeFormat object creation."""
    title_fmt = TitleAssetFormat(len=25, req=1)
    image_fmt = ImageAssetFormat(w=1200, h=627, req=1)
    data_fmt = DataAssetFormat(type=NativeDataAssetType.SPONSORED, len=15, req=0)

    asset_fmt = AssetFormat(id=1, req=1, title=title_fmt, img=image_fmt, data=data_fmt)
    native_fmt = NativeFormat(asset=[asset_fmt], priv=1)

    assert len(native_fmt.asset) == 1
    assert native_fmt.asset[0].title.len == 25
    assert native_fmt.asset[0].img.w == 1200
    assert native_fmt.priv == 1


def test_display_placement_creation() -> None:
    """Test DisplayPlacement object creation."""
    display_fmt = DisplayFormat(w=300, h=250)
    event_spec = EventSpec(type=EventType.IMPRESSION, method=[EventTrackingMethod.IMAGE_PIXEL])

    placement = DisplayPlacement(
        pos=AdPosition.ABOVE_THE_FOLD,
        instl=0,
        w=300,
        h=250,
        displayfmt=[display_fmt],
        event=[event_spec],
    )

    assert placement.pos == AdPosition.ABOVE_THE_FOLD
    assert placement.instl == 0
    assert placement.w == 300
    assert len(placement.displayfmt) == 1
    assert len(placement.event) == 1


def test_video_placement_creation() -> None:
    """Test VideoPlacement object creation."""
    placement = VideoPlacement(
        ptype=VideoPlacementType.IN_STREAM,
        pos=AdPosition.ABOVE_THE_FOLD,
        mindur=15,
        maxdur=30,
        mime=["video/mp4"],
        playmethod=[PlaybackMethod.PAGE_LOAD_SOUND_ON],
        linear=LinearityMode.LINEAR,
        skip=1,
    )

    assert placement.ptype == VideoPlacementType.IN_STREAM
    assert placement.mindur == 15
    assert placement.maxdur == 30
    assert placement.linear == LinearityMode.LINEAR
    assert placement.skip == 1


def test_audio_placement_creation() -> None:
    """Test AudioPlacement object creation."""
    placement = AudioPlacement(
        mindur=15,
        maxdur=30,
        mime=["audio/mp3"],
        playmethod=[PlaybackMethod.PAGE_LOAD_SOUND_ON],
    )

    assert placement.mindur == 15
    assert placement.maxdur == 30
    assert "audio/mp3" in placement.mime


def test_companion_ad_creation() -> None:
    """Test Companion object creation."""
    display_placement = DisplayPlacement(w=300, h=250)
    companion = Companion(id="comp-1", vcm=1, display=display_placement)

    assert companion.id == "comp-1"
    assert companion.vcm == 1
    assert companion.display.w == 300


def test_placement_with_display() -> None:
    """Test Placement object with display subtype."""
    display_placement = DisplayPlacement(w=300, h=250, pos=AdPosition.ABOVE_THE_FOLD)
    placement = Placement(tagid="tag-123", display=display_placement)

    assert placement.tagid == "tag-123"
    assert placement.display.w == 300


def test_placement_with_video() -> None:
    """Test Placement object with video subtype."""
    video_placement = VideoPlacement(
        ptype=VideoPlacementType.IN_STREAM,
        mindur=15,
        maxdur=30,
    )
    placement = Placement(tagid="tag-video-123", video=video_placement)

    assert placement.tagid == "tag-video-123"
    assert placement.video.mindur == 15


def test_placement_with_audio() -> None:
    """Test Placement object with audio subtype."""
    audio_placement = AudioPlacement(mindur=15, maxdur=30)
    placement = Placement(tagid="tag-audio-123", audio=audio_placement)

    assert placement.tagid == "tag-audio-123"
    assert placement.audio.mindur == 15


def test_placement_requires_one_subtype() -> None:
    """Test that Placement requires at least one placement subtype."""
    # No placement subtype
    with pytest.raises(ValueError, match="at least one placement subtype"):
        Placement(tagid="tag-123")


def test_placement_can_have_multiple_subtypes() -> None:
    """Test that Placement can have multiple subtypes."""
    display_placement = DisplayPlacement(w=300, h=250)
    video_placement = VideoPlacement(mindur=15, maxdur=30)

    placement = Placement(tagid="tag-123", display=display_placement, video=video_placement)

    assert placement.display is not None
    assert placement.video is not None


def test_placement_with_secure_flag() -> None:
    """Test Placement with secure flag."""
    display_placement = DisplayPlacement(w=300, h=250)
    placement = Placement(tagid="tag-123", display=display_placement, secure=1)

    assert placement.secure == 1


def test_placement_with_extension() -> None:
    """Test Placement with extension field."""
    display_placement = DisplayPlacement(w=300, h=250)
    placement = Placement(
        tagid="tag-123", display=display_placement, ext={"custom": "placement_data"}
    )

    assert placement.ext["custom"] == "placement_data"


def test_video_placement_with_companion() -> None:
    """Test VideoPlacement with companion ads."""
    display_placement = DisplayPlacement(w=300, h=250)
    companion = Companion(id="comp-1", display=display_placement)

    video_placement = VideoPlacement(
        ptype=VideoPlacementType.IN_STREAM,
        mindur=15,
        maxdur=30,
        comp=[companion],
    )

    assert len(video_placement.comp) == 1
    assert video_placement.comp[0].id == "comp-1"


def test_asset_format_with_multiple_types() -> None:
    """Test AssetFormat with multiple asset types."""
    title_fmt = TitleAssetFormat(len=25)
    image_fmt = ImageAssetFormat(w=1200, h=627)

    asset_fmt = AssetFormat(id=1, title=title_fmt, img=image_fmt)

    assert asset_fmt.title.len == 25
    assert asset_fmt.img.w == 1200


def test_display_placement_with_native_format() -> None:
    """Test DisplayPlacement with native format."""
    title_fmt = TitleAssetFormat(len=25)
    asset_fmt = AssetFormat(id=1, title=title_fmt)
    native_fmt = NativeFormat(asset=[asset_fmt])

    placement = DisplayPlacement(nativefmt=native_fmt)

    assert placement.nativefmt is not None
    assert len(placement.nativefmt.asset) == 1


def test_placement_sdk_fields() -> None:
    """Test Placement with SDK fields."""
    display_placement = DisplayPlacement(w=300, h=250)
    placement = Placement(
        tagid="tag-123",
        display=display_placement,
        sdk="AdSDK",
        sdkver="1.2.3",
    )

    assert placement.sdk == "AdSDK"
    assert placement.sdkver == "1.2.3"


def test_placement_reward_flag() -> None:
    """Test Placement with reward flag."""
    video_placement = VideoPlacement(mindur=15, maxdur=30)
    placement = Placement(tagid="tag-123", video=video_placement, reward=1)

    assert placement.reward == 1
