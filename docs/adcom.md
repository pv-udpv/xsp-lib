# AdCOM 1.0 - Advertising Common Object Model

**AdCOM 1.0** is the foundational domain object model shared across IAB programmatic standards including OpenRTB 3.0, CATS, and OpenDirect. It provides structured, reusable representations of ads, placements, users, devices, and contexts.

## Overview

AdCOM is Layer 4 (Domain Objects) in IAB's OpenMedia architecture:
- **Layer 1**: Byte transport (HTTP, gRPC)
- **Layer 2**: Data representation (JSON, Protobuf)
- **Layer 3**: Transactions (OpenRTB 3.0, CATS, OpenDirect)
- **Layer 4**: **Domain objects** (AdCOM) — ads, placements, users, devices, content

### Key Benefits

- **Reusability**: Single model for RTB, direct buying, video, display, native, DOOH
- **Safety**: Structured formats reduce malware/heavy payloads (vs. arbitrary HTML/JS)
- **Transparency**: Required fields for supply chain auditing (ads.cert, seller IDs)
- **Future-proof**: Living spec; new fields/enums don't break implementations

## Installation

```bash
# Install with schema validation support
pip install xsp-lib[schemas]
```

## Quick Start

### Creating an Ad

```python
from xsp.standards.adcom import (
    Ad,
    Display,
    Banner,
    Event,
    EventType,
    EventTrackingMethod,
)

# Create a display banner ad
banner = Banner(
    img="https://cdn.example.com/banner.jpg",
    w=300,
    h=250,
    link="https://advertiser.example.com",
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
            url="https://tracker.example.com/impression",
        )
    ],
)

ad = Ad(
    id="ad-12345",
    adomain=["advertiser.example.com"],
    cat=["IAB1-1"],
    display=display,
)
```

### Creating a Placement

```python
from xsp.standards.adcom import (
    Placement,
    VideoPlacement,
    VideoPlacementType,
    PlaybackMethod,
    LinearityMode,
)

# Create a video placement
video_placement = VideoPlacement(
    ptype=VideoPlacementType.IN_STREAM,
    mindur=15,
    maxdur=30,
    skip=1,
    playmethod=[PlaybackMethod.PAGE_LOAD_SOUND_ON],
    mime=["video/mp4"],
    linear=LinearityMode.LINEAR,
)

placement = Placement(
    tagid="placement-001",
    secure=1,
    video=video_placement,
)
```

### Validation

```python
from xsp.standards.adcom import validate_ad, validate_placement

# Validate from dictionary
ad_data = {
    "id": "ad-123",
    "adomain": ["example.com"],
    "display": {"mime": "image/jpeg", "w": 300, "h": 250},
}

ad = validate_ad(ad_data)
```

## Object Model

### Media Objects (Ads & Creatives)

Define actual ads: creative details, rendering metadata, tracking, audit.

- **`Ad`** - Root ad object (must contain exactly one media subtype)
- **`Display`** - Display ad
  - **`Banner`** - Banner creative
  - **`Native`** - Native ad with assets
    - **`Asset`** - Asset container (title, image, video, data, link)
    - **`TitleAsset`**, **`ImageAsset`**, **`VideoAsset`**, **`DataAsset`**, **`LinkAsset`**
- **`Video`** - Video ad (VAST)
- **`Audio`** - Audio ad (DAAST)
- **`Event`** - Tracking pixels/JS
- **`Audit`** - Quality/compliance information

### Placement Objects (Allowed Ads)

Define permitted ads for an impression: sizes, formats, restrictions.

- **`Placement`** - Root placement object
- **`DisplayPlacement`** - Display placement specification
  - **`DisplayFormat`** - Display size/format
  - **`NativeFormat`** - Native asset requirements
    - **`AssetFormat`** - Asset format specification
- **`VideoPlacement`** - Video placement specification
  - **`Companion`** - Companion ad specification
- **`AudioPlacement`** - Audio placement specification
- **`EventSpec`** - Tracking requirements

### Context Objects (Environment)

User, device, location, content, channel (site/app/DOOH), regulations.

- **Distribution Channels**
  - **`Site`** - Website context
  - **`App`** - Mobile/CTV app context
  - **`Dooh`** - Digital out-of-home context
- **Publisher**
  - **`Publisher`** - Publisher information
  - **`Content`** - Content metadata
  - **`Producer`**, **`Network`**, **`Channel`** - Broadcast metadata
- **User & Device**
  - **`User`** - User information
  - **`Device`** - Device information
  - **`Geo`** - Geographic location
  - **`UserAgent`**, **`BrandVersion`** - User agent data
