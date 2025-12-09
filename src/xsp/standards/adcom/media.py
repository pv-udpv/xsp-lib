"""AdCOM 1.0 Media Objects.

Media objects define actual ads: creatives, rendering metadata, tracking, audit.
"""

from typing import Literal

from pydantic import Field, field_validator

from .enums import (
    ApiFramework,
    AuditStatusCode,
    CreativeAttribute,
    EventTrackingMethod,
    EventType,
    LinearityMode,
    NativeDataAssetType,
)
from .types import AdComModel


class Event(AdComModel):
    """Event tracking object.

    Attributes:
        type: Type of event to track
        method: Method of tracking (pixel, JS)
        api: API frameworks for JS events
        url: Tracking URL template
        cdata: Optional custom data
    """

    type: EventType = Field(description="Type of event to track")
    method: EventTrackingMethod = Field(description="Method of tracking")
    api: list[ApiFramework] | None = Field(
        default=None, description="API frameworks for JS events"
    )
    url: str | None = Field(default=None, description="Tracking URL template")
    cdata: dict[str, str] | None = Field(default=None, description="Custom data")


class Audit(AdComModel):
    """Ad quality and compliance audit information.

    Attributes:
        status: Audit status code
        feedback: Feedback from auditor
        init: Date/time of initial submission (Unix timestamp)
        lastmod: Date/time of last modification (Unix timestamp)
        corr: Correction requested
    """

    status: AuditStatusCode | None = Field(default=None, description="Audit status code")
    feedback: list[str] | None = Field(default=None, description="Feedback from auditor")
    init: int | None = Field(
        default=None, description="Date/time of initial submission (Unix timestamp)"
    )
    lastmod: int | None = Field(
        default=None, description="Date/time of last modification (Unix timestamp)"
    )
    corr: str | None = Field(default=None, description="Correction requested")


class Banner(AdComModel):
    """Banner display ad.

    Attributes:
        img: Image URL
        w: Width in device independent pixels
        h: Height in device independent pixels
        link: Destination URL
    """

    img: str | None = Field(default=None, description="Image URL")
    w: int | None = Field(default=None, description="Width in pixels")
    h: int | None = Field(default=None, description="Height in pixels")
    link: str | None = Field(default=None, description="Destination URL")


class TitleAsset(AdComModel):
    """Native title asset.

    Attributes:
        text: The text of the title
        len: Length of title text
    """

    text: str = Field(description="The text of the title")
    len: int | None = Field(default=None, description="Length of title text")


class ImageAsset(AdComModel):
    """Native image asset.

    Attributes:
        url: URL of the image
        w: Width in pixels
        h: Height in pixels
        type: Type code (icon vs main image)
    """

    url: str = Field(description="URL of the image")
    w: int | None = Field(default=None, description="Width in pixels")
    h: int | None = Field(default=None, description="Height in pixels")
    type: int | None = Field(default=None, description="Type code")


class VideoAsset(AdComModel):
    """Native video asset.

    Attributes:
        adm: Video markup (VAST XML)
        curl: Click-through URL
    """

    adm: str | None = Field(default=None, description="Video markup (VAST XML)")
    curl: str | None = Field(default=None, description="Click-through URL")


class DataAsset(AdComModel):
    """Native data asset.

    Attributes:
        value: Formatted string of data
        type: Type of data (e.g., sponsored, desc, rating)
        len: Length of value
    """

    value: str = Field(description="Formatted string of data")
    type: NativeDataAssetType | None = Field(default=None, description="Type of data")
    len: int | None = Field(default=None, description="Length of value")


class LinkAsset(AdComModel):
    """Native link asset.

    Attributes:
        url: Landing URL
        urlfb: Fallback URL
        trkr: Tracking URLs
    """

    url: str = Field(description="Landing URL")
    urlfb: str | None = Field(default=None, description="Fallback URL")
    trkr: list[str] | None = Field(default=None, description="Tracking URLs")


