# VAST Wrapper Chain Resolver

Production-ready VAST wrapper chain resolution with fallback support, creative selection strategies, and HTTP tracking integration.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Configuration Reference](#configuration-reference)
- [Usage Patterns](#usage-patterns)
- [Selection Strategies](#selection-strategies)
- [Tracking Integration](#tracking-integration)
- [YAML Configuration](#yaml-configuration)
- [API Reference](#api-reference)
- [Best Practices](#best-practices)
- [Error Handling](#error-handling)
- [IAB VAST Compliance](#iab-vast-compliance)

---

## Overview

The VAST wrapper chain resolver handles the complex task of resolving VAST wrapper chains to final InLine ad responses. In production VAST delivery, ad responses often contain multiple levels of Wrapper elements that must be followed recursively to obtain the actual creative assets.

**What it does:**
- Recursively follows VAST wrapper chains until an InLine response is found
- Supports multiple upstream servers with automatic fallback
- Implements intelligent creative selection strategies (bitrate, quality, custom)
- Collects and fires impression and error tracking pixels
- Provides comprehensive error handling and timeout protection
- Supports YAML-based configuration with environment variables

**Why you need it:**
- **Production reliability**: Automatic fallback prevents ad serving failures
- **Performance**: Configurable timeouts and depth limits prevent runaway requests
- **Flexibility**: Multiple creative selection strategies for different use cases
- **Compliance**: Full IAB VAST 4.2 specification compliance
- **Operations**: YAML configuration enables environment-based deployment

Per VAST 4.2 §2.4.3.4, wrapper elements contain `VASTAdTagURI` that must be resolved recursively to obtain the final InLine ad response containing creative assets.

---

## Architecture

The resolver follows this flow for each ad request:

```
┌─────────────────────────────────────────────────────────────────┐
│                     VAST Chain Resolution Flow                  │
└─────────────────────────────────────────────────────────────────┘

  Client Request
       │
       ▼
  ┌─────────────────┐
  │ Chain Resolver  │
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐      ┌──────────────────┐
  │ Primary Upstream│─────▶│ VAST Response 1  │ (Wrapper)
  └────────┬────────┘      └──────────────────┘
           │                        │
           │ Failure?               │ VASTAdTagURI
           ▼                        ▼
  ┌─────────────────┐      ┌──────────────────┐
  │Fallback Upstream│      │ VAST Response 2  │ (Wrapper)
  └────────┬────────┘      └──────────────────┘
           │                        │
           │ Success                │ VASTAdTagURI
           │                        ▼
           │               ┌──────────────────┐
           │               │ VAST Response 3  │ (InLine)
           │               └──────────────────┘
           │                        │
           │◀───────────────────────┘
           │
           ▼
  ┌─────────────────┐
  │ Collect Tracking│
  │  URLs from Chain│
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │ Apply Selection │
  │    Strategy     │
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │ Fire Impression │
  │   Tracking      │
  └────────┬────────┘
           │
           ▼
     Return Result
```

**Key components:**

1. **VastChainResolver**: Main resolver orchestrating the resolution process
2. **VastChainConfig**: Configuration controlling resolution behavior
3. **VastUpstream**: Individual VAST upstream servers (primary + fallbacks)
4. **Selection Strategies**: Algorithms for choosing the best creative
5. **Tracking Integration**: HTTP pixel firing for impressions and errors

---

## Quick Start

### Basic Usage

```python
import asyncio
from xsp.protocols.vast import VastUpstream, VastChainResolver, VastChainConfig
from xsp.protocols.vast.chain import SelectionStrategy
from xsp.transports.http import HttpTransport

async def main():
    # Create transport
    transport = HttpTransport()
    
    # Create primary and fallback upstreams
    primary = VastUpstream(
        transport=transport,
        endpoint="https://primary.ad-server.com/vast",
        version="4.2",
        enable_macros=True
    )
    
    secondary = VastUpstream(
        transport=transport,
        endpoint="https://backup.ad-server.com/vast",
        version="4.2",
        enable_macros=True
    )
    
    # Configure resolver
    config = VastChainConfig(
        max_depth=5,
        timeout=30.0,
        enable_fallbacks=True,
        selection_strategy=SelectionStrategy.HIGHEST_BITRATE
    )
    
    # Create resolver
    resolver = VastChainResolver(
        config=config,
        upstreams={
            "primary": primary,
            "secondary": secondary
        }
    )
    
    # Resolve wrapper chain
    result = await resolver.resolve(params={
        "w": "640",
        "h": "480",
        "playerVersion": "1.0"
    })
    
    if result.success:
        print(f"Resolved chain: {result.chain}")
        print(f"Resolution time: {result.resolution_time_ms:.2f}ms")
        print(f"Used fallback: {result.used_fallback}")
        
        if result.selected_creative:
            media = result.selected_creative["selected_media_file"]
            print(f"Selected media: {media['uri']}")
            print(f"Bitrate: {media.get('bitrate')}kbps")
            print(f"Resolution: {media.get('width')}x{media.get('height')}")
    else:
        print(f"Resolution failed: {result.error}")

asyncio.run(main())
```

### YAML Configuration

```python
import asyncio
from xsp.protocols.vast.config_loader import VastChainConfigLoader
from xsp.transports.http import HttpTransport

async def main():
    # Load configuration from YAML
    transport = HttpTransport()
    resolvers = VastChainConfigLoader.load(
        "config/vast_chains.yaml",
        transport
    )
    
    # Use default chain
    resolver = resolvers["default"]
    result = await resolver.resolve(params={"w": "640", "h": "480"})
    
    if result.success:
        print(f"Ad title: {result.vast_data['ad_title']}")
        print(f"Chain depth: {len(result.chain)}")

asyncio.run(main())
```

---

## Configuration Reference

### VastChainConfig

Configuration object controlling wrapper chain resolution behavior.

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_depth` | `int` | `5` | Maximum wrapper chain depth. Per VAST 4.2 §2.4.1.2 default is 5. |
| `timeout` | `float` | `30.0` | Total timeout for entire chain resolution in seconds. |
| `per_request_timeout` | `float` | `10.0` | Timeout for each individual wrapper request in seconds. |
| `enable_fallbacks` | `bool` | `True` | Enable fallback to secondary upstreams on primary failure. |
| `resolution_strategy` | `ResolutionStrategy` | `RECURSIVE` | Strategy for resolving wrapper chains. |
| `selection_strategy` | `SelectionStrategy` | `HIGHEST_BITRATE` | Strategy for selecting creative from resolved VAST. |
| `follow_redirects` | `bool` | `True` | Follow HTTP redirects in wrapper chain. |
| `validate_each_response` | `bool` | `False` | Validate XML structure of each wrapper response. |
| `collect_tracking_urls` | `bool` | `True` | Collect tracking URLs from all wrappers in chain. |
| `collect_error_urls` | `bool` | `True` | Collect error URLs from all wrappers in chain. |
| `custom_selector` | `Callable` | `None` | Custom creative selector function when `selection_strategy=CUSTOM`. |
| `additional_params` | `dict` | `{}` | Additional parameters passed to upstream requests. |

**Example:**

```python
from xsp.protocols.vast.chain import VastChainConfig, SelectionStrategy

config = VastChainConfig(
    max_depth=3,
    timeout=20.0,
    per_request_timeout=5.0,
    enable_fallbacks=True,
    selection_strategy=SelectionStrategy.BEST_QUALITY,
    collect_tracking_urls=True
)
```

### ResolutionStrategy

Strategy for resolving VAST wrapper chains.

**Values:**

- `RECURSIVE`: Follow wrapper chain recursively until InLine is found (default)
- `FIRST_INLINE`: Return the first InLine response encountered
- `MAX_DEPTH`: Continue until max_depth is reached
- `PARALLEL`: Resolve multiple wrapper chains in parallel (for ad pods)

**Example:**

```python
from xsp.protocols.vast.chain import ResolutionStrategy

config = VastChainConfig(
    resolution_strategy=ResolutionStrategy.RECURSIVE
)
```

### SelectionStrategy

Strategy for selecting creative from resolved VAST response.

**Values:**

- `HIGHEST_BITRATE`: Select media file with highest bitrate (default)
- `LOWEST_BITRATE`: Select media file with lowest bitrate
- `BEST_QUALITY`: Select based on resolution and codec quality
- `CUSTOM`: Use custom selection function

**Example:**

```python
from xsp.protocols.vast.chain import SelectionStrategy

config = VastChainConfig(
    selection_strategy=SelectionStrategy.LOWEST_BITRATE
)
```

---

## Usage Patterns

### Pattern 1: Basic Chain Resolution

Simple wrapper chain resolution with default settings.

```python
import asyncio
from xsp.protocols.vast import VastUpstream, VastChainResolver, VastChainConfig
from xsp.transports.http import HttpTransport

async def basic_resolution():
    transport = HttpTransport()
    
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
        version="4.2"
    )
    
    config = VastChainConfig()  # Use defaults
    resolver = VastChainResolver(
        config=config,
        upstreams={"primary": upstream}
    )
    
    result = await resolver.resolve()
    
    if result.success:
        print(f"✓ Resolved in {result.resolution_time_ms:.2f}ms")
        print(f"  Chain depth: {len(result.chain)}")
        
        if result.selected_creative:
            media = result.selected_creative["selected_media_file"]
            print(f"  Media URL: {media['uri']}")

asyncio.run(basic_resolution())
```

### Pattern 2: YAML Configuration

Load configuration from YAML file for environment-based deployment.

```python
import asyncio
import os
from xsp.protocols.vast.config_loader import VastChainConfigLoader
from xsp.transports.http import HttpTransport

async def yaml_configuration():
    # Set environment variables
    os.environ["PRIMARY_VAST_ENDPOINT"] = "https://primary.example.com/vast"
    os.environ["SECONDARY_VAST_ENDPOINT"] = "https://secondary.example.com/vast"
    
    # Load from YAML
    transport = HttpTransport()
    resolvers = VastChainConfigLoader.load(
        "config/vast_chains.yaml",
        transport
    )
    
    # Access different chain configurations
    default_resolver = resolvers["default"]
    high_quality_resolver = resolvers["high_quality"]
    low_bandwidth_resolver = resolvers["low_bandwidth"]
    
    # Use appropriate resolver based on context
    is_mobile = True  # Detect from user agent
    resolver = low_bandwidth_resolver if is_mobile else default_resolver
    
    result = await resolver.resolve(params={"w": "640", "h": "480"})
    
    if result.success:
        print(f"✓ Selected strategy: {'low_bandwidth' if is_mobile else 'default'}")

asyncio.run(yaml_configuration())
```

### Pattern 3: Custom Selection Strategy

Implement custom creative selection logic.

```python
import asyncio
from xsp.protocols.vast import VastUpstream, VastChainResolver, VastChainConfig
from xsp.protocols.vast.chain import SelectionStrategy
from xsp.transports.http import HttpTransport

def mobile_selector(media_files):
    """Select best creative for mobile devices.
    
    Prefers:
    1. HLS streaming (adaptive bitrate)
    2. MP4 progressive
    3. Resolution <= 720p
    4. Lowest bitrate for bandwidth efficiency
    """
    # Filter for mobile-friendly formats
    mp4_files = [f for f in media_files if f.get("type") == "video/mp4"]
    
    if not mp4_files:
        return media_files[0] if media_files else None
    
    # Filter for reasonable resolution
    mobile_files = [
        f for f in mp4_files
        if f.get("height", 0) <= 720
    ]
    
    if not mobile_files:
        mobile_files = mp4_files
    
    # Select lowest bitrate for bandwidth
    files_with_bitrate = [f for f in mobile_files if f.get("bitrate")]
    
    if files_with_bitrate:
        return min(files_with_bitrate, key=lambda f: f.get("bitrate", 0))
    
    return mobile_files[0]

async def custom_selection():
    transport = HttpTransport()
    
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
        version="4.2"
    )
    
    config = VastChainConfig(
        selection_strategy=SelectionStrategy.CUSTOM
    )
    
    resolver = VastChainResolver(
        config=config,
        upstreams={"primary": upstream}
    )
    
    # Set custom selector
    resolver.set_custom_selector(mobile_selector)
    
    result = await resolver.resolve(params={"w": "640", "h": "480"})
    
    if result.success and result.selected_creative:
        media = result.selected_creative["selected_media_file"]
        print(f"✓ Selected mobile-optimized creative:")
        print(f"  Type: {media.get('type')}")
        print(f"  Resolution: {media.get('width')}x{media.get('height')}")
        print(f"  Bitrate: {media.get('bitrate')}kbps")

asyncio.run(custom_selection())
```

### Pattern 4: Multiple Fallbacks with Error Handling

Production-ready configuration with comprehensive error handling.

```python
import asyncio
import logging
from xsp.protocols.vast import VastUpstream, VastChainResolver, VastChainConfig
from xsp.protocols.vast.chain import SelectionStrategy
from xsp.transports.http import HttpTransport
from xsp.core.exceptions import UpstreamError, UpstreamTimeout

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def production_resolution():
    transport = HttpTransport()
    
    # Create multiple upstreams
    upstreams = {
        "primary": VastUpstream(
            transport=transport,
            endpoint="https://primary.ad-server.com/vast",
            version="4.2",
            enable_macros=True
        ),
        "secondary": VastUpstream(
            transport=transport,
            endpoint="https://secondary.ad-server.com/vast",
            version="4.2",
            enable_macros=True
        ),
        "tertiary": VastUpstream(
            transport=transport,
            endpoint="https://tertiary.ad-server.com/vast",
            version="4.2",
            enable_macros=True
        )
    }
    
    # Production configuration
    config = VastChainConfig(
        max_depth=5,
        timeout=30.0,
        per_request_timeout=10.0,
        enable_fallbacks=True,
        selection_strategy=SelectionStrategy.BEST_QUALITY,
        collect_tracking_urls=True,
        collect_error_urls=True
    )
    
    resolver = VastChainResolver(config=config, upstreams=upstreams)
    
    try:
        result = await resolver.resolve(params={
            "w": "1920",
            "h": "1080",
            "playerVersion": "2.0",
            "url": "https://example.com/content"
        })
        
        if result.success:
            logger.info(f"✓ Resolution successful")
            logger.info(f"  Chain depth: {len(result.chain)}")
            logger.info(f"  Used fallback: {result.used_fallback}")
            logger.info(f"  Resolution time: {result.resolution_time_ms:.2f}ms")
            
            if result.selected_creative:
                media = result.selected_creative["selected_media_file"]
                logger.info(f"  Selected: {media['uri']}")
                logger.info(f"  Bitrate: {media.get('bitrate')}kbps")
                
            # Access tracking URLs
            if result.vast_data:
                impressions = result.vast_data.get("impressions", [])
                logger.info(f"  Impression URLs: {len(impressions)}")
                
            return result.selected_creative
        else:
            logger.error(f"✗ Resolution failed: {result.error}")
            
            # Fallback to default ad
            return None
            
    except UpstreamTimeout as e:
        logger.error(f"✗ Timeout during resolution: {e}")
        # Return default ad or error response
        return None
        
    except UpstreamError as e:
        logger.error(f"✗ Upstream error: {e}")
        # Return default ad or error response
        return None
        
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        return None

asyncio.run(production_resolution())
```

---

## Selection Strategies

The resolver supports multiple creative selection strategies to optimize ad delivery for different scenarios.

### HIGHEST_BITRATE

Selects the media file with the highest bitrate for best quality.

**Use cases:**
- Desktop browsers with good bandwidth
- WiFi connections
- Premium content requiring high quality

**Behavior:**
- Filters media files with valid bitrate attribute
- Selects file with maximum bitrate value
- Falls back to first file if no bitrates available

**Example:**

```python
from xsp.protocols.vast.chain import VastChainConfig, SelectionStrategy

config = VastChainConfig(
    selection_strategy=SelectionStrategy.HIGHEST_BITRATE
)
```

**Per VAST 4.2 §2.4.4.1**: MediaFile bitrate attribute indicates encoding bitrate in kbps.

### LOWEST_BITRATE

Selects the media file with the lowest bitrate for bandwidth efficiency.

**Use cases:**
- Mobile devices on cellular networks
- Low bandwidth environments
- Data-constrained scenarios

**Behavior:**
- Filters media files with valid bitrate attribute
- Selects file with minimum bitrate value
- Falls back to first file if no bitrates available

**Example:**

```python
config = VastChainConfig(
    selection_strategy=SelectionStrategy.LOWEST_BITRATE
)
```

### BEST_QUALITY

Intelligent quality selection balancing bitrate and context.

**Use cases:**
- Adaptive quality based on available bandwidth
- Mobile-first responsive design
- Mixed device types

**Behavior:**
1. Finds highest bitrate media file
2. If bitrate >= 1000kbps, selects highest (good connection)
3. If bitrate < 1000kbps, selects lowest (limited bandwidth)
4. Falls back to first file if no bitrates available

**Example:**

```python
config = VastChainConfig(
    selection_strategy=SelectionStrategy.BEST_QUALITY
)
```

**Rationale:** High bitrate availability suggests good connection; low maximum bitrate suggests bandwidth constraints, so select lowest for reliability.

### CUSTOM

User-defined selection logic for specialized requirements.

**Use cases:**
- Device-specific optimization (iOS HLS, Android formats)
- Codec preference (H.264, VP9, AV1)
- Delivery method preference (streaming vs progressive)
- Business logic (premium tier users get HD)

**Behavior:**
- Calls user-provided selector function
- Function receives list of media file dicts
- Function returns selected media file dict or None

**Example:**

```python
def hls_preferred_selector(media_files):
    """Prefer HLS streaming, fall back to highest bitrate MP4."""
    # Prefer HLS
    hls_files = [
        f for f in media_files
        if f.get("type") == "application/x-mpegURL"
    ]
    if hls_files:
        return hls_files[0]
    
    # Fall back to highest bitrate MP4
    mp4_files = [
        f for f in media_files
        if f.get("type") == "video/mp4" and f.get("bitrate")
    ]
    if mp4_files:
        return max(mp4_files, key=lambda f: f.get("bitrate", 0))
    
    # Default
    return media_files[0] if media_files else None

config = VastChainConfig(
    selection_strategy=SelectionStrategy.CUSTOM
)

resolver = VastChainResolver(config=config, upstreams=upstreams)
resolver.set_custom_selector(hls_preferred_selector)
```

**Media File Dictionary Structure:**

```python
{
    "delivery": "progressive",      # or "streaming"
    "type": "video/mp4",            # MIME type
    "width": 1920,                  # Width in pixels
    "height": 1080,                 # Height in pixels
    "bitrate": 2500,                # Bitrate in kbps
    "uri": "https://cdn.example.com/video.mp4"
}
```

---

## Tracking Integration

The resolver automatically collects and fires VAST tracking pixels during the resolution process.

### Impression Tracking

Impression URLs are collected from all wrapper elements in the chain and the final InLine response, then fired when the ad is ready for display.

**Per VAST 4.2 §2.3.1.4**: Impression elements contain URLs that should be fired when the impression is counted (typically on first frame display).

**How it works:**

1. Resolver collects all `<Impression>` URLs from each VAST response in the chain
2. URLs are accumulated in `result.vast_data["impressions"]`
3. Application fires tracking pixels when appropriate:

```python
result = await resolver.resolve()

if result.success and result.vast_data:
    impression_urls = result.vast_data.get("impressions", [])
    
    # Fire impression tracking when ad starts displaying
    for url in impression_urls:
        asyncio.create_task(fire_tracking_pixel(url))
```

**Fire-and-forget tracking helper:**

```python
import aiohttp

async def fire_tracking_pixel(url: str) -> None:
    """Fire tracking pixel without blocking."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5.0) as response:
                pass  # Fire and forget
    except Exception as e:
        logger.warning(f"Failed to fire tracking pixel {url}: {e}")
```

### Error Tracking

Error URLs are collected from all wrapper elements and can be fired when errors occur during ad playback or resolution.

**Per VAST 4.2 §2.4.2.4**: Error elements contain URLs that should be fired with error code macro substitution when errors occur.

**VAST Error Codes:**

| Code | Description |
|------|-------------|
| `900` | Undefined Error |
| `901` | General VAST error |
| `902` | VAST schema validation error |
| `303` | No VAST response after one or more wrappers |
| `100` | XML parsing error |
| `101` | VAST schema validation error |
| `200` | Trafficking error (wrapper limit reached, etc.) |

**How it works:**

```python
result = await resolver.resolve()

if not result.success and result.vast_data:
    error_urls = result.vast_data.get("error_urls", [])
    
    # Fire error tracking with error code
    error_code = "303"  # No VAST response
    for url in error_urls:
        # Replace [ERRORCODE] macro
        expanded_url = url.replace("[ERRORCODE]", error_code)
        asyncio.create_task(fire_tracking_pixel(expanded_url))
```

**Internal error tracking:**

The resolver includes internal methods for tracking (used internally, can be called manually):

```python
# Fire error tracking (internal method)
await resolver._track_error(
    error_urls=["https://track.example.com/error?code=[ERRORCODE]"],
    error_code="303"
)

# Fire impression tracking (internal method)
await resolver._track_impression(
    impression_urls=["https://track.example.com/imp?id=123"]
)
```

### Tracking Events

In addition to impression and error tracking, the resolver collects tracking event URLs from Linear creatives.

**Per VAST 4.2 §2.3.1.5.5**: Tracking elements contain URLs for video events (start, midpoint, complete, etc.).

```python
result = await resolver.resolve()

if result.success and result.vast_data:
    tracking_events = result.vast_data.get("tracking_events", {})
    
    # Fire start event
    start_urls = tracking_events.get("start", [])
    for url in start_urls:
        asyncio.create_task(fire_tracking_pixel(url))
    
    # Fire midpoint event at 50% progress
    midpoint_urls = tracking_events.get("midpoint", [])
    # ...
```

**Common tracking events:**

- `start`: Video started playing
- `firstQuartile`: 25% of video played
- `midpoint`: 50% of video played
- `thirdQuartile`: 75% of video played
- `complete`: 100% of video played
- `mute`: Video muted
- `unmute`: Video unmuted
- `pause`: Video paused
- `resume`: Video resumed
- `fullscreen`: Entered fullscreen
- `exitFullscreen`: Exited fullscreen

---

## YAML Configuration

The resolver supports YAML-based configuration for easy deployment across environments.

### Configuration File Structure

```yaml
# vast_chains.yaml

# Define upstream servers
upstreams:
  vast:
    primary:
      endpoint: ${PRIMARY_VAST_ENDPOINT}
      version: "4.2"
      enable_macros: true
      validate_xml: false
    
    secondary:
      endpoint: ${SECONDARY_VAST_ENDPOINT:-https://backup.example.com/vast}
      version: "4.2"
      enable_macros: true
      validate_xml: false

# Define chain resolvers
chains:
  # Default production chain
  default:
    primary: vast.primary
    fallbacks:
      - vast.secondary
    max_depth: 5
    timeout: 30.0
    per_request_timeout: 10.0
    enable_fallbacks: true
    resolution_strategy: recursive
    selection_strategy: highest_bitrate
    follow_redirects: true
    validate_each_response: false
    collect_tracking_urls: true
    collect_error_urls: true
    additional_params: {}
  
  # Mobile-optimized chain
  mobile:
    primary: vast.primary
    fallbacks:
      - vast.secondary
    max_depth: 3
    timeout: 15.0
    per_request_timeout: 5.0
    enable_fallbacks: true
    resolution_strategy: recursive
    selection_strategy: lowest_bitrate
    collect_tracking_urls: true
  
  # High-quality chain for premium content
  premium:
    primary: vast.primary
    fallbacks:
      - vast.secondary
    max_depth: 5
    timeout: 30.0
    selection_strategy: best_quality
```

### Environment Variables

The YAML loader supports environment variable substitution with two patterns:

**Required variable** (fails if not set):
```yaml
endpoint: ${PRIMARY_VAST_ENDPOINT}
```

**Optional variable with default**:
```yaml
endpoint: ${SECONDARY_VAST_ENDPOINT:-https://backup.example.com/vast}
```

**Setting environment variables:**

```bash
# Linux/macOS
export PRIMARY_VAST_ENDPOINT="https://primary.example.com/vast"
export SECONDARY_VAST_ENDPOINT="https://secondary.example.com/vast"

# Python
import os
os.environ["PRIMARY_VAST_ENDPOINT"] = "https://primary.example.com/vast"
```

### Loading Configuration

```python
from xsp.protocols.vast.config_loader import VastChainConfigLoader
from xsp.transports.http import HttpTransport

# Load all resolvers from YAML
transport = HttpTransport()
resolvers = VastChainConfigLoader.load("config/vast_chains.yaml", transport)

# Access specific chains
default_resolver = resolvers["default"]
mobile_resolver = resolvers["mobile"]
premium_resolver = resolvers["premium"]

# Use based on context
if is_mobile_device:
    result = await mobile_resolver.resolve(params={"w": "640", "h": "480"})
else:
    result = await default_resolver.resolve(params={"w": "1920", "h": "1080"})
```

### Multi-Environment Configuration

**Development:**

```yaml
# config/development.yaml
upstreams:
  vast:
    primary:
      endpoint: http://localhost:8080/vast
      version: "4.2"
```

**Staging:**

```yaml
# config/staging.yaml
upstreams:
  vast:
    primary:
      endpoint: https://staging-ads.example.com/vast
      version: "4.2"
```

**Production:**

```yaml
# config/production.yaml
upstreams:
  vast:
    primary:
      endpoint: ${VAST_PRIMARY_ENDPOINT}
      version: "4.2"
    secondary:
      endpoint: ${VAST_SECONDARY_ENDPOINT}
      version: "4.2"
```

**Loading based on environment:**

```python
import os
from xsp.protocols.vast.config_loader import VastChainConfigLoader
from xsp.transports.http import HttpTransport

env = os.getenv("ENVIRONMENT", "development")
config_path = f"config/{env}.yaml"

transport = HttpTransport()
resolvers = VastChainConfigLoader.load(config_path, transport)
```

---

## API Reference

### VastChainResolver

Main resolver class for VAST wrapper chain resolution.

#### Constructor

```python
VastChainResolver(
    config: VastChainConfig,
    upstreams: dict[str, VastUpstream]
)
```

**Parameters:**
- `config` (VastChainConfig): Resolution configuration
- `upstreams` (dict[str, VastUpstream]): Dictionary of upstream instances. First key is primary, remaining are fallbacks.

**Raises:**
- `ValueError`: If upstreams dict is empty

**Example:**

```python
from xsp.protocols.vast import VastChainResolver, VastChainConfig, VastUpstream
from xsp.transports.http import HttpTransport

transport = HttpTransport()

upstreams = {
    "primary": VastUpstream(transport, "https://primary.example.com/vast"),
    "secondary": VastUpstream(transport, "https://secondary.example.com/vast")
}

config = VastChainConfig(max_depth=5)
resolver = VastChainResolver(config=config, upstreams=upstreams)
```

#### resolve()

Resolve VAST wrapper chain to final InLine response.

```python
async def resolve(
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    context: dict[str, Any] | None = None,
    **kwargs: Any
) -> VastResolutionResult
```

**Parameters:**
- `params` (dict[str, Any], optional): Query parameters for upstream requests
- `headers` (dict[str, str], optional): HTTP headers for upstream requests
- `context` (dict[str, Any], optional): Additional context for macro substitution
- `**kwargs`: Additional arguments passed to upstream

**Returns:**
- `VastResolutionResult`: Resolution result containing resolved VAST and metadata

**Example:**

```python
result = await resolver.resolve(
    params={
        "w": "1920",
        "h": "1080",
        "playerVersion": "2.0"
    },
    headers={
        "User-Agent": "MyPlayer/1.0"
    },
    context={
        "CONTENTPLAYHEAD": "00:01:30.500"
    }
)

if result.success:
    print(f"Chain: {result.chain}")
    print(f"Time: {result.resolution_time_ms}ms")
```

#### set_custom_selector()

Set custom creative selection function.

```python
def set_custom_selector(
    selector: Callable[[list[dict[str, Any]]], dict[str, Any] | None]
) -> None
```

**Parameters:**
- `selector` (Callable): Function that takes list of media files and returns selected one or None

**Example:**

```python
def select_hd_only(media_files):
    """Select first HD file (1080p or higher)."""
    for mf in media_files:
        if mf.get("height", 0) >= 1080:
            return mf
    return media_files[0] if media_files else None

resolver.set_custom_selector(select_hd_only)
```

### VastResolutionResult

Result object returned by `resolve()`.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | Whether resolution succeeded |
| `vast_data` | `dict[str, Any] \| None` | Parsed VAST data dictionary |
| `selected_creative` | `dict[str, Any] \| None` | Selected creative with media file |
| `chain` | `list[str]` | List of URLs in the wrapper chain |
| `xml` | `str \| None` | Final VAST XML response |
| `error` | `Exception \| None` | Error that occurred during resolution |
| `used_fallback` | `bool` | Whether a fallback upstream was used |
| `resolution_time_ms` | `float \| None` | Total resolution time in milliseconds |

**Example:**

```python
result = await resolver.resolve()

if result.success:
    # Access resolved data
    ad_title = result.vast_data["ad_title"]
    ad_system = result.vast_data["ad_system"]
    
    # Get selected creative
    if result.selected_creative:
        media = result.selected_creative["selected_media_file"]
        print(f"Media URL: {media['uri']}")
        print(f"Bitrate: {media.get('bitrate')}kbps")
    
    # Chain information
    print(f"Chain depth: {len(result.chain)}")
    print(f"Chain URLs: {result.chain}")
    
    # Performance metrics
    print(f"Resolution time: {result.resolution_time_ms:.2f}ms")
    print(f"Used fallback: {result.used_fallback}")
else:
    print(f"Error: {result.error}")
```

### VastChainConfigLoader

YAML configuration loader for creating resolver instances.

#### load()

Load VAST chain configurations from YAML file.

```python
@classmethod
def load(
    cls,
    config_path: str | Path,
    transport: Transport
) -> dict[str, VastChainResolver]
```

**Parameters:**
- `config_path` (str | Path): Path to YAML configuration file
- `transport` (Transport): Transport instance to use for all upstreams

**Returns:**
- `dict[str, VastChainResolver]`: Dictionary mapping chain names to resolver instances

**Raises:**
- `FileNotFoundError`: If config file doesn't exist
- `ValueError`: If configuration is invalid or required env vars missing
- `yaml.YAMLError`: If YAML parsing fails

**Example:**

```python
from xsp.protocols.vast.config_loader import VastChainConfigLoader
from xsp.transports.http import HttpTransport
from pathlib import Path

transport = HttpTransport()
config_path = Path("config/vast_chains.yaml")

resolvers = VastChainConfigLoader.load(config_path, transport)

# Access resolvers by name
default = resolvers["default"]
mobile = resolvers["mobile"]
premium = resolvers["premium"]
```

---

## Best Practices

### Production Deployment

**1. Always configure fallback upstreams:**

```python
# ✅ Good: Multiple fallbacks for reliability
upstreams = {
    "primary": primary_upstream,
    "secondary": secondary_upstream,
    "tertiary": tertiary_upstream
}

# ❌ Bad: Single upstream, no redundancy
upstreams = {
    "primary": primary_upstream
}
```

**2. Set appropriate timeouts:**

```python
# ✅ Good: Reasonable timeouts prevent hanging
config = VastChainConfig(
    timeout=30.0,              # Total timeout
    per_request_timeout=10.0   # Per-request timeout
)

# ❌ Bad: Too long, can hang user experience
config = VastChainConfig(
    timeout=120.0,
    per_request_timeout=60.0
)
```

**3. Use YAML configuration for environment management:**

```python
# ✅ Good: Environment-based configuration
env = os.getenv("ENVIRONMENT", "production")
resolvers = VastChainConfigLoader.load(f"config/{env}.yaml", transport)

# ❌ Bad: Hard-coded endpoints
upstream = VastUpstream(transport, "https://ads.example.com/vast")
```

**4. Enable tracking collection:**

```python
# ✅ Good: Collect tracking for analytics
config = VastChainConfig(
    collect_tracking_urls=True,
    collect_error_urls=True
)

# ❌ Bad: Missing tracking data
config = VastChainConfig(
    collect_tracking_urls=False
)
```

### Performance Optimization

**1. Limit wrapper chain depth:**

```python
# ✅ Good: Prevent excessive redirects
config = VastChainConfig(
    max_depth=3  # Reasonable limit
)

# ❌ Bad: Unlimited depth can cause performance issues
config = VastChainConfig(
    max_depth=20  # Too deep
)
```

**2. Use appropriate selection strategy:**

```python
# Mobile devices - prefer low bandwidth
mobile_config = VastChainConfig(
    selection_strategy=SelectionStrategy.LOWEST_BITRATE
)

# Desktop/WiFi - prefer high quality
desktop_config = VastChainConfig(
    selection_strategy=SelectionStrategy.HIGHEST_BITRATE
)
```

**3. Disable validation in production:**

```python
# ✅ Good: Validation off in production for performance
config = VastChainConfig(
    validate_each_response=False
)

# Enable only in development/testing
dev_config = VastChainConfig(
    validate_each_response=True
)
```

### Error Handling

**1. Always check result.success:**

```python
# ✅ Good: Check success before using result
result = await resolver.resolve()

if result.success:
    process_creative(result.selected_creative)
else:
    log_error(result.error)
    serve_default_ad()

# ❌ Bad: Assume success
result = await resolver.resolve()
process_creative(result.selected_creative)  # May be None!
```

**2. Handle specific exceptions:**

```python
# ✅ Good: Specific exception handling
try:
    result = await resolver.resolve()
except UpstreamTimeout:
    logger.error("Resolution timed out")
    serve_default_ad()
except UpstreamError as e:
    logger.error(f"Upstream error: {e}")
    serve_default_ad()

# ❌ Bad: Catch-all exception
try:
    result = await resolver.resolve()
except Exception:
    pass  # Lost error context
```

**3. Fire error tracking on failures:**

```python
# ✅ Good: Track errors for monitoring
result = await resolver.resolve()

if not result.success and result.vast_data:
    error_urls = result.vast_data.get("error_urls", [])
    await resolver._track_error(error_urls, error_code="303")
```

### Monitoring and Observability

**1. Log resolution metrics:**

```python
# ✅ Good: Comprehensive logging
result = await resolver.resolve()

logger.info(
    "VAST resolution",
    extra={
        "success": result.success,
        "chain_depth": len(result.chain),
        "used_fallback": result.used_fallback,
        "resolution_time_ms": result.resolution_time_ms,
        "error": str(result.error) if result.error else None
    }
)
```

**2. Track fallback usage:**

```python
# ✅ Good: Monitor fallback patterns
if result.used_fallback:
    metrics.increment("vast.fallback.used")
    logger.warning("Primary upstream failed, used fallback")
```

**3. Monitor resolution time:**

```python
# ✅ Good: Track performance metrics
if result.resolution_time_ms:
    metrics.timing("vast.resolution.time", result.resolution_time_ms)
    
    if result.resolution_time_ms > 5000:
        logger.warning(f"Slow VAST resolution: {result.resolution_time_ms}ms")
```

---

## Error Handling

### Common Errors

#### UpstreamTimeout

Resolution exceeded configured timeout.

**Cause:** Network latency, slow upstream servers, or deep wrapper chains.

**Solution:**

```python
from xsp.core.exceptions import UpstreamTimeout

try:
    result = await resolver.resolve()
except UpstreamTimeout as e:
    logger.error(f"Resolution timed out: {e}")
    # Serve default ad or cached response
    return get_default_ad()
```

**Prevention:**

```python
# Set reasonable timeouts
config = VastChainConfig(
    timeout=30.0,              # Total timeout
    per_request_timeout=10.0,  # Per-request timeout
    max_depth=3                # Limit chain depth
)
```

#### UpstreamError

Generic upstream error (network, invalid response, etc.).

**Cause:** Network failures, invalid VAST XML, missing required elements.

**Solution:**

```python
from xsp.core.exceptions import UpstreamError

try:
    result = await resolver.resolve()
except UpstreamError as e:
    logger.error(f"Upstream error: {e}")
    
    # Try fallback if not already used
    if not result.used_fallback and len(resolver._fallback_keys) > 0:
        # Fallback happens automatically
        pass
    else:
        # All upstreams failed
        return get_default_ad()
```

**Prevention:**

```python
# Configure multiple fallbacks
upstreams = {
    "primary": primary_upstream,
    "secondary": secondary_upstream,
    "tertiary": tertiary_upstream
}

config = VastChainConfig(enable_fallbacks=True)
```

#### ValueError (Custom Selector)

Custom selection strategy used without setting selector function.

**Cause:** `selection_strategy=CUSTOM` without calling `set_custom_selector()`.

**Solution:**

```python
config = VastChainConfig(
    selection_strategy=SelectionStrategy.CUSTOM
)

resolver = VastChainResolver(config=config, upstreams=upstreams)

# Must set custom selector
resolver.set_custom_selector(my_selector_function)
```

### Fallback Behavior

When primary upstream fails, the resolver automatically attempts fallbacks in order:

```
Primary → Fail → Secondary → Fail → Tertiary → Success
```

**Check if fallback was used:**

```python
result = await resolver.resolve()

if result.success:
    if result.used_fallback:
        logger.warning("Primary failed, used fallback upstream")
        metrics.increment("vast.fallback.used")
    else:
        logger.info("Primary upstream succeeded")
```

### Depth Limit Exceeded

Wrapper chain exceeded `max_depth` without finding InLine response.

**Error:** `UpstreamError: Max wrapper depth (5) exceeded`

**Cause:** Circular wrapper references or excessively deep chains.

**Solution:**

```python
# Reduce max_depth to fail faster
config = VastChainConfig(max_depth=3)
```

**Detection:**

```python
result = await resolver.resolve()

if not result.success and "max wrapper depth" in str(result.error).lower():
    logger.error(f"Wrapper chain too deep: {result.chain}")
    # Report to ad server for investigation
```

### Missing VASTAdTagURI

Wrapper element missing required `VASTAdTagURI` element.

**Error:** `UpstreamError: Wrapper missing VASTAdTagURI`

**Cause:** Invalid VAST XML from upstream.

**Solution:**

```python
# Enable XML validation to catch early
config = VastChainConfig(validate_each_response=True)

# Or handle in application
if not result.success and "missing VASTAdTagURI" in str(result.error):
    logger.error(f"Invalid wrapper from upstream: {result.chain[-1]}")
    # Fire error tracking
    await resolver._track_error(error_urls, error_code="901")
```

---

## IAB VAST Compliance

The VAST wrapper chain resolver implements IAB VAST 4.2 specification requirements for wrapper chain resolution.

### Specification References

#### VAST 4.2 §2.4.3.4 - Wrapper Element

**Requirement:** Wrapper elements contain `VASTAdTagURI` that must be resolved to obtain the final InLine ad response.

**Implementation:**
- Resolver extracts `VASTAdTagURI` from Wrapper elements
- Recursively fetches each URL in the chain
- Continues until InLine response is found

**Code:**

```python
def _extract_wrapper_url(self, xml: str) -> str | None:
    """Extract VASTAdTagURI from Wrapper element."""
    root = ET.fromstring(xml)
    vast_ad_tag_uri = root.find(".//Wrapper/VASTAdTagURI")
    if vast_ad_tag_uri is not None and vast_ad_tag_uri.text:
        return vast_ad_tag_uri.text.strip()
    return None
```

#### VAST 4.2 §2.4.1.2 - maxwrapperdepth Attribute

**Requirement:** VAST wrapper chains should respect `maxwrapperdepth` attribute to prevent infinite recursion. Default value is 5.

**Implementation:**
- `VastChainConfig.max_depth` defaults to 5 per specification
- Resolver stops after `max_depth` iterations
- Raises `UpstreamError` if depth exceeded

**Code:**

```python
config = VastChainConfig(
    max_depth=5  # Per VAST 4.2 §2.4.1.2
)
```

#### VAST 4.2 §2.4.4.1 - MediaFile Selection

**Requirement:** MediaFile selection should consider delivery method, dimensions, bitrate, codec, and scalability.

**Implementation:**
- `SelectionStrategy.HIGHEST_BITRATE` - Select by bitrate
- `SelectionStrategy.BEST_QUALITY` - Quality-based selection
- `SelectionStrategy.CUSTOM` - User-defined selection logic

**Code:**

```python
def _select_creative(self, vast_data: dict[str, Any]) -> dict[str, Any] | None:
    """Select creative per VAST 4.2 §2.4.4.1."""
    media_files = vast_data.get("media_files", [])
    
    if self.config.selection_strategy == SelectionStrategy.HIGHEST_BITRATE:
        files_with_bitrate = [f for f in media_files if f.get("bitrate")]
        if files_with_bitrate:
            return max(files_with_bitrate, key=lambda f: f.get("bitrate", 0))
```

#### VAST 4.2 §2.3.1.4 - Impression Tracking

**Requirement:** Impression elements contain URLs that should be fired when the impression is counted.

**Implementation:**
- Resolver collects `<Impression>` URLs from all wrappers and InLine
- Accumulated in `result.vast_data["impressions"]`
- Application fires pixels when ad displays

**Code:**

```python
def _collect_impressions(self, xml: str) -> list[str]:
    """Collect impression URLs per VAST 4.2 §2.3.1.4."""
    root = etree.fromstring(xml.encode("utf-8"))
    impression_elements = root.xpath("//Impression")
    # ... extract URLs
```

#### VAST 4.2 §2.4.2.4 - Error Tracking

**Requirement:** Error elements contain URLs that should be fired with error code macro substitution when errors occur.

**Implementation:**
- Resolver collects `<Error>` URLs from all wrappers and InLine
- Supports `[ERRORCODE]` macro substitution
- Internal `_track_error()` method for firing

**Code:**

```python
async def _track_error(self, error_urls: list[str], error_code: str = "900") -> None:
    """Send error tracking URLs per VAST 4.2 §2.4.2.4."""
    expanded_urls = [url.replace("[ERRORCODE]", error_code) for url in error_urls]
    # ... fire pixels
```

### Compliance Checklist

- ✅ Wrapper chain resolution per §2.4.3.4
- ✅ Depth limit enforcement per §2.4.1.2 (default 5)
- ✅ MediaFile selection per §2.4.4.1
- ✅ Impression tracking per §2.3.1.4
- ✅ Error tracking per §2.4.2.4
- ✅ Tracking event collection per §2.3.1.5.5
- ✅ VASTAdTagURI extraction from Wrapper
- ✅ InLine detection for terminal response
- ✅ XML parsing with lxml for robustness
- ✅ Macro substitution support (via VastUpstream)

### Version Support

| VAST Version | Supported | Notes |
|--------------|-----------|-------|
| 2.0 | ✅ | Basic wrapper resolution |
| 3.0 | ✅ | Enhanced wrapper support |
| 4.0 | ✅ | Ad verification, ViewableImpression |
| 4.1 | ✅ | Audio ads (adType="audio") |
| 4.2 | ✅ | SIMID, enhanced macros (recommended) |

### Extensions Beyond Specification

The resolver includes production-ready features beyond the IAB specification:

1. **Multiple Fallback Upstreams** - Automatic fallback to secondary servers
2. **YAML Configuration** - Environment-based configuration
3. **Custom Selection Strategies** - User-defined creative selection
4. **Performance Metrics** - Resolution timing and metadata
5. **Fire-and-Forget Tracking** - Non-blocking pixel firing

These extensions maintain full VAST 4.2 compliance while adding operational capabilities for production deployment.

---

## See Also

- [VAST Protocol Documentation](./vast.md)
- [IAB VAST 4.2 Specification](https://iabtechlab.com/vast/)
- [VastUpstream API Reference](./vast.md#vastupstream)
- [Example: Basic Chain Resolution](../../examples/vast_chain_resolution.py)
- [Example: Custom Selection](../../examples/vast_custom_selector.py)
