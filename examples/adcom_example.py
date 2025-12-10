"""AdCOM 1.0 Usage Examples.

Demonstrates creating and validating AdCOM objects for use with OpenRTB 3.0.
"""

from xsp.standards.adcom import (
    Ad,
    AdPosition,
    ApiFramework,
    App,
    AuditStatusCode,
    Banner,
    ConnectionType,
    Device,
    DeviceType,
    Display,
    DisplayPlacement,
    EventTrackingMethod,
    EventType,
    Geo,
    LinearityMode,
    LocationType,
    Placement,
    PlaybackMethod,
    Publisher,
    Site,
    User,
    Video,
    VideoPlacement,
    VideoPlacementType,
    validate_ad,
    validate_placement,
)
from xsp.standards.adcom.media import Audit, Event


def example_display_ad() -> None:
    """Create a display banner ad."""
    print("=" * 60)
    print("Example 1: Display Banner Ad")
    print("=" * 60)

    # Create a banner display ad
    banner = Banner(
        img="https://cdn.example.com/banners/300x250.jpg",
        w=300,
        h=250,
        link="https://advertiser.example.com/landing",
    )

    display = Display(
        mime="image/jpeg",
        w=300,
        h=250,
        banner=banner,
        event=[
            Event(
                type=EventType.IMPRESSION,
                method=EventTrackingMethod.IMAGE_PIXEL,
                url="https://tracker.example.com/impression?id={AUCTION_ID}",
            )
        ],
    )

    audit = Audit(status=AuditStatusCode.APPROVED, feedback=["Approved for all audiences"])

    ad = Ad(
        id="banner-ad-12345",
        adomain=["advertiser.example.com"],
        cat=["IAB1-1"],  # Arts & Entertainment - Books
        cattax=2,  # IAB Content Category Taxonomy 2.0
        secure=1,  # Requires HTTPS
        display=display,
        audit=audit,
    )

    print(f"Ad ID: {ad.id}")
    print(f"Advertiser Domains: {ad.adomain}")
    print(f"Banner Size: {ad.display.banner.w}x{ad.display.banner.h}")
    print(f"Audit Status: {ad.audit.status.name}")
    print(f"Tracking Events: {len(ad.display.event)}")
    print()


def example_video_ad() -> None:
    """Create a linear video ad with VAST."""
    print("=" * 60)
    print("Example 2: Linear Video Ad")
    print("=" * 60)

    video = Video(
        mime=["video/mp4"],
        api=[ApiFramework.VPAID_2_0, ApiFramework.OMID_1],
        dur=30,
        w=1920,
        h=1080,
        linear=LinearityMode.LINEAR,
        adm="<VAST version='4.0'><!-- VAST XML here --></VAST>",
        curl="https://advertiser.example.com/video-landing",
    )

    ad = Ad(
        id="video-ad-67890",
        adomain=["video-advertiser.example.com"],
        cat=["IAB1-5"],  # Arts & Entertainment - Movies
        video=video,
    )

    print(f"Ad ID: {ad.id}")
    print(f"Video Duration: {ad.video.dur}s")
    print(f"Video Resolution: {ad.video.w}x{ad.video.h}")
    print(f"Linearity: {ad.video.linear.name}")
    print(f"API Frameworks: {[api.name for api in ad.video.api]}")
    print()


def example_display_placement() -> None:
    """Create a display ad placement."""
    print("=" * 60)
    print("Example 3: Display Ad Placement")
    print("=" * 60)

    from xsp.standards.adcom.placement import DisplayFormat, EventSpec

    display_placement = DisplayPlacement(
        pos=AdPosition.ABOVE_THE_FOLD,
        instl=0,  # Not interstitial
        topframe=1,  # In top frame
        w=300,
        h=250,
        mime=["image/jpeg", "image/png", "image/gif"],
        api=[ApiFramework.MRAID_3],
        displayfmt=[
            DisplayFormat(w=300, h=250),
            DisplayFormat(w=728, h=90),
        ],
        event=[
            EventSpec(
                type=EventType.IMPRESSION,
                method=[EventTrackingMethod.IMAGE_PIXEL, EventTrackingMethod.JAVASCRIPT],
            )
        ],
    )

    placement = Placement(
        tagid="placement-display-001",
        secure=1,
        display=display_placement,
    )

    print(f"Placement Tag ID: {placement.tagid}")
    print(f"Ad Position: {placement.display.pos.name}")
    print(f"Accepted Sizes: {[(fmt.w, fmt.h) for fmt in placement.display.displayfmt]}")
    print(f"MIME Types: {placement.display.mime}")
    print()


def example_video_placement() -> None:
    """Create a video ad placement."""
    print("=" * 60)
    print("Example 4: Video Ad Placement")
    print("=" * 60)

    video_placement = VideoPlacement(
        ptype=VideoPlacementType.IN_STREAM,
        pos=AdPosition.ABOVE_THE_FOLD,
        delay=0,  # Pre-roll
        mindur=15,
        maxdur=30,
        skip=1,  # Skippable
        skipafter=5,  # Skip after 5 seconds
        playmethod=[PlaybackMethod.PAGE_LOAD_SOUND_ON],
        mime=["video/mp4", "video/webm"],
        api=[ApiFramework.VPAID_2_0, ApiFramework.OMID_1],
        w=1920,
        h=1080,
        linear=LinearityMode.LINEAR,
    )

    placement = Placement(
        tagid="placement-video-001",
        secure=1,
        video=video_placement,
    )

    print(f"Placement Tag ID: {placement.tagid}")
    print(f"Placement Type: {placement.video.ptype.name}")
    print(f"Duration Range: {placement.video.mindur}s - {placement.video.maxdur}s")
    print(f"Skippable: {'Yes' if placement.video.skip else 'No'}")
    print(f"Skip After: {placement.video.skipafter}s")
    print()


