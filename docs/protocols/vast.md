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

## Configuration

VAST protocol settings can be configured via TOML configuration files or environment variables.

### TOML Configuration

Create a `settings.toml` file with VAST-specific settings:

```toml
[vast]
# VAST protocol upstream for video ad serving
version = "4.2"          # VAST version (2.0, 3.0, 4.0, 4.1, 4.2)
enable_macros = true     # IAB macro substitution
validate_xml = false     # XML schema validation

[vmap]
# VMAP upstream for video ad pod scheduling
# Inherits all VAST settings

[vast.macros]
# IAB macro substitution configuration
enable_timestamp = true      # Enable [TIMESTAMP] macro
enable_cachebusting = true   # Enable [CACHEBUSTING] macro
```

### Usage with Configuration

```python
from xsp.protocols.vast import VastUpstream, MacroSubstitutor, VastVersion
from xsp.transports.http import HttpTransport

# Create upstream with configuration values
upstream = VastUpstream(
    transport=HttpTransport(),
    endpoint="https://ads.example.com/vast",
    version=VastVersion.V4_2,  # From config: vast.version
    enable_macros=True,         # From config: vast.enable_macros
    validate_xml=False,         # From config: vast.validate_xml
)

# Create macro substitutor with configuration
macro_sub = MacroSubstitutor(
    enable_timestamp=True,      # From config: vast.macros.enable_timestamp
    enable_cachebusting=True,   # From config: vast.macros.enable_cachebusting
)
```

### Generate Configuration Template

Generate a complete TOML configuration template including all VAST settings:

```python
from xsp.core.config_generator import ConfigGenerator
from xsp.protocols.vast import VastUpstream, VmapUpstream, MacroSubstitutor

# Import classes to register them
toml = ConfigGenerator.generate_toml()
print(toml)
```

Output:
```toml
[vast]
# VAST protocol upstream for video ad serving
# Source: VastUpstream

# Type: bool
enable_macros = true

# Type: bool
validate_xml = false

# Type: VastVersion
version = "4.2"


[vast.macros]
# IAB macro substitution configuration
# Source: MacroSubstitutor

# Type: bool
enable_cachebusting = true

# Type: bool
enable_timestamp = true


[vmap]
# VMAP upstream for video ad pod scheduling
# Source: VmapUpstream
```

### Multi-Environment Configuration

Use different configuration files for different environments:

**Base config** (`settings.toml`):
```toml
[vast]
version = "4.2"
enable_macros = true
validate_xml = false
```

**Production overrides** (`settings.production.toml`):
```toml
[vast]
validate_xml = true  # Strict validation in production
```

**Development overrides** (`settings.development.toml`):
```toml
[vast]
enable_macros = false  # Disable macros for easier debugging
```

## Features

- **VAST 2.0 - 4.2** support
- **VPAID** (JavaScript/Flash creative)
- **IAB macro substitution** ([TIMESTAMP], [CACHEBUSTING], etc.)
- **Flexible encoding** (preserve Cyrillic in URL params)
- **XML validation**
- **VMAP** support (Video Multiple Ad Playlist)

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

#### Constructor

```python
MacroSubstitutor(
    *,
    enable_cachebusting: bool = True,
    enable_timestamp: bool = True,
)
```

#### Built-in Macros

- `[TIMESTAMP]` - Unix timestamp in milliseconds (enabled by default)
- `[CACHEBUSTING]` - Random 9-digit number (enabled by default)

#### Context Macros

Pass context values to substitute:
- `[CONTENTPLAYHEAD]` - Video playback position
- `[ASSETURI]` - Creative asset URI
- `[ERRORCODE]` - VAST error code

#### Custom Macros

```python
# Create with custom configuration
sub = MacroSubstitutor(
    enable_timestamp=True,
    enable_cachebusting=False,  # Disable cache busting
)

# Register custom macro
sub.register("CUSTOM", lambda: "custom_value")
url = sub.substitute("https://example.com?c=[CUSTOM]&t=[TIMESTAMP]")
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