- **Data**
  - **`Data`** - Data provider segments
  - **`Segment`** - Individual data segment
  - **`ExtendedIdentifiers`** - Extended user IDs
- **Regulations**
  - **`Regs`** - Regulatory flags (COPPA, GDPR)
  - **`Restrictions`** - Content restrictions

## Enumerations

40+ enumerated lists from AdCOM spec:

- **`ApiFramework`** - VPAID, MRAID, OMID, SIMID
- **`CreativeAttribute`** - Audio auto-play, expandable, etc.
- **`EventType`** - Impression, viewable events
- **`AdPosition`** - Above/below fold, header, footer
- **`VideoPlacementType`** - In-stream, in-banner, in-feed
- **`PlaybackMethod`** - Auto-play, click-to-play
- **`CategoryTaxonomy`** - IAB content categories
- **`DeviceType`** - Phone, tablet, CTV, desktop
- **`ConnectionType`** - WiFi, cellular, ethernet
- And 30+ more...

## Extensions

All AdCOM objects support vendor-specific extensions via the `ext` field:

```python
from xsp.standards.adcom import Ad, Display, set_ext, get_ext

display = Display(mime="image/jpeg")
ad = Ad(id="ad-123", display=display)

# Set extension
set_ext(ad, "vendor_id", "12345")

# Get extension
vendor_id = get_ext(ad, "vendor_id")

# Extensions are also accepted in dict form
ad_with_ext = Ad(
    id="ad-123",
    display=display,
    ext={"vendor": "data", "custom": 123}
)
```

## Default Values

Per AdCOM spec:

- **`cattax`** (category taxonomy) defaults to `2` (IAB Content Category Taxonomy 2.0)
- **`secure`** omitted means unknown (not 0 or 1)
- **`req`** (required flag) defaults to `0` (optional)

## Unknown Fields

AdCOM objects accept unknown fields per spec (for forward compatibility):

```python
# Unknown fields are accepted
ad_data = {
    "id": "ad-123",
    "display": {"mime": "image/jpeg"},
    "future_field": "value",  # Accepted, not validated
}

ad = validate_ad(ad_data)  # No error
```

## OpenRTB 3.0 Integration

AdCOM objects are used in OpenRTB 3.0 bid requests and responses:

**Bid Request** (SSP → DSP):
```json
{
  "id": "bid-request-123",
  "item": [{
    "spec": {
      "placement": {  // AdCOM Placement
        "tagid": "tag-001",
        "video": {    // AdCOM VideoPlacement
          "ptype": 1,
          "mindur": 15,
          "maxdur": 30
        }
      }
    }
  }],
  "context": {
    "site": {...},      // AdCOM Site
    "device": {...},    // AdCOM Device
    "user": {...},      // AdCOM User
    "regs": {...}       // AdCOM Regs
  }
}
```

**Bid Response** (DSP → SSP):
```json
{
  "id": "bid-request-123",
  "seatbid": [{
    "bid": [{
      "item": "item-1",
      "price": 2.50,
      "media": {        // AdCOM Ad
        "id": "ad-123",
        "video": {      // AdCOM Video
          "dur": 30,
          "adm": "<VAST>...</VAST>"
        }
      }
    }]
  }]
}
```

## API Reference

### Validation Functions

- **`validate_ad(data: dict) -> Ad`** - Validate and parse Ad object
- **`validate_placement(data: dict) -> Placement`** - Validate and parse Placement
- **`validate_context(data: dict, type: str) -> Site | App | Dooh`** - Validate context
- **`validate_user(data: dict) -> User`** - Validate User
- **`validate_device(data: dict) -> Device`** - Validate Device
- **`validate_regs(data: dict) -> Regs`** - Validate Regs

### Utility Functions

- **`get_ext(obj, key, default=None)`** - Get extension value
- **`set_ext(obj, key, value)`** - Set extension value
- **`merge_ext(obj, extensions)`** - Merge extensions
- **`has_ext(obj, key)`** - Check if extension exists

## Examples

See `examples/adcom_example.py` for comprehensive usage examples:

```bash
python examples/adcom_example.py
```

## Testing

Run tests:

```bash
pytest tests/unit/standards/
```

Type checking:

```bash
mypy src/xsp/standards/adcom --strict
```

Linting:

```bash
ruff check src/xsp/standards/adcom
```

## References

- [AdCOM 1.0 Specification](https://github.com/InteractiveAdvertisingBureau/AdCOM/blob/main/AdCOM%20v1.0%20FINAL.md)
- [IAB OpenMedia](https://iabtechlab.com/standards/openmedia)
- [OpenRTB 3.0](https://github.com/InteractiveAdvertisingBureau/openrtb)

## License

MIT License - See LICENSE file for details.