class Asset(AdComModel):
    """Native asset container.

    Attributes:
        id: Asset ID
        req: Required flag (0=optional, 1=required)
        title: Title asset
        img: Image asset
        video: Video asset
        data: Data asset
        link: Link asset
    """

    id: int | None = Field(default=None, description="Asset ID")
    req: int | None = Field(default=0, description="Required flag")
    title: TitleAsset | None = Field(default=None, description="Title asset")
    img: ImageAsset | None = Field(default=None, description="Image asset")
    video: VideoAsset | None = Field(default=None, description="Video asset")
    data: DataAsset | None = Field(default=None, description="Data asset")
    link: LinkAsset | None = Field(default=None, description="Link asset")

    @field_validator("req")
    @classmethod
    def validate_req(cls, v: int | None) -> int:
        """Validate req is 0 or 1."""
        if v is not None and v not in (0, 1):
            raise ValueError("req must be 0 or 1")
        return v or 0


class Native(AdComModel):
    """Native ad format.

    Attributes:
        link: Link object
        assets: Array of asset objects
        priv: Privacy/terms URL
    """

    link: LinkAsset | None = Field(default=None, description="Link object")
    assets: list[Asset] | None = Field(default=None, description="Array of asset objects")
    priv: str | None = Field(default=None, description="Privacy/terms URL")


class Display(AdComModel):
    """Display ad.

    Attributes:
        mime: MIME type
        api: API frameworks
        type: Creative type (banner vs native)
        w: Width
        h: Height
        wratio: Width ratio for responsive
        hratio: Height ratio for responsive
        adm: Ad markup
        curl: Click-through URL
        banner: Banner object
        native: Native object
        event: Event trackers
    """

    mime: str | None = Field(default=None, description="MIME type")
    api: list[ApiFramework] | None = Field(default=None, description="API frameworks")
    type: int | None = Field(default=None, description="Creative type")
    w: int | None = Field(default=None, description="Width")
    h: int | None = Field(default=None, description="Height")
    wratio: int | None = Field(default=None, description="Width ratio for responsive")
    hratio: int | None = Field(default=None, description="Height ratio for responsive")
    adm: str | None = Field(default=None, description="Ad markup")
    curl: str | None = Field(default=None, description="Click-through URL")
    banner: Banner | None = Field(default=None, description="Banner object")
    native: Native | None = Field(default=None, description="Native object")
    event: list[Event] | None = Field(default=None, description="Event trackers")


class Video(AdComModel):
    """Video ad.

    Attributes:
        mime: MIME types
        api: API frameworks
        type: Creative type
        adm: Video markup (VAST)
        curl: Click-through URL
        protocol: Protocol (VAST version)
        w: Width
        h: Height
        dur: Duration in seconds
        bitrate: Bitrate in kbps
        mindur: Minimum duration
        maxdur: Maximum duration
        maxext: Maximum extended duration
        minbitrate: Minimum bitrate
        maxbitrate: Maximum bitrate
        delivery: Delivery methods
        maxseq: Maximum ad sequence
        linear: Linearity
        skip: Skippable (0=no, 1=yes)
        skipmin: Minimum duration before skip
        skipafter: Duration after which skip is enabled
        boxing: Letterboxing/pillarboxing allowed
        comp: Companion ads
        event: Event trackers
    """

    mime: list[str] | None = Field(default=None, description="MIME types")
    api: list[ApiFramework] | None = Field(default=None, description="API frameworks")
    type: int | None = Field(default=None, description="Creative type")
    adm: str | None = Field(default=None, description="Video markup (VAST)")
    curl: str | None = Field(default=None, description="Click-through URL")
    protocol: int | None = Field(default=None, description="Protocol (VAST version)")
    w: int | None = Field(default=None, description="Width")
    h: int | None = Field(default=None, description="Height")
    dur: int | None = Field(default=None, description="Duration in seconds")
    bitrate: int | None = Field(default=None, description="Bitrate in kbps")
    mindur: int | None = Field(default=None, description="Minimum duration")
    maxdur: int | None = Field(default=None, description="Maximum duration")
    maxext: int | None = Field(default=None, description="Maximum extended duration")
    minbitrate: int | None = Field(default=None, description="Minimum bitrate")
    maxbitrate: int | None = Field(default=None, description="Maximum bitrate")
    delivery: list[int] | None = Field(default=None, description="Delivery methods")
    maxseq: int | None = Field(default=None, description="Maximum ad sequence")
    linear: LinearityMode | None = Field(default=None, description="Linearity")
    skip: int | None = Field(default=None, description="Skippable (0=no, 1=yes)")
    skipmin: int | None = Field(default=None, description="Minimum duration before skip")
    skipafter: int | None = Field(default=None, description="Duration after skip enabled")
    boxing: int | None = Field(default=None, description="Letterboxing allowed")
    comp: list["Display"] | None = Field(default=None, description="Companion ads")
    event: list[Event] | None = Field(default=None, description="Event trackers")


