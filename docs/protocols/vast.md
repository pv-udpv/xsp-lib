# VAST Protocol

## Implementation

Full VAST 2.0-4.2 support with macro substitution, validation, and VMAP.

### Features

- **Multiple versions**: VAST 2.0, 3.0, 4.0, 4.1, 4.2
- **Macro support**: Player macro substitution
- **Flexible encoding** (preserve Cyrillic in URL params)
- **XML validation**
- **VMAP** support (Video Multiple Ad Playlist)
- **Wrapper chain resolution** with fallback and creative selection

## Macro Substitution

Supported macros:

```
[TIMESTAMP] - milliseconds since 1970
[RANDOM] - random number 0-1
[CACHEBUSTING] - alias for [RANDOM]
[CONTENTPLAYHEAD] - video player position
```

Example:

```python
from xsp.protocols.vast import VastUpstream
from xsp.transports.http import HttpTransport

upstream = VastUpstream(
    transport=HttpTransport(),
    endpoint="https://ads.example.com/vast",
    version="4.2",
    enable_macros=True
)

vast_xml = await upstream.fetch(
    context={"CONTENTPLAYHEAD": "00:00:30.500"}
)
```

## VMAP Support

```python
from xsp.protocols.vast import VmapUpstream

upstream = VmapUpstream(
    transport=HttpTransport(),
    endpoint="https://ads.example.com/vmap",
    version="1.0"
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

```python
class VastVersion(str, Enum):
    V2_0 = "2.0"
    V3_0 = "3.0"
    V4_0 = "4.0"
    V4_1 = "4.1"
    V4_2 = "4.2"
```

### MediaType

```python
class MediaType(str, Enum):
    MP4 = "video/mp4"
    WEBM = "video/webm"
    QUICKTIME = "video/quicktime"
    HLS = "application/x-mpegURL"
```
