"""Tests for AdCOM context objects."""


from xsp.standards.adcom.context import (
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
from xsp.standards.adcom.enums import (
    ConnectionType,
    ContentContext,
    DeviceType,
    DOOHVenueType,
    LocationType,
    ProductionQuality,
)


def test_segment_creation() -> None:
    """Test Segment object creation."""
    segment = Segment(id="seg-123", name="Sports Fans", value="1")

    assert segment.id == "seg-123"
    assert segment.name == "Sports Fans"
    assert segment.value == "1"


def test_data_creation() -> None:
    """Test Data object creation."""
    segment = Segment(id="seg-123", name="Sports Fans")
    data = Data(id="data-provider-1", name="Data Provider", segment=[segment])

    assert data.id == "data-provider-1"
    assert data.name == "Data Provider"
    assert len(data.segment) == 1


def test_geo_creation() -> None:
    """Test Geo object creation."""
    geo = Geo(
        type=LocationType.GPS_LOCATION,
        lat=37.7749,
        lon=-122.4194,
        country="USA",
        region="CA",
        city="San Francisco",
        zip="94105",
    )

    assert geo.type == LocationType.GPS_LOCATION
    assert geo.lat == 37.7749
    assert geo.lon == -122.4194
    assert geo.country == "USA"
    assert geo.city == "San Francisco"


def test_brand_version_creation() -> None:
    """Test BrandVersion object creation."""
    brand = BrandVersion(brand="Chrome", version=["96", "0", "4664", "45"])

    assert brand.brand == "Chrome"
    assert brand.version == ["96", "0", "4664", "45"]


def test_user_agent_creation() -> None:
    """Test UserAgent object creation."""
    chrome = BrandVersion(brand="Chrome", version=["96"])
    platform = BrandVersion(brand="Windows", version=["10"])

    ua = UserAgent(browsers=[chrome], platform=platform, mobile=0)

    assert len(ua.browsers) == 1
    assert ua.browsers[0].brand == "Chrome"
    assert ua.platform.brand == "Windows"
    assert ua.mobile == 0


def test_device_creation() -> None:
    """Test Device object creation."""
    geo = Geo(
        type=LocationType.IP_ADDRESS,
        country="USA",
        region="CA",
    )

    device = Device(
        type=DeviceType.PHONE,
        ua="Mozilla/5.0 ...",
        ifa="abc-def-123",
        make="Apple",
        model="iPhone",
        os="iOS",
        osv="15.0",
        w=375,
        h=812,
        ip="192.0.2.1",
        contype=ConnectionType.WIFI,
        geo=geo,
    )

    assert device.type == DeviceType.PHONE
    assert device.make == "Apple"
    assert device.model == "iPhone"
    assert device.os == "iOS"
    assert device.contype == ConnectionType.WIFI
    assert device.geo.country == "USA"


def test_user_creation() -> None:
    """Test User object creation."""
    geo = Geo(country="USA")
    segment = Segment(id="seg-1", name="Tech Enthusiasts")
    data = Data(id="data-1", segment=[segment])

    user = User(
        id="user-123",
        buyeruid="buyer-user-456",
        yob=1990,
        gender="M",
        data=[data],
        geo=geo,
    )

    assert user.id == "user-123"
    assert user.yob == 1990
    assert user.gender == "M"
    assert len(user.data) == 1
    assert user.geo.country == "USA"


def test_producer_creation() -> None:
    """Test Producer object creation."""
    producer = Producer(
        id="prod-123",
        name="Content Producer",
        domain="producer.example.com",
        cat=["IAB1"],
        cattax=2,
    )

    assert producer.id == "prod-123"
    assert producer.name == "Content Producer"
    assert producer.cattax == 2


def test_content_creation() -> None:
    """Test Content object creation."""
    producer = Producer(id="prod-123", name="Producer")
    network = Network(id="net-123", name="Network")
    channel = Channel(id="chan-123", name="Channel")

    content = Content(
        id="content-123",
        title="Great Show",
        series="Show Series",
        season="S01",
        episode=1,
        cat=["IAB1"],
        cattax=2,
        prodq=ProductionQuality.PROFESSIONAL,
        context=ContentContext.VIDEO,
        len=3600,
        producer=producer,
        network=network,
        channel=channel,
    )

    assert content.id == "content-123"
    assert content.title == "Great Show"
    assert content.episode == 1
    assert content.prodq == ProductionQuality.PROFESSIONAL
    assert content.producer.name == "Producer"
    assert content.cattax == 2


def test_publisher_creation() -> None:
    """Test Publisher object creation."""
    publisher = Publisher(
        id="pub-123",
        name="Publisher",
        domain="publisher.example.com",
        cat=["IAB1"],
    )

    assert publisher.id == "pub-123"
    assert publisher.name == "Publisher"


def test_site_creation() -> None:
    """Test Site object creation."""
    publisher = Publisher(id="pub-123", name="Publisher")
    content = Content(id="content-123", title="Article")

    site = Site(
        id="site-123",
        name="Example Site",
        domain="example.com",
        page="https://example.com/page",
        ref="https://google.com",
        cat=["IAB1"],
        cattax=2,
        mobile=0,
        privpolicy=1,
        publisher=publisher,
        content=content,
    )

    assert site.id == "site-123"
    assert site.name == "Example Site"
    assert site.domain == "example.com"
    assert site.publisher.name == "Publisher"
    assert site.cattax == 2


def test_app_creation() -> None:
    """Test App object creation."""
    publisher = Publisher(id="pub-123", name="Publisher")
    content = Content(id="content-123", title="Game")

    app = App(
        id="app-123",
        name="Example App",
        bundle="com.example.app",
        domain="example.com",
        storeurl="https://appstore.com/app",
        cat=["IAB1"],
        ver="1.2.3",
        privpolicy=1,
        paid=0,
        publisher=publisher,
        content=content,
    )

    assert app.id == "app-123"
    assert app.name == "Example App"
    assert app.bundle == "com.example.app"
    assert app.ver == "1.2.3"
    assert app.publisher.name == "Publisher"


def test_dooh_creation() -> None:
    """Test Dooh object creation."""
    publisher = Publisher(id="pub-123", name="DOOH Publisher")
    content = Content(id="content-123", title="DOOH Content")

    dooh = Dooh(
        id="dooh-123",
        name="Airport Display",
        venuetype=[DOOHVenueType.AIRPORT_GENERAL],
        publisher=publisher,
        content=content,
    )

    assert dooh.id == "dooh-123"
    assert dooh.name == "Airport Display"
    assert DOOHVenueType.AIRPORT_GENERAL in dooh.venuetype
    assert dooh.publisher.name == "DOOH Publisher"


def test_restrictions_creation() -> None:
    """Test Restrictions object creation."""
    restrictions = Restrictions(
        bcat=["IAB25", "IAB26"],
        cattax=2,
        badv=["blocked-advertiser.com"],
        bapp=["com.blocked.app"],
        battr=[1, 2, 3],
    )

    assert "IAB25" in restrictions.bcat
    assert restrictions.cattax == 2
    assert "blocked-advertiser.com" in restrictions.badv


def test_regs_creation() -> None:
    """Test Regs object creation."""
    regs = Regs(coppa=1, gdpr=1)

    assert regs.coppa == 1
    assert regs.gdpr == 1


def test_extended_identifiers_creation() -> None:
    """Test ExtendedIdentifiers object creation."""
    eids = ExtendedIdentifiers(
        source="example.com",
        uids=[{"id": "user-123", "atype": "1"}],
    )

    assert eids.source == "example.com"
    assert len(eids.uids) == 1


def test_context_with_extensions() -> None:
    """Test context objects with extensions."""
    site = Site(
        id="site-123",
        domain="example.com",
        ext={"custom": "site_value"},
    )

    assert site.ext["custom"] == "site_value"


def test_content_cattax_default() -> None:
    """Test Content cattax defaults to 2."""
    content = Content(id="content-123", title="Title")

    assert content.cattax == 2


def test_user_with_eids() -> None:
    """Test User with extended identifiers."""
    eids = ExtendedIdentifiers(
        source="id-provider.com",
        uids=[{"id": "user-123"}],
    )

    user = User(id="user-123", eids=[eids])

    assert len(user.eids) == 1
    assert user.eids[0].source == "id-provider.com"


def test_device_with_user_agent_data() -> None:
    """Test Device with structured user agent data."""
    chrome = BrandVersion(brand="Chrome", version=["96"])
    ua_data = UserAgent(browsers=[chrome], mobile=0)

    device = Device(type=DeviceType.PHONE, uadata=ua_data)

    assert device.uadata.browsers[0].brand == "Chrome"
    assert device.uadata.mobile == 0
