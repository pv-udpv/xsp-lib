"""AdCOM 1.0 Context Objects.

Context objects describe the environment: user, device, location, content, channel, regulations.
"""

from pydantic import Field

from .enums import (
    CategoryTaxonomy,
    ConnectionType,
    ContentContext,
    DeliveryMethod,
    DeviceType,
    DOOHVenueType,
    FeedType,
    LocationType,
    MediaRating,
    ProductionQuality,
    QAGMediaRating,
    VolumeNormalizationMode,
)
from .types import AdComModel


class Segment(AdComModel):
    """Data segment.

    Attributes:
        id: Segment ID
        name: Segment name
        value: Segment value
    """

    id: str | None = Field(default=None, description="Segment ID")
    name: str | None = Field(default=None, description="Segment name")
    value: str | None = Field(default=None, description="Segment value")


class Data(AdComModel):
    """Data object.

    Attributes:
        id: Data source ID
        name: Data source name
        segment: Array of segments
    """

    id: str | None = Field(default=None, description="Data source ID")
    name: str | None = Field(default=None, description="Data source name")
    segment: list[Segment] | None = Field(default=None, description="Array of segments")


class ExtendedIdentifiers(AdComModel):
    """Extended identifiers (eids).

    Attributes:
        source: Source ID
        uids: User IDs
    """

    source: str | None = Field(default=None, description="Source ID")
    uids: list[dict[str, str]] | None = Field(default=None, description="User IDs")


class Geo(AdComModel):
    """Geographic location.

    Attributes:
        type: Location type
        lat: Latitude
        lon: Longitude
        accur: Accuracy in meters
        lastfix: Last fix timestamp (Unix)
        ipserv: IP service type
        country: Country (ISO-3166-1 alpha-3)
        region: Region (ISO-3166-2)
        metro: Metro/DMA code
        city: City
        zip: ZIP/postal code
        utcoffset: UTC offset in minutes
    """

    type: LocationType | None = Field(default=None, description="Location type")
    lat: float | None = Field(default=None, description="Latitude")
    lon: float | None = Field(default=None, description="Longitude")
    accur: int | None = Field(default=None, description="Accuracy in meters")
    lastfix: int | None = Field(default=None, description="Last fix timestamp")
    ipserv: int | None = Field(default=None, description="IP service type")
    country: str | None = Field(default=None, description="Country (ISO-3166-1 alpha-3)")
    region: str | None = Field(default=None, description="Region (ISO-3166-2)")
    metro: str | None = Field(default=None, description="Metro/DMA code")
    city: str | None = Field(default=None, description="City")
    zip: str | None = Field(default=None, description="ZIP/postal code")
    utcoffset: int | None = Field(default=None, description="UTC offset in minutes")


class BrandVersion(AdComModel):
    """Browser brand and version.

    Attributes:
        brand: Browser brand
        version: Browser version
    """

    brand: str = Field(description="Browser brand")
    version: list[str] | None = Field(default=None, description="Browser version")


class UserAgent(AdComModel):
    """User agent information.

    Attributes:
        browsers: Browser brands and versions
        platform: Platform object
        mobile: Mobile indicator (0=no, 1=yes)
        architecture: Device architecture
        bitness: CPU bitness
        model: Device model
        source: Source of UA data
    """

    browsers: list[BrandVersion] | None = Field(
        default=None, description="Browser brands and versions"
    )
    platform: "BrandVersion | None" = Field(default=None, description="Platform object")
    mobile: int | None = Field(default=None, description="Mobile indicator (0=no, 1=yes)")
    architecture: str | None = Field(default=None, description="Device architecture")
    bitness: str | None = Field(default=None, description="CPU bitness")
    model: str | None = Field(default=None, description="Device model")
    source: int | None = Field(default=None, description="Source of UA data")


