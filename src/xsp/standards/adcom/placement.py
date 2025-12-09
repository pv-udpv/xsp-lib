"""AdCOM 1.0 Placement Objects.

Placement objects define permitted ads for an impression: sizes, formats, restrictions.
"""

from pydantic import Field

from .enums import (
    AdPosition,
    ApiFramework,
    CompanionType,
    CreativeAttribute,
    EventTrackingMethod,
    EventType,
    ExpandableDirection,
    LinearityMode,
    NativeDataAssetType,
    PlaybackCessationMode,
    PlaybackMethod,
    VideoPlacementType,
)
from .types import AdComModel


class EventSpec(AdComModel):
    """Event tracking specification.

    Attributes:
        type: Type of event to track
        method: Tracking methods
        api: API frameworks for JS
        jstrk: JavaScript trackers
        wjs: HTTPS required for JS trackers (0=no, 1=yes)
        pxtrk: Pixel trackers
        wpx: HTTPS required for pixel trackers (0=no, 1=yes)
    """

    type: EventType = Field(description="Type of event to track")
    method: list[EventTrackingMethod] | None = Field(default=None, description="Tracking methods")
    api: list[ApiFramework] | None = Field(default=None, description="API frameworks for JS")
    jstrk: list[str] | None = Field(default=None, description="JavaScript trackers")
    wjs: int | None = Field(default=None, description="HTTPS required for JS trackers")
    pxtrk: list[str] | None = Field(default=None, description="Pixel trackers")
    wpx: int | None = Field(default=None, description="HTTPS required for pixel trackers")


class Companion(AdComModel):
    """Companion ad specification for video/audio.

    Attributes:
        id: Companion ID
        vcm: Video completion required (0=no, 1=yes)
        display: Display placement object
    """

    id: str | None = Field(default=None, description="Companion ID")
    vcm: int | None = Field(default=None, description="Video completion required")
    display: "DisplayPlacement | None" = Field(default=None, description="Display placement")


class TitleAssetFormat(AdComModel):
    """Native title asset format.

    Attributes:
        len: Maximum length of title text
        req: Required (0=optional, 1=required)
    """

    len: int = Field(description="Maximum length of title text")
    req: int | None = Field(default=0, description="Required (0=optional, 1=required)")


class ImageAssetFormat(AdComModel):
    """Native image asset format.

    Attributes:
        type: Type of image (icon vs main)
        mime: MIME types
        w: Width in pixels
        h: Height in pixels
        wmin: Minimum width
        hmin: Minimum height
        wratio: Width ratio
        hratio: Height ratio
        req: Required (0=optional, 1=required)
    """

    type: int | None = Field(default=None, description="Type of image")
    mime: list[str] | None = Field(default=None, description="MIME types")
    w: int | None = Field(default=None, description="Width in pixels")
    h: int | None = Field(default=None, description="Height in pixels")
    wmin: int | None = Field(default=None, description="Minimum width")
    hmin: int | None = Field(default=None, description="Minimum height")
    wratio: int | None = Field(default=None, description="Width ratio")
    hratio: int | None = Field(default=None, description="Height ratio")
    req: int | None = Field(default=0, description="Required (0=optional, 1=required)")


class VideoAssetFormat(AdComModel):
    """Native video asset format.

    Attributes:
        mime: MIME types
        mindur: Minimum duration
        maxdur: Maximum duration
        protocols: Protocols (VAST versions)
        w: Width
        h: Height
        req: Required (0=optional, 1=required)
    """

    mime: list[str] | None = Field(default=None, description="MIME types")
    mindur: int | None = Field(default=None, description="Minimum duration")
    maxdur: int | None = Field(default=None, description="Maximum duration")
    protocols: list[int] | None = Field(default=None, description="Protocols (VAST versions)")
    w: int | None = Field(default=None, description="Width")
    h: int | None = Field(default=None, description="Height")
    req: int | None = Field(default=0, description="Required (0=optional, 1=required)")


class DataAssetFormat(AdComModel):
    """Native data asset format.

    Attributes:
        type: Type of data
        len: Maximum length of value
        req: Required (0=optional, 1=required)
    """

    type: NativeDataAssetType = Field(description="Type of data")
    len: int | None = Field(default=None, description="Maximum length of value")
    req: int | None = Field(default=0, description="Required (0=optional, 1=required)")


class AssetFormat(AdComModel):
    """Native asset format container.

    Attributes:
        id: Asset format ID
        req: Required (0=optional, 1=required)
        title: Title format
        img: Image format
        video: Video format
        data: Data format
    """

    id: int | None = Field(default=None, description="Asset format ID")
    req: int | None = Field(default=0, description="Required (0=optional, 1=required)")
    title: TitleAssetFormat | None = Field(default=None, description="Title format")
    img: ImageAssetFormat | None = Field(default=None, description="Image format")
    video: VideoAssetFormat | None = Field(default=None, description="Video format")
    data: DataAssetFormat | None = Field(default=None, description="Data format")


