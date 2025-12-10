# VAST Protocol

Video Ad Serving Template (VAST) implementation for `xsp-lib`.

## Quick Start

```python
import asyncio
from xsp.protocols.vast import VastUpstream, VastVersion
from xsp.transports.http import HttpTransport

async def main():
    upstream = VastUpstream(
        transport=HttpTransport(),
        endpoint="https://ads.example.com/vast",
        version=VastVersion.V4_2,
        enable_macros=True,
        validate_xml=True
    )
    
    # Fetch VAST XML
    vast_xml = await upstream.fetch_vast(
        user_id="user123",
        ip_address="192.168.1.1",
        url="https://example.com/video"
    )
    
    print(vast_xml)
    await upstream.close()

asyncio.run(main())
```

## Features

- **VAST 2.0 - 4.2** support
- **VPAID** (JavaScript/Flash creative)
- **IAB macro substitution** ([TIMESTAMP], [CACHEBUSTING], etc.)
- **Flexible encoding** (preserve Cyrillic in URL params)
- **XML validation**
- **VMAP** support (Video Multiple Ad Playlist)
- **Wrapper chain resolution** with fallback and creative selection

## Macro Substitution

```python
# With macro context
vast_xml = await upstream.fetch(
    params={"imp": "https://track.com/[TIMESTAMP]?cb=[CACHEBUSTING]"},
    context={"CONTENTPLAYHEAD": "00:01:30"}
)
```

## Cyrillic URL Support

```python
# Preserve Cyrillic characters
vast_xml = await upstream.fetch(
    params={
        "url": "https://example.ru/видео",
        "_encoding_config": {"url": False}  # Don't encode
    }
)
```

## VMAP Support

```python
from xsp.protocols.vast import VmapUpstream

upstream = VmapUpstream(
    transport=HttpTransport(),
    endpoint="https://ads.example.com/vmap"
)

vmap_xml = await upstream.fetch()
```

## Wrapper Chain Resolution

The VAST wrapper chain resolver handles production VAST delivery with automatic wrapper resolution, multiple fallback upstreams, and intelligent creative selection.

### Quick Example

```python
from xsp.protocols.vast import VastUpstream, VastChainResolver, VastChainConfig
from xsp.protocols.vast.chain import SelectionStrategy
from xsp.transports.http import HttpTransport

# Create upstreams
transport = HttpTransport()
upstreams = {
    "primary": VastUpstream(transport, "https://primary.ads.com/vast", version="4.2"),
    "secondary": VastUpstream(transport, "https://backup.ads.com/vast", version="4.2")
}

# Configure resolver
config = VastChainConfig(
    max_depth=5,
    timeout=30.0,
    enable_fallbacks=True,
    selection_strategy=SelectionStrategy.HIGHEST_BITRATE
)

# Resolve wrapper chain
resolver = VastChainResolver(config=config, upstreams=upstreams)
result = await resolver.resolve(params={"w": "1920", "h": "1080"})

if result.success:
    print(f"Chain depth: {len(result.chain)}")
    print(f"Resolution time: {result.resolution_time_ms}ms")
    
    if result.selected_creative:
        media = result.selected_creative["selected_media_file"]
        print(f"Selected: {media['uri']}")
```

### Key Features

- **Recursive wrapper resolution** per VAST 4.2 §2.4.3.4
- **Multiple fallback upstreams** for reliability
- **Creative selection strategies**: HIGHEST_BITRATE, LOWEST_BITRATE, BEST_QUALITY, CUSTOM
- **Tracking collection**: Impressions, errors, and tracking events
- **YAML configuration** with environment variables
- **Comprehensive error handling** and timeout protection

### See Also

**[→ Full VAST Chain Resolver Documentation](./vast-chain-resolver.md)**

Detailed guide covering:
- Architecture and flow diagrams
- Selection strategy details
- YAML configuration examples
- Custom selector implementation
- Tracking integration
- Production best practices
- IAB VAST 4.2 compliance

## Types

### VastVersion

Enum for supported VAST versions:
- `V2_0` - VAST 2.0
- `V3_0` - VAST 3.0
- `V4_0` - VAST 4.0
- `V4_1` - VAST 4.1
- `V4_2` - VAST 4.2

### MediaType

Enum for media file MIME types:
- `VIDEO_MP4` - video/mp4
- `VIDEO_WEBM` - video/webm
- `VIDEO_OGG` - video/ogg
- `VIDEO_3GPP` - video/3gpp
- `APPLICATION_JAVASCRIPT` - VPAID JavaScript
- `APPLICATION_X_SHOCKWAVE_FLASH` - VPAID Flash

### VastResponse

Dataclass for parsed VAST response:
- `xml`: Raw XML string
- `version`: VAST version
- `ad_system`: Ad system name (optional)
- `ad_title`: Ad title (optional)
- `impressions`: List of impression URLs (optional)
- `media_files`: List of media file dicts (optional)
- `tracking_events`: Dict of tracking events (optional)
- `error_urls`: List of error tracking URLs (optional)

## API Reference

### VastUpstream

Main class for VAST ad serving.

#### Constructor

```python
VastUpstream(
    transport: Transport,
    endpoint: str,
    *,
    version: VastVersion = VastVersion.V4_2,
    enable_macros: bool = True,
    validate_xml: bool = False,
    **kwargs
)
```

#### Methods

**`fetch()`** - Fetch VAST XML from upstream
```python
async def fetch(
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    context: dict[str, Any] | None = None,
    **kwargs
) -> str
```

**`fetch_vast()`** - Convenience method for VAST-specific parameters
```python
async def fetch_vast(
    *,
    user_id: str | None = None,
    ip_address: str | None = None,
    url: str | None = None,
    params: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    **kwargs
) -> str
```

### MacroSubstitutor

IAB standard macro substitution.

#### Built-in Macros

- `[TIMESTAMP]` - Unix timestamp in milliseconds
- `[CACHEBUSTING]` - Random 9-digit number

#### Context Macros

Pass context values to substitute:
- `[CONTENTPLAYHEAD]` - Video playback position
- `[ASSETURI]` - Creative asset URI
- `[ERRORCODE]` - VAST error code

#### Custom Macros

```python
sub = MacroSubstitutor()
sub.register("CUSTOM", lambda: "custom_value")
url = sub.substitute("https://example.com?c=[CUSTOM]")
```

### Validation

```python
from xsp.protocols.vast import validate_vast_xml, VastValidationError

try:
    result = validate_vast_xml(vast_xml_string)
    print(f"VAST version: {result['version']}")
    print(f"Has ads: {result['has_ads']}")
except VastValidationError as e:
    print(f"Invalid VAST: {e}")
```
