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

## See Also

- [VAST Protocol Documentation](./vast.md)
- [IAB VAST 4.2 Specification](https://iabtechlab.com/vast/)
- [Example: Basic Chain Resolution](../../examples/vast_chain_resolution.py)
- [Example: Custom Selection](../../examples/vast_custom_selector.py)