class Device(AdComModel):
    """Device information.

    Attributes:
        type: Device type
        ua: User agent string
        uadata: User agent data (structured)
        ifa: ID for advertising
        dnt: Do not track (0=no, 1=yes)
        lmt: Limit ad tracking (0=no, 1=yes)
        make: Device make
        model: Device model
        os: Operating system
        osv: OS version
        hwv: Hardware version
        h: Screen height
        w: Screen width
        ppi: Pixels per inch
        pxratio: Pixel ratio
        js: JavaScript supported (0=no, 1=yes)
        lang: Language (BCP-47)
        ip: IPv4 address
        ipv6: IPv6 address
        xff: X-Forwarded-For
        iptr: IP truncation (0=none, 1=last octet, 2=last 2 octets, 3=last 3 octets)
        carrier: Carrier/ISP
        mccmnc: Mobile country/network code
        contype: Connection type
        geofetch: Allow geo fetch (0=no, 1=yes)
        geo: Geographic location
    """

    type: DeviceType | None = Field(default=None, description="Device type")
    ua: str | None = Field(default=None, description="User agent string")
    uadata: UserAgent | None = Field(default=None, description="User agent data (structured)")
    ifa: str | None = Field(default=None, description="ID for advertising")
    dnt: int | None = Field(default=None, description="Do not track (0=no, 1=yes)")
    lmt: int | None = Field(default=None, description="Limit ad tracking (0=no, 1=yes)")
    make: str | None = Field(default=None, description="Device make")
    model: str | None = Field(default=None, description="Device model")
    os: str | None = Field(default=None, description="Operating system")
    osv: str | None = Field(default=None, description="OS version")
    hwv: str | None = Field(default=None, description="Hardware version")
    h: int | None = Field(default=None, description="Screen height")
    w: int | None = Field(default=None, description="Screen width")
    ppi: int | None = Field(default=None, description="Pixels per inch")
    pxratio: float | None = Field(default=None, description="Pixel ratio")
    js: int | None = Field(default=None, description="JavaScript supported (0=no, 1=yes)")
    lang: str | None = Field(default=None, description="Language (BCP-47)")
    ip: str | None = Field(default=None, description="IPv4 address")
    ipv6: str | None = Field(default=None, description="IPv6 address")
    xff: str | None = Field(default=None, description="X-Forwarded-For")
    iptr: int | None = Field(default=None, description="IP truncation")
    carrier: str | None = Field(default=None, description="Carrier/ISP")
    mccmnc: str | None = Field(default=None, description="Mobile country/network code")
    contype: ConnectionType | None = Field(default=None, description="Connection type")
    geofetch: int | None = Field(default=None, description="Allow geo fetch (0=no, 1=yes)")
    geo: Geo | None = Field(default=None, description="Geographic location")


class User(AdComModel):
    """User information.

    Attributes:
        id: User ID
        buyeruid: Buyer-specific user ID
        yob: Year of birth
        gender: Gender (M/F/O)
        keywords: Keywords
        consent: Consent string
        eids: Extended identifiers
        data: Data segments
        geo: Geographic location
    """

    id: str | None = Field(default=None, description="User ID")
    buyeruid: str | None = Field(default=None, description="Buyer-specific user ID")
    yob: int | None = Field(default=None, description="Year of birth")
    gender: str | None = Field(default=None, description="Gender (M/F/O)")
    keywords: str | None = Field(default=None, description="Keywords")
    consent: str | None = Field(default=None, description="Consent string")
    eids: list[ExtendedIdentifiers] | None = Field(
        default=None, description="Extended identifiers"
    )
    data: list[Data] | None = Field(default=None, description="Data segments")
    geo: Geo | None = Field(default=None, description="Geographic location")


class Producer(AdComModel):
    """Content producer.

    Attributes:
        id: Producer ID
        name: Producer name
        domain: Producer domain
        cat: Content categories
        cattax: Category taxonomy (default 2)
    """

    id: str | None = Field(default=None, description="Producer ID")
    name: str | None = Field(default=None, description="Producer name")
    domain: str | None = Field(default=None, description="Producer domain")
    cat: list[str] | None = Field(default=None, description="Content categories")
    cattax: int | None = Field(default=2, description="Category taxonomy")


class Network(AdComModel):
    """Broadcast network.

    Attributes:
        id: Network ID
        name: Network name
        domain: Network domain
    """

    id: str | None = Field(default=None, description="Network ID")
    name: str | None = Field(default=None, description="Network name")
    domain: str | None = Field(default=None, description="Network domain")


