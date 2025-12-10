# Protocol-Agnostic Orchestrator

The orchestrator provides a unified interface for ad serving across multiple AdTech protocols (VAST, VMAP, OpenRTB, custom) with common cross-cutting concerns like caching and tracking.

## Overview

The orchestrator layer consists of three main components:

1. **Flexible Schemas** (`AdRequest`, `AdResponse`) - TypedDict-based schemas that work across protocols
2. **Protocol Handler Interface** (`ProtocolHandler`) - ABC for protocol-specific implementations
3. **Orchestrator** - Main orchestration class with caching and coordination

## Architecture

```
┌────────────────────────────────────────────────────┐
│           Application Layer                        │
│  orchestrator.fetch_ad(AdRequest(...))             │
└─────────────────────┬──────────────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────────────┐
│        Orchestrator (Protocol-Agnostic)            │
│  • Request validation                              │
│  • Response caching                                │
│  • Event tracking                                  │
│  • Error handling                                  │
└─────────────────────┬──────────────────────────────┘
                      │
         ┌────────────┼────────────┐
         │            │            │
         ▼            ▼            ▼
  ┌──────────┐ ┌──────────┐ ┌──────────┐
  │   VAST   │ │   VMAP   │ │ OpenRTB  │
  │ Handler  │ │ Handler  │ │ Handler  │
  └────┬─────┘ └────┬─────┘ └────┬─────┘
       │            │            │
       ▼            ▼            ▼
  VastUpstream  VmapUpstream  RTBUpstream
```

## Quick Start

### Basic Usage

```python
from xsp.orchestrator import AdRequest, Orchestrator
from xsp.protocols.vast import VastProtocolHandler, VastUpstream
from xsp.transports.http import HttpTransport

# Create VAST upstream
transport = HttpTransport()
vast_upstream = VastUpstream(
    transport=transport,
    endpoint="https://ads.example.com/vast",
)

# Create protocol handler
vast_handler = VastProtocolHandler(upstream=vast_upstream)

# Create orchestrator
orchestrator = Orchestrator(
    protocol_handler=vast_handler,
    enable_caching=True,
    cache_ttl=3600,
)

# Fetch ad
response = await orchestrator.fetch_ad(
    AdRequest(
        slot_id="pre-roll",
        user_id="user123",
        device_type="mobile",
    )
)

# Track event
if response["success"]:
    await orchestrator.track_event("impression", response)
```

## Schemas

### AdRequest

Protocol-agnostic ad request with required and optional fields.

**Required fields:**
- `slot_id`: Ad slot identifier
- `user_id`: User identifier

**Optional common fields:**
- `ip_address`: Client IP address
- `device_type`: Device type ('desktop', 'mobile', 'tablet', 'tv')
- `content_url`: URL of content being played
- `content_duration`: Total content duration in seconds
- `playhead_position`: Current playback position in seconds
- `player_size`: Player dimensions (width, height)
- `geo`: Geographic information dict

**Protocol-specific:**
- `extensions`: Dictionary for protocol-specific fields

### AdResponse

Protocol-agnostic ad response.

**Required fields:**
- `success`: Whether ad fetch was successful
- `slot_id`: Ad slot identifier (echoed from request)

**Optional fields:**
- Creative details: `ad_id`, `creative_url`, `creative_type`, `format`, `duration`, `bitrate`, `dimensions`
- Tracking: `tracking_urls`
- Metadata: `ad_system`, `advertiser`, `campaign_id`
- Resolution info: `resolution_chain`, `used_fallback`, `cached`, `resolution_time_ms`
- Error info: `error`, `error_code`
- Protocol-specific: `extensions`, `raw_response`

## Protocol Handlers

### Creating a Protocol Handler

Implement the `ProtocolHandler` ABC:

```python
from xsp.orchestrator.protocol import ProtocolHandler
from xsp.orchestrator.schemas import AdRequest, AdResponse

class MyProtocolHandler(ProtocolHandler):
    async def fetch(self, request: AdRequest, **context) -> AdResponse:
        # Map AdRequest to protocol-specific parameters
        # Fetch from upstream
        # Map response to AdResponse
        pass

    async def track(self, event: str, response: AdResponse, **context) -> None:
        # Fire tracking URLs
        pass

    def validate_request(self, request: AdRequest) -> bool:
        # Validate request has required fields
        return "slot_id" in request and "user_id" in request
```

