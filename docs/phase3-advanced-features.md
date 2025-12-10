# Phase 3: Advanced Features - Protocol Handlers and Orchestration

This document describes the Phase 3 implementation of the xsp-lib architecture, which provides protocol-specific handlers and high-level orchestration capabilities.

## Overview

Phase 3 introduces:
- **State Backend Abstraction**: Key-value storage for caching and session management
- **Protocol Handler Interface**: Unified interface for protocol-specific implementations
- **VAST Chain Resolver**: Resolves VAST wrapper chains with session support
- **VAST Protocol Handler**: Maps generic AdRequest to VAST-specific parameters
- **Orchestrator**: Protocol-agnostic ad serving with routing and caching

## Components

### 1. State Backend (`src/xsp/core/state.py`)

Provides key-value storage for session data and caching.

#### StateBackend Protocol

```python
from xsp.core.state import StateBackend

class StateBackend(Protocol):
    async def get(self, key: str) -> Any | None: ...
    async def set(self, key: str, value: Any, *, ttl: float | None = None) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def exists(self, key: str) -> bool: ...
    async def close(self) -> None: ...
```

#### Implementations

**InMemoryStateBackend** - Simple in-memory storage for testing:
```python
from xsp.core.state import InMemoryStateBackend

backend = InMemoryStateBackend()
await backend.set("key", "value")
result = await backend.get("key")  # "value"
```

**RedisStateBackend** - Production-ready distributed storage:
```python
from xsp.core.state import RedisStateBackend
import redis.asyncio as redis

client = await redis.from_url("redis://localhost")
backend = RedisStateBackend(client)
await backend.set("key", "value", ttl=300)  # 5 minute TTL
```

### 2. Protocol Abstractions (`src/xsp/core/protocol.py`)

#### AdRequest

Universal ad request across all protocols:

```python
from xsp import AdRequest

request = AdRequest(
    user_id="user123",
    ip_address="192.168.1.1",
    url="https://example.com/video",
    placement_id="homepage-banner",
    protocol="vast",  # Optional, can be auto-detected
    params={"format": "video"},
    context={"playhead": 0},
    headers={"Cookie": "session=abc"},
)
```

#### AdResponse

Universal ad response with protocol-specific data:

```python
response = AdResponse(
    protocol="vast",
    data="<VAST>...</VAST>",  # XML string or JSON dict
    status="success",  # or "error"
    error=None,
    metadata={"user_id": "user123"},
)
```

#### ProtocolHandler

Interface for protocol implementations:

```python
class ProtocolHandler(Protocol):
    @property
    def protocol_name(self) -> str: ...
    
    async def handle(self, request: AdRequest) -> AdResponse: ...
    async def close(self) -> None: ...
```

### 3. VAST Chain Resolver (`src/xsp/protocols/vast/chain_resolver.py`)

Resolves VAST wrapper chains following redirects until an inline ad is reached.

#### Features

- **Max Depth Protection**: Prevents infinite loops (default 5 per VAST 4.2 §3.4.1)
- **Session Support**: Propagates headers across redirects
- **Error Handling**: Graceful handling of malformed VAST

#### Usage

```python
from xsp.protocols.vast import ChainResolver, VastUpstream
from xsp.transports.http import HttpTransport

transport = HttpTransport()
upstream = VastUpstream(
    transport=transport,
    endpoint="https://ads.example.com/vast"
)

resolver = ChainResolver(
    upstream=upstream,
    max_depth=5,  # VAST 4.2 recommendation
    propagate_headers=True,
)

# Resolve wrapper chain
vast_xml = await resolver.resolve(
    params={"user_id": "123"},
    headers={"Cookie": "session=abc"},
)

await resolver.close()
```

#### Error Handling

```python
from xsp.protocols.vast import MaxDepthExceededError, ChainResolutionError

try:
    vast_xml = await resolver.resolve()
except MaxDepthExceededError:
    # Too many wrappers
    print("Maximum wrapper depth exceeded")
except ChainResolutionError as e:
    # Other resolution errors
    print(f"Resolution failed: {e}")
```

### 4. VAST Protocol Handler (`src/xsp/protocols/vast/handler.py`)

Maps AdRequest to VAST parameters and delegates to ChainResolver.

#### Parameter Mapping

- `user_id` → `uid` parameter
- `ip_address` → `ip` parameter  
- `url` → `url` parameter
- `placement_id` → `placement_id` parameter
- Additional params from `request.params`

#### Usage

```python
from xsp import AdRequest
from xsp.protocols.vast import ChainResolver, VastProtocolHandler, VastUpstream
from xsp.transports.http import HttpTransport

# Setup
transport = HttpTransport()
upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")
resolver = ChainResolver(upstream=upstream)
handler = VastProtocolHandler(chain_resolver=resolver)

# Handle request
request = AdRequest(
    user_id="user123",
    ip_address="192.168.1.1",
    url="https://example.com/video",
)

response = await handler.handle(request)
print(f"Status: {response.status}")
print(f"VAST XML: {response.data}")

await handler.close()
```

### 5. Orchestrator (`src/xsp/orchestrator/orchestrator.py`)

Protocol-agnostic ad serving with routing, caching, and error handling.

#### Features

- **Protocol Routing**: Routes requests to appropriate handlers
- **Caching**: Optional response caching with StateBackend
- **Auto-detection**: Detects protocol from request
- **Error Handling**: Unified error responses

#### Basic Usage