class Channel(AdComModel):
    """Broadcast channel.

    Attributes:
        id: Channel ID
        name: Channel name
        domain: Channel domain
    """

    id: str | None = Field(default=None, description="Channel ID")
    name: str | None = Field(default=None, description="Channel name")
    domain: str | None = Field(default=None, description="Channel domain")


class Content(AdComModel):
    """Content information.

    Attributes:
        id: Content ID
        episode: Episode number
        title: Content title
        series: Series name
        season: Season
        artist: Artist
        genre: Genre
        album: Album
        isrc: ISRC code
        url: Content URL
        cat: Content categories
        cattax: Category taxonomy (default 2)
        prodq: Production quality
        context: Content context
        rating: Content rating
        urating: User rating
        mrating: Media rating
        keywords: Keywords
        live: Live stream (0=no, 1=yes)
        srcrel: Source relationship (0=indirect, 1=direct)
        len: Length in seconds
        lang: Language (ISO-639-1)
        embed: Embedded (0=no, 1=yes)
        producer: Producer object
        network: Network object
        channel: Channel object
        data: Data segments
    """

    id: str | None = Field(default=None, description="Content ID")
    episode: int | None = Field(default=None, description="Episode number")
    title: str | None = Field(default=None, description="Content title")
    series: str | None = Field(default=None, description="Series name")
    season: str | None = Field(default=None, description="Season")
    artist: str | None = Field(default=None, description="Artist")
    genre: str | None = Field(default=None, description="Genre")
    album: str | None = Field(default=None, description="Album")
    isrc: str | None = Field(default=None, description="ISRC code")
    url: str | None = Field(default=None, description="Content URL")
    cat: list[str] | None = Field(default=None, description="Content categories")
    cattax: int | None = Field(default=2, description="Category taxonomy")
    prodq: ProductionQuality | None = Field(default=None, description="Production quality")
    context: ContentContext | None = Field(default=None, description="Content context")
    rating: str | None = Field(default=None, description="Content rating")
    urating: str | None = Field(default=None, description="User rating")
    mrating: MediaRating | None = Field(default=None, description="Media rating")
    keywords: str | None = Field(default=None, description="Keywords")
    live: int | None = Field(default=None, description="Live stream (0=no, 1=yes)")
    srcrel: int | None = Field(default=None, description="Source relationship")
    len: int | None = Field(default=None, description="Length in seconds")
    lang: str | None = Field(default=None, description="Language (ISO-639-1)")
    embed: int | None = Field(default=None, description="Embedded (0=no, 1=yes)")
    producer: Producer | None = Field(default=None, description="Producer object")
    network: Network | None = Field(default=None, description="Network object")
    channel: Channel | None = Field(default=None, description="Channel object")
    data: list[Data] | None = Field(default=None, description="Data segments")


class Publisher(AdComModel):
    """Publisher information.

    Attributes:
        id: Publisher ID
        name: Publisher name
        domain: Publisher domain
        cat: Content categories
        cattax: Category taxonomy (default 2)
    """

    id: str | None = Field(default=None, description="Publisher ID")
    name: str | None = Field(default=None, description="Publisher name")
    domain: str | None = Field(default=None, description="Publisher domain")
    cat: list[str] | None = Field(default=None, description="Content categories")
    cattax: int | None = Field(default=2, description="Category taxonomy")