class Audio(AdComModel):
    """Audio ad.

    Attributes:
        mime: MIME types
        api: API frameworks
        adm: Audio markup
        curl: Click-through URL
        dur: Duration in seconds
        bitrate: Bitrate in kbps
        mindur: Minimum duration
        maxdur: Maximum duration
        maxext: Maximum extended duration
        minbitrate: Minimum bitrate
        maxbitrate: Maximum bitrate
        delivery: Delivery methods
        maxseq: Maximum ad sequence
        comp: Companion ads
        event: Event trackers
    """

    mime: list[str] | None = Field(default=None, description="MIME types")
    api: list[ApiFramework] | None = Field(default=None, description="API frameworks")
    adm: str | None = Field(default=None, description="Audio markup")
    curl: str | None = Field(default=None, description="Click-through URL")
    dur: int | None = Field(default=None, description="Duration in seconds")
    bitrate: int | None = Field(default=None, description="Bitrate in kbps")
    mindur: int | None = Field(default=None, description="Minimum duration")
    maxdur: int | None = Field(default=None, description="Maximum duration")
    maxext: int | None = Field(default=None, description="Maximum extended duration")
    minbitrate: int | None = Field(default=None, description="Minimum bitrate")
    maxbitrate: int | None = Field(default=None, description="Maximum bitrate")
    delivery: list[int] | None = Field(default=None, description="Delivery methods")
    maxseq: int | None = Field(default=None, description="Maximum ad sequence")
    comp: list[Display] | None = Field(default=None, description="Companion ads")
    event: list[Event] | None = Field(default=None, description="Event trackers")


class Ad(AdComModel):
    """Root Ad object.

    An Ad represents a single creative unit. It must contain exactly one
    media subtype (display, video, or audio).

    Attributes:
        id: Ad ID
        adomain: Advertiser domains
        bundle: App bundle/package name
        iurl: Image URL for content review
        cat: IAB content categories
        cattax: Category taxonomy (default 2)
        lang: Language (ISO-639-1)
        attr: Creative attributes
        secure: HTTPS required (0=no, 1=yes, omit=unknown)
        mrating: Media rating
        init: Initial submission timestamp
        lastmod: Last modification timestamp
        display: Display ad object
        video: Video ad object
        audio: Audio ad object
        audit: Audit object
    """

    id: str = Field(description="Ad ID")
    adomain: list[str] | None = Field(default=None, description="Advertiser domains")
    bundle: str | None = Field(default=None, description="App bundle/package name")
    iurl: str | None = Field(default=None, description="Image URL for content review")
    cat: list[str] | None = Field(default=None, description="IAB content categories")
    cattax: int | None = Field(default=2, description="Category taxonomy")
    lang: str | None = Field(default=None, description="Language (ISO-639-1)")
    attr: list[CreativeAttribute] | None = Field(
        default=None, description="Creative attributes"
    )
    secure: Literal[0, 1] | None = Field(
        default=None, description="HTTPS required (0=no, 1=yes, omit=unknown)"
    )
    mrating: int | None = Field(default=None, description="Media rating")
    init: int | None = Field(default=None, description="Initial submission timestamp")
    lastmod: int | None = Field(default=None, description="Last modification timestamp")
    display: Display | None = Field(default=None, description="Display ad object")
    video: Video | None = Field(default=None, description="Video ad object")
    audio: Audio | None = Field(default=None, description="Audio ad object")
    audit: Audit | None = Field(default=None, description="Audit object")

    @field_validator("cattax")
    @classmethod
    def validate_cattax_default(cls, v: int | None) -> int:
        """Default cattax to 2 if not specified."""
        return v if v is not None else 2

    def model_post_init(self, __context: object) -> None:
        """Validate exactly one media subtype is present."""
        media_types = sum(
            [
                self.display is not None,
                self.video is not None,
                self.audio is not None,
            ]
        )
        if media_types != 1:
            raise ValueError("Ad must contain exactly one media subtype (display, video, or audio)")