def example_context_objects() -> None:
    """Create context objects (Site, App, User, Device)."""
    print("=" * 60)
    print("Example 5: Context Objects")
    print("=" * 60)

    # Site context
    site = Site(
        id="site-news-001",
        name="Example News Site",
        domain="news.example.com",
        page="https://news.example.com/article/12345",
        cat=["IAB12"],  # News
        mobile=0,
        privpolicy=1,
        publisher=Publisher(
            id="pub-001",
            name="Example Publisher",
            domain="publisher.example.com",
        ),
    )

    # App context
    app = App(
        id="app-game-001",
        name="Example Game",
        bundle="com.example.game",
        storeurl="https://play.google.com/store/apps/details?id=com.example.game",
        cat=["IAB9"],  # Gaming
        ver="2.1.0",
        privpolicy=1,
        paid=0,
    )

    # Device
    device = Device(
        type=DeviceType.PHONE,
        ua="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)...",
        ifa="abc-def-12345",
        make="Apple",
        model="iPhone 13",
        os="iOS",
        osv="15.0",
        w=375,
        h=812,
        ip="192.0.2.1",
        contype=ConnectionType.WIFI,
        geo=Geo(
            type=LocationType.GPS_LOCATION,
            lat=37.7749,
            lon=-122.4194,
            country="USA",
            region="CA",
            city="San Francisco",
        ),
    )

    # User
    user = User(
        id="user-abc123",
        yob=1990,
        gender="M",
    )

    print(f"Site: {site.name} ({site.domain})")
    print(f"App: {app.name} v{app.ver} ({app.bundle})")
    print(f"Device: {device.make} {device.model} ({device.os} {device.osv})")
    print(f"Location: {device.geo.city}, {device.geo.region}")
    print(f"User: YOB={user.yob}, Gender={user.gender}")
    print()


def example_validation() -> None:
    """Demonstrate validation of AdCOM objects."""
    print("=" * 60)
    print("Example 6: Validation")
    print("=" * 60)

    # Valid ad data
    ad_data = {
        "id": "ad-valid-001",
        "adomain": ["example.com"],
        "display": {"mime": "image/jpeg", "w": 300, "h": 250},
    }

    try:
        ad = validate_ad(ad_data)
        print(f"✓ Ad validation successful: {ad.id}")
    except Exception as e:
        print(f"✗ Ad validation failed: {e}")

    # Invalid ad data (missing required media subtype)
    invalid_ad_data = {"id": "ad-invalid-001"}

    try:
        ad = validate_ad(invalid_ad_data)
        print(f"✓ Ad validation successful: {ad.id}")
    except Exception as e:
        print(f"✗ Ad validation failed (expected): {type(e).__name__}")

    # Valid placement data
    placement_data = {
        "tagid": "tag-001",
        "display": {"w": 300, "h": 250},
    }

    try:
        placement = validate_placement(placement_data)
        print(f"✓ Placement validation successful: {placement.tagid}")
    except Exception as e:
        print(f"✗ Placement validation failed: {e}")

    print()


def example_openrtb_integration() -> None:
    """Show how AdCOM integrates with OpenRTB 3.0."""
    print("=" * 60)
    print("Example 7: OpenRTB 3.0 Integration Pattern")
    print("=" * 60)

    print(
        """
In OpenRTB 3.0, AdCOM objects are used as follows:

Bid Request (from SSP):
{
  "id": "bid-request-123",
  "tmax": 150,
  "source": {...},
  "item": [
    {
      "id": "item-1",
      "qty": 1,
      "spec": {
        "placement": <AdCOM Placement object>  # VideoPlacement, DisplayPlacement, etc.
      }
    }
  ],
  "context": {
    "site": <AdCOM Site object>,
    "device": <AdCOM Device object>,
    "user": <AdCOM User object>,
    "regs": <AdCOM Regs object>
  }
}

Bid Response (from DSP):
{
  "id": "bid-request-123",
  "bidid": "bid-response-456",
  "seatbid": [
    {
      "seat": "dsp-seat-1",
      "bid": [
        {
          "id": "bid-1",
          "item": "item-1",
          "price": 2.50,
          "media": <AdCOM Ad object>  # Video ad, Display ad, etc.
        }
      ]
    }
  ]
}

The AdCOM objects provide structured, validated representations that work
across different transaction protocols (OpenRTB, CATS, OpenDirect).
"""
    )


def main() -> None:
    """Run all examples."""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "AdCOM 1.0 Usage Examples" + " " * 24 + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    example_display_ad()
    example_video_ad()
    example_display_placement()
    example_video_placement()
    example_context_objects()
    example_validation()
    example_openrtb_integration()

    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