class NativeFormat(AdComModel):
    """Native ad format specification.

    Attributes:
        asset: Array of asset formats
        priv: Privacy policy required (0=no, 1=yes)
    """

    asset: list[AssetFormat] | None = Field(default=None, description="Array of asset formats")
    priv: int | None = Field(default=None, description="Privacy policy required")


class DisplayFormat(AdComModel):
    """Display format specification.

    Attributes:
        w: Width
        h: Height
        wratio: Width ratio
        hratio: Height ratio
        expdir: Expandable directions
    """

    w: int | None = Field(default=None, description="Width")
    h: int | None = Field(default=None, description="Height")
    wratio: int | None = Field(default=None, description="Width ratio")
    hratio: int | None = Field(default=None, description="Height ratio")
    expdir: list[ExpandableDirection] | None = Field(
        default=None, description="Expandable directions"
    )


class DisplayPlacement(AdComModel):
    """Display placement specification.

    Attributes:
        pos: Ad position
        instl: Interstitial (0=no, 1=yes)
        topframe: Top frame (0=no, 1=yes)
        ifrbust: iFrame busting (0=no, 1=yes)
        clktype: Click type (0=non-clickable, 1=clickable)
        ampren: AMP rendering (0=no, 1=yes)
        ptype: Placement type
        context: Context type
        mime: MIME types
        api: API frameworks
        ctype: Creative types
        w: Width
        h: Height
        wratio: Width ratio for responsive
        hratio: Height ratio for responsive
        priv: Privacy supported (0=no, 1=yes)
        displayfmt: Display formats
        nativefmt: Native format
        event: Event specs
    """

    pos: AdPosition | None = Field(default=None, description="Ad position")
    instl: int | None = Field(default=0, description="Interstitial (0=no, 1=yes)")
    topframe: int | None = Field(default=None, description="Top frame (0=no, 1=yes)")
    ifrbust: list[str] | None = Field(default=None, description="iFrame busting")
    clktype: int | None = Field(default=None, description="Click type")
    ampren: int | None = Field(default=None, description="AMP rendering (0=no, 1=yes)")
    ptype: int | None = Field(default=None, description="Placement type")
    context: int | None = Field(default=None, description="Context type")
    mime: list[str] | None = Field(default=None, description="MIME types")
    api: list[ApiFramework] | None = Field(default=None, description="API frameworks")
    ctype: list[int] | None = Field(default=None, description="Creative types")
    w: int | None = Field(default=None, description="Width")
    h: int | None = Field(default=None, description="Height")
    wratio: int | None = Field(default=None, description="Width ratio for responsive")
    hratio: int | None = Field(default=None, description="Height ratio for responsive")
    priv: int | None = Field(default=None, description="Privacy supported (0=no, 1=yes)")
    displayfmt: list[DisplayFormat] | None = Field(default=None, description="Display formats")
    nativefmt: NativeFormat | None = Field(default=None, description="Native format")
    event: list[EventSpec] | None = Field(default=None, description="Event specs")


class VideoPlacement(AdComModel):
    """Video placement specification.

    Attributes:
        ptype: Placement type
        pos: Ad position
        delay: Pre-roll delay (seconds, -1=mid/post, -2=unknown)
        skip: Skippable (0=no, 1=yes)
        skipmin: Minimum duration before skip
        skipafter: Duration after which skip is enabled
        playmethod: Playback methods
        playend: Playback cessation mode
        clktype: Click type
        mime: MIME types
        api: API frameworks
        ctype: Creative types
        w: Width
        h: Height
        unit: Size units (1=px, 2=%, 3=dip)
        mindur: Minimum duration
        maxdur: Maximum duration
        maxext: Maximum extended duration
        minbitrate: Minimum bitrate
        maxbitrate: Maximum bitrate
        delivery: Delivery methods
        maxseq: Maximum ad sequence
        linear: Linearity
        boxing: Letterboxing allowed (0=no, 1=yes)
        comp: Companion ads
        comptype: Companion types
        event: Event specs
    """

    ptype: VideoPlacementType | None = Field(default=None, description="Placement type")
    pos: AdPosition | None = Field(default=None, description="Ad position")
    delay: int | None = Field(default=None, description="Pre-roll delay")
    skip: int | None = Field(default=None, description="Skippable (0=no, 1=yes)")
    skipmin: int | None = Field(default=None, description="Minimum duration before skip")
    skipafter: int | None = Field(default=None, description="Duration after skip enabled")
    playmethod: list[PlaybackMethod] | None = Field(default=None, description="Playback methods")
    playend: PlaybackCessationMode | None = Field(
        default=None, description="Playback cessation mode"
    )
    clktype: int | None = Field(default=None, description="Click type")
    mime: list[str] | None = Field(default=None, description="MIME types")
    api: list[ApiFramework] | None = Field(default=None, description="API frameworks")
    ctype: list[int] | None = Field(default=None, description="Creative types")
    w: int | None = Field(default=None, description="Width")
    h: int | None = Field(default=None, description="Height")
    unit: int | None = Field(default=None, description="Size units")
    mindur: int | None = Field(default=None, description="Minimum duration")
    maxdur: int | None = Field(default=None, description="Maximum duration")
    maxext: int | None = Field(default=None, description="Maximum extended duration")
    minbitrate: int | None = Field(default=None, description="Minimum bitrate")
    maxbitrate: int | None = Field(default=None, description="Maximum bitrate")
    delivery: list[int] | None = Field(default=None, description="Delivery methods")
    maxseq: int | None = Field(default=None, description="Maximum ad sequence")
    linear: LinearityMode | None = Field(default=None, description="Linearity")
    boxing: int | None = Field(default=None, description="Letterboxing allowed")
    comp: list[Companion] | None = Field(default=None, description="Companion ads")
    comptype: list[CompanionType] | None = Field(default=None, description="Companion types")
    event: list[EventSpec] | None = Field(default=None, description="Event specs")