class Site(AdComModel):
    """Website context.

    Attributes:
        id: Site ID
        name: Site name
        domain: Site domain
        cat: Content categories
        cattax: Category taxonomy (default 2)
        sectcat: Section categories
        pagecat: Page categories
        page: Page URL
        ref: Referrer URL
        search: Search string
        mobile: Mobile optimized (0=no, 1=yes)
        amp: AMP page (0=no, 1=yes)
        privpolicy: Privacy policy (0=no, 1=yes)
        keywords: Keywords
        publisher: Publisher object
        content: Content object
    """

    id: str | None = Field(default=None, description="Site ID")
    name: str | None = Field(default=None, description="Site name")
    domain: str | None = Field(default=None, description="Site domain")
    cat: list[str] | None = Field(default=None, description="Content categories")
    cattax: int | None = Field(default=2, description="Category taxonomy")
    sectcat: list[str] | None = Field(default=None, description="Section categories")
    pagecat: list[str] | None = Field(default=None, description="Page categories")
    page: str | None = Field(default=None, description="Page URL")
    ref: str | None = Field(default=None, description="Referrer URL")
    search: str | None = Field(default=None, description="Search string")
    mobile: int | None = Field(default=None, description="Mobile optimized (0=no, 1=yes)")
    amp: int | None = Field(default=None, description="AMP page (0=no, 1=yes)")
    privpolicy: int | None = Field(default=None, description="Privacy policy (0=no, 1=yes)")
    keywords: str | None = Field(default=None, description="Keywords")
    publisher: Publisher | None = Field(default=None, description="Publisher object")
    content: Content | None = Field(default=None, description="Content object")


class App(AdComModel):
    """App context.

    Attributes:
        id: App ID
        name: App name
        bundle: App bundle/package
        domain: App domain
        storeurl: App store URL
        cat: Content categories
        cattax: Category taxonomy (default 2)
        sectcat: Section categories
        pagecat: Page categories
        ver: App version
        privpolicy: Privacy policy (0=no, 1=yes)
        paid: Paid app (0=no, 1=yes)
        keywords: Keywords
        publisher: Publisher object
        content: Content object
    """

    id: str | None = Field(default=None, description="App ID")
    name: str | None = Field(default=None, description="App name")
    bundle: str | None = Field(default=None, description="App bundle/package")
    domain: str | None = Field(default=None, description="App domain")
    storeurl: str | None = Field(default=None, description="App store URL")
    cat: list[str] | None = Field(default=None, description="Content categories")
    cattax: int | None = Field(default=2, description="Category taxonomy")
    sectcat: list[str] | None = Field(default=None, description="Section categories")
    pagecat: list[str] | None = Field(default=None, description="Page categories")
    ver: str | None = Field(default=None, description="App version")
    privpolicy: int | None = Field(default=None, description="Privacy policy (0=no, 1=yes)")
    paid: int | None = Field(default=None, description="Paid app (0=no, 1=yes)")
    keywords: str | None = Field(default=None, description="Keywords")
    publisher: Publisher | None = Field(default=None, description="Publisher object")
    content: Content | None = Field(default=None, description="Content object")


class Dooh(AdComModel):
    """Digital out-of-home context.

    Attributes:
        id: DOOH ID
        name: DOOH venue name
        venuetype: Venue type
        venuetypetax: Venue type taxonomy
        publisher: Publisher object
        content: Content object
    """

    id: str | None = Field(default=None, description="DOOH ID")
    name: str | None = Field(default=None, description="DOOH venue name")
    venuetype: list[DOOHVenueType] | None = Field(default=None, description="Venue type")
    venuetypetax: int | None = Field(default=None, description="Venue type taxonomy")
    publisher: Publisher | None = Field(default=None, description="Publisher object")
    content: Content | None = Field(default=None, description="Content object")


class Restrictions(AdComModel):
    """Restrictions on ad attributes.

    Attributes:
        bcat: Blocked categories
        cattax: Category taxonomy (default 2)
        badv: Blocked advertiser domains
        bapp: Blocked app bundles
        battr: Blocked creative attributes
    """

    bcat: list[str] | None = Field(default=None, description="Blocked categories")
    cattax: int | None = Field(default=2, description="Category taxonomy")
    badv: list[str] | None = Field(default=None, description="Blocked advertiser domains")
    bapp: list[str] | None = Field(default=None, description="Blocked app bundles")
    battr: list[int] | None = Field(default=None, description="Blocked creative attributes")


class Regs(AdComModel):
    """Regulatory information.

    Attributes:
        coppa: COPPA flag (0=no, 1=yes)
        gdpr: GDPR applies (0=no, 1=yes)
    """

    coppa: int | None = Field(default=None, description="COPPA flag (0=no, 1=yes)")
    gdpr: int | None = Field(default=None, description="GDPR applies (0=no, 1=yes)")