```python
from xsp import AdRequest, Orchestrator
from xsp.protocols.vast import ChainResolver, VastProtocolHandler, VastUpstream
from xsp.transports.http import HttpTransport

# Setup VAST handler
transport = HttpTransport()
upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")
resolver = ChainResolver(upstream=upstream)
vast_handler = VastProtocolHandler(chain_resolver=resolver)

# Create orchestrator
orchestrator = Orchestrator(
    handlers={"vast": vast_handler}
)

# Serve ad
request = AdRequest(protocol="vast", user_id="user123")
response = await orchestrator.serve(request)

await orchestrator.close()
```

#### With Caching

```python
from xsp import InMemoryStateBackend, Orchestrator

cache_backend = InMemoryStateBackend()

orchestrator = Orchestrator(
    handlers={"vast": vast_handler},
    cache_backend=cache_backend,
    enable_caching=True,
    cache_ttl=300.0,  # 5 minutes
)

# First request - fetches from upstream
response1 = await orchestrator.serve(request)

# Second identical request - served from cache
response2 = await orchestrator.serve(request)
```

#### Multiple Protocols

```python
# Future: Add OpenRTB handler
# openrtb_handler = OpenRtbProtocolHandler(...)

orchestrator = Orchestrator(
    handlers={
        "vast": vast_handler,
        # "openrtb": openrtb_handler,
        # "daast": daast_handler,
    }
)

# Route to VAST
vast_request = AdRequest(protocol="vast", user_id="user123")
vast_response = await orchestrator.serve(vast_request)

# Route to OpenRTB (when implemented)
# rtb_request = AdRequest(protocol="openrtb", ...)
# rtb_response = await orchestrator.serve(rtb_request)
```

#### Register Handlers Dynamically

```python
orchestrator = Orchestrator()

# Register handlers
orchestrator.register_handler("vast", vast_handler)
# orchestrator.register_handler("openrtb", openrtb_handler)

# Serve requests
response = await orchestrator.serve(request)
```

## Architecture

### Request Flow

```
AdRequest
    ↓
Orchestrator
    ↓ (check cache)
    ↓ (route by protocol)
    ↓
ProtocolHandler (e.g., VastProtocolHandler)
    ↓ (map to protocol params)
    ↓
ChainResolver
    ↓ (resolve wrappers)
    ↓
VastUpstream
    ↓
Transport (HTTP/Memory/File)
    ↓
Response ← Wrapper chain resolution
    ↓
AdResponse (with VAST XML)
    ↓ (cache if enabled)
    ↓
Return to caller
```

### Component Diagram

```
┌─────────────────────────────────────────────┐
│          Orchestrator                       │
│  ┌────────────┐      ┌──────────────────┐  │
│  │  Routing   │      │  Caching Layer   │  │
│  └────────────┘      └──────────────────┘  │
└─────────────────────────────────────────────┘
           │                         │
           ↓                         ↓
  ┌────────────────┐         ┌──────────────┐
  │ ProtocolHandler│         │ StateBackend │
  │   (VAST)       │         │   (Redis)    │
  └────────────────┘         └──────────────┘
           │
           ↓
  ┌────────────────┐
  │ ChainResolver  │
  │  (Max Depth)   │
  └────────────────┘
           │
           ↓
  ┌────────────────┐
  │ VastUpstream   │
  └────────────────┘
           │
           ↓
  ┌────────────────┐
  │   Transport    │
  │   (HTTP)       │
  └────────────────┘
```

## Testing

All components include comprehensive unit tests:

- **State Backends**: 6 tests (`tests/unit/core/test_state.py`)
- **Chain Resolver**: 5 tests (`tests/unit/protocols/test_vast_chain_resolver.py`)
- **Protocol Handler**: 5 tests (`tests/unit/protocols/test_vast_handler.py`)
- **Orchestrator**: 7 tests (`tests/unit/test_orchestrator.py`)

Run tests:
```bash
pytest tests/unit/core/test_state.py -v
pytest tests/unit/protocols/test_vast_chain_resolver.py -v
pytest tests/unit/protocols/test_vast_handler.py -v
pytest tests/unit/test_orchestrator.py -v
```

## Type Safety

All components pass strict mypy checking:

```bash
mypy src/xsp/core/protocol.py --strict
mypy src/xsp/core/state.py --strict
mypy src/xsp/protocols/vast/chain_resolver.py --strict
mypy src/xsp/protocols/vast/handler.py --strict
mypy src/xsp/orchestrator/ --strict
```

## Future Enhancements

### OpenRTB Protocol Handler

```python
# To be implemented
class OpenRtbProtocolHandler:
    async def handle(self, request: AdRequest) -> AdResponse:
        # Map AdRequest to BidRequest
        # Call OpenRTB upstream
        # Return BidResponse as AdResponse
        ...
```

### DAAST Protocol Handler

```python
# To be implemented (deprecated - use VAST with adType="audio")
class DaastProtocolHandler:
    # Note: DAAST deprecated, use VastProtocolHandler with adType="audio"
    ...
```

### Advanced Caching Strategies

- Cache invalidation
- Cache warming
- Distributed caching with Redis cluster
- Cache metrics and monitoring

### Session Management

- Cookie propagation across wrapper chains
- Session affinity
- User tracking

## References

- [VAST 4.2 Specification](https://www.iab.com/guidelines/vast/) - §3.4.1 on wrapper chains
- Phase 1: Core Infrastructure (Issue #34)
- Phase 2: Protocol Implementations (Issue #40)

## Examples

See `examples/orchestrator_example.py` for a complete working example.