class AudioPlacement(AdComModel):
    """Audio placement specification.

    Attributes:
        delay: Pre-roll delay (seconds, -1=mid/post, -2=unknown)
        skip: Skippable (0=no, 1=yes)
        skipmin: Minimum duration before skip
        skipafter: Duration after which skip is enabled
        playmethod: Playback methods
        playend: Playback cessation mode
        feed: Feed type
        nvol: Volume normalization mode
        mime: MIME types
        api: API frameworks
        ctype: Creative types
        mindur: Minimum duration
        maxdur: Maximum duration
        maxext: Maximum extended duration
        minbitrate: Minimum bitrate
        maxbitrate: Maximum bitrate
        delivery: Delivery methods
        maxseq: Maximum ad sequence
        comp: Companion ads
        comptype: Companion types
        event: Event specs
    """

    delay: int | None = Field(default=None, description="Pre-roll delay")
    skip: int | None = Field(default=None, description="Skippable (0=no, 1=yes)")
    skipmin: int | None = Field(default=None, description="Minimum duration before skip")
    skipafter: int | None = Field(default=None, description="Duration after skip enabled")
    playmethod: list[PlaybackMethod] | None = Field(default=None, description="Playback methods")
    playend: PlaybackCessationMode | None = Field(
        default=None, description="Playback cessation mode"
    )
    feed: int | None = Field(default=None, description="Feed type")
    nvol: int | None = Field(default=None, description="Volume normalization mode")
    mime: list[str] | None = Field(default=None, description="MIME types")
    api: list[ApiFramework] | None = Field(default=None, description="API frameworks")
    ctype: list[int] | None = Field(default=None, description="Creative types")
    mindur: int | None = Field(default=None, description="Minimum duration")
    maxdur: int | None = Field(default=None, description="Maximum duration")
    maxext: int | None = Field(default=None, description="Maximum extended duration")
    minbitrate: int | None = Field(default=None, description="Minimum bitrate")
    maxbitrate: int | None = Field(default=None, description="Maximum bitrate")
    delivery: list[int] | None = Field(default=None, description="Delivery methods")
    maxseq: int | None = Field(default=None, description="Maximum ad sequence")
    comp: list[Companion] | None = Field(default=None, description="Companion ads")
    comptype: list[CompanionType] | None = Field(default=None, description="Companion types")
    event: list[EventSpec] | None = Field(default=None, description="Event specs")


class Placement(AdComModel):
    """Root Placement object.

    A Placement describes an ad slot. It must contain exactly one
    placement subtype (display, video, or audio).

    Attributes:
        tagid: Tag ID
        ssai: Server-side ad insertion (0=no, 1=yes)
        sdk: SDK name
        sdkver: SDK version
        reward: Rewarded (0=no, 1=yes)
        wlang: Whitelist of languages
        secure: HTTPS required (0=no, 1=yes, omit=unknown)
        admx: Markup allowed (0=no, 1=yes)
        curlx: Click-through URLs allowed (0=no, 1=yes)
        display: Display placement
        video: Video placement
        audio: Audio placement
    """

    tagid: str | None = Field(default=None, description="Tag ID")
    ssai: int | None = Field(default=None, description="Server-side ad insertion")
    sdk: str | None = Field(default=None, description="SDK name")
    sdkver: str | None = Field(default=None, description="SDK version")
    reward: int | None = Field(default=None, description="Rewarded (0=no, 1=yes)")
    wlang: list[str] | None = Field(default=None, description="Whitelist of languages")
    secure: int | None = Field(default=None, description="HTTPS required")
    admx: int | None = Field(default=None, description="Markup allowed (0=no, 1=yes)")
    curlx: int | None = Field(default=None, description="Click-through URLs allowed")
    display: DisplayPlacement | None = Field(default=None, description="Display placement")
    video: VideoPlacement | None = Field(default=None, description="Video placement")
    audio: AudioPlacement | None = Field(default=None, description="Audio placement")

    def model_post_init(self, __context: object) -> None:
        """Validate at least one placement subtype is present."""
        placement_types = sum(
            [
                self.display is not None,
                self.video is not None,
                self.audio is not None,
            ]
        )
        if placement_types == 0:
            raise ValueError(
                "Placement must contain at least one placement subtype (display, video, or audio)"
            )