### VAST Protocol Handler

Maps `AdRequest` to VAST parameters and `AdResponse` to VAST XML responses.

```python
from xsp.protocols.vast import VastProtocolHandler, VastUpstream

handler = VastProtocolHandler(upstream=vast_upstream)
```

## Features

### ✅ Protocol-Agnostic

Same API works across VAST, VMAP, OpenRTB, and custom protocols:

```python
# VAST
orchestrator = Orchestrator(protocol_handler=vast_handler)

# OpenRTB
orchestrator = Orchestrator(protocol_handler=openrtb_handler)

# Same fetch_ad() call for both!
response = await orchestrator.fetch_ad(request)
```

### ✅ Type-Safe

Full TypedDict support with IDE autocomplete and mypy checking:

```python
request: AdRequest = AdRequest(
    slot_id="pre-roll",
    user_id="user123",
)

response: AdResponse = await orchestrator.fetch_ad(request)
```

### ✅ Flexible

Extensions dict allows protocol-specific fields:

```python
# VAST-specific extensions
response["extensions"]["vast_xml"]

# OpenRTB-specific extensions
response["extensions"]["bid_price"]
```

### ✅ Cacheable

Unified caching layer with pluggable backends:

```python
orchestrator = Orchestrator(
    protocol_handler=handler,
    cache=MemoryCache(),  # or RedisCache()
    enable_caching=True,
    cache_ttl=3600,
)
```

### ✅ Observable

Tracks resolution chain, fallbacks, and cache hits:

```python
response["resolution_chain"]  # List of upstream URLs used
response["used_fallback"]     # Whether fallback was used
response["cached"]            # Whether from cache
response["resolution_time_ms"] # Resolution time
```

## Testing

### Unit Tests

Mock protocol handlers for testing:

```python
from xsp.orchestrator import Orchestrator
from xsp.orchestrator.protocol import ProtocolHandler

class MockHandler(ProtocolHandler):
    async def fetch(self, request, **context):
        return AdResponse(success=True, slot_id=request["slot_id"])

    async def track(self, event, response, **context):
        pass

    def validate_request(self, request):
        return True

orchestrator = Orchestrator(protocol_handler=MockHandler())
```

### Integration Tests

Use memory transport for predictable responses:

```python
from xsp.transports.memory import MemoryTransport
from xsp.protocols.vast import VastUpstream, VastProtocolHandler

transport = MemoryTransport(sample_vast_xml.encode())
upstream = VastUpstream(transport=transport, endpoint="memory://vast")
handler = VastProtocolHandler(upstream=upstream)
orchestrator = Orchestrator(protocol_handler=handler)
```

## Examples

See `examples/orchestrator_vast_example.py` for a complete working example.

## Future Enhancements

The following features are planned for future releases:

- Configuration loading from YAML (`Orchestrator.from_config()`)
- Additional protocol handlers (VMAP, OpenRTB)
- Redis cache backend
- Metrics and observability hooks
- Retry and circuit breaker integration

## API Reference

### Orchestrator

Main orchestrator class.

**Constructor:**
```python
Orchestrator(
    protocol_handler: ProtocolHandler,
    cache: CacheBackend | None = None,
    enable_caching: bool = True,
    cache_ttl: int = 3600,
)
```

**Methods:**
- `fetch_ad(request: AdRequest) -> AdResponse` - Fetch ad
- `track_event(event: str, response: AdResponse) -> None` - Track event

### ProtocolHandler (ABC)

Protocol handler interface.

**Methods:**
- `fetch(request: AdRequest, **context) -> AdResponse` - Fetch ad
- `track(event: str, response: AdResponse, **context) -> None` - Track event
- `validate_request(request: AdRequest) -> bool` - Validate request

### CacheBackend (ABC)

Cache backend interface.

**Methods:**
- `get(key: str) -> AdResponse | None` - Get from cache
- `set(key: str, value: AdResponse, ttl: int) -> None` - Set in cache
