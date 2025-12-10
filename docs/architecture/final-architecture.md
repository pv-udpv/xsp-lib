# Final Architecture

**xsp-lib** provides a unified, protocol-agnostic framework for integrating AdTech upstream services. This document describes the complete system design, including layers, components, and data flow.

## Overview

The architecture is built on four foundational principles:

1. **Protocol Agnosticism** - TypedDict schemas allow any protocol (VAST, OpenRTB, DAAST, CATS)
2. **Transport Abstraction** - Pluggable I/O layer supports HTTP, gRPC, WebSocket, file, memory
3. **Type Safety** - Full type hints with mypy --strict compliance
4. **Session Management** - Stateful ad serving with frequency capping and budget tracking

## System Layers

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                       │
│  (Ad Server, SSP, DSP, Analytics, Frequency Capping)       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Protocol Layer                           │
│  VastUpstream | OpenRtbUpstream | DaastUpstream | ...      │
│  (VAST 3.0-4.2, OpenRTB 2.6/3.0, DAAST, CATS)              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Middleware Layer                          │
│  Retry | CircuitBreaker | Cache | Metrics | Auth           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Session Layer (NEW)                       │
│  SessionContext | UpstreamSession | FrequencyCap           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Core Abstractions                        │
│  Upstream[T] | BaseUpstream[T] | UpstreamConfig            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Transport Layer                           │
│  HttpTransport | GrpcTransport | FileTransport | ...       │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Upstream[T] Protocol

The foundation abstraction representing any AdTech service:

```python
class Upstream(Protocol[T]):
    """Universal upstream service protocol."""
    
    async def fetch(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        context: dict[str, Any] | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> T:
        """Fetch data from upstream service."""
        ...
    
    async def close(self) -> None:
        """Release resources (connections, caches, etc.)."""
        ...
    
    async def health_check(self) -> bool:
        """Verify upstream service availability."""
        ...
```

**Key Design Decisions:**
- Generic over response type `T` for type safety
- Keyword-only parameters for clarity
- `context` parameter for session state
- Protocol-based (structural typing) for flexibility

### 2. Transport Abstraction

The `Transport` protocol abstracts I/O operations:

```python
class Transport(Protocol):
    """I/O abstraction for network and file operations."""
    
    async def send(
        self,
        data: bytes,
        *,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> bytes:
        """Send data and return response."""
        ...
```

**Implementations:**
- **HttpTransport** - REST APIs, XML/JSON feeds (aiohttp-based)
- **GrpcTransport** - Binary protocols (future)
- **WebSocketTransport** - Real-time streaming (future)
- **FileTransport** - File-based fixtures for testing
- **MemoryTransport** - In-memory for unit tests

### 3. BaseUpstream[T]

`BaseUpstream[T]` composes transport with encoder/decoder logic:

```python
class BaseUpstream(Generic[T]):
    """Base implementation composing transport with codecs."""
    
    def __init__(
        self,
        transport: Transport,
        decoder: Callable[[bytes], T],
        encoder: Callable[[Any], bytes] | None = None,
        config: UpstreamConfig | None = None,
    ):
        self._transport = transport
        self._decoder = decoder
        self._encoder = encoder or self._default_encoder
        self._config = config or UpstreamConfig()
```

**Responsibilities:**
- Delegates I/O to transport
- Encodes requests (Any → bytes)
- Decodes responses (bytes → T)
- Manages default parameters, headers, timeout

### 4. SessionContext (NEW)

Immutable context for request correlation and cachebusting:

```python
@dataclass(frozen=True)
class SessionContext:
    """Request context for session management."""
    
    timestamp: int  # Unix timestamp (milliseconds)
    correlator: str  # UUID for request correlation
    cachebusting: str  # Random value for cache prevention
    cookies: dict[str, str]  # HTTP cookies
    request_id: str  # Unique request identifier
```

**Use Cases:**
- VAST macro substitution (CACHEBUSTING, TIMESTAMP)
- Request correlation across services
- Cookie management for frequency capping
- Analytics and debugging

### 5. UpstreamSession Protocol (NEW)

Stateful session management for frequency capping and budget tracking:

```python
class UpstreamSession(Protocol):
    """Protocol for stateful ad serving session."""
    
    async def request(
        self,
        context: SessionContext,
        **kwargs: Any,
    ) -> Any:
        """Execute request with session state."""
        ...
    
    async def check_frequency_cap(
        self,
        user_id: str,
        campaign_id: str,
    ) -> bool:
        """Check if user has exceeded frequency cap."""
        ...
    
    async def track_budget(
        self,
        campaign_id: str,
        cost: Decimal,
    ) -> bool:
        """Track campaign spend and check budget."""
        ...
```

### 6. UpstreamConfig (NEW)

Transport-agnostic configuration:

```python
@dataclass
class UpstreamConfig:
    """Configuration for upstream services."""
    
    timeout: float = 30.0
    max_retries: int = 3
    encoding: str = "utf-8"
    encoding_config: dict[str, Any] | None = None  # e.g., Cyrillic preservation
    default_headers: dict[str, str] | None = None
    default_params: dict[str, Any] | None = None
```

## Data Flow

### Standard Request Flow

```
Application
    ↓ calls fetch()
VastUpstream (Protocol-specific logic)
    ↓ delegates to BaseUpstream
BaseUpstream
    ↓ encodes request
    ↓ applies middleware (retry, circuit breaker)
SessionContext (correlation, cachebusting)
    ↓
Transport (HttpTransport)
    ↓ HTTP POST/GET
Upstream Service (VAST ad server)
    ↓ XML/JSON response
Transport
    ↓ bytes
BaseUpstream
    ↓ decodes response (bytes → VastResponse)
    ↓ validates schema
VastUpstream
    ↓ returns typed response
Application
```

### Session-Aware Request Flow (NEW)

```
Application
    ↓ creates SessionContext
UpstreamSession
    ↓ check_frequency_cap()
    ↓ track_budget()
    ↓ request(context)
VastUpstream
    ↓ substitutes macros (CACHEBUSTING, TIMESTAMP)
    ↓ delegates to BaseUpstream
BaseUpstream → Transport → Upstream Service
    ↓ response
UpstreamSession
    ↓ updates frequency cap counters
    ↓ updates budget tracking
Application
```

## Middleware System

Middleware wraps upstreams for cross-cutting concerns:

```python
class RetryMiddleware:
    """Exponential backoff retry logic."""
    
    def __init__(self, upstream: Upstream[T], max_retries: int = 3):
        self._upstream = upstream
        self._max_retries = max_retries
    
    async def fetch(self, **kwargs: Any) -> T:
        for attempt in range(self._max_retries):
            try:
                return await self._upstream.fetch(**kwargs)
            except TransientError:
                await asyncio.sleep(2 ** attempt)
        raise MaxRetriesExceeded()
```

**Available Middleware:**
- **Retry** - Exponential backoff with jitter
- **CircuitBreaker** - Fail-fast for degraded upstreams (future)
- **Cache** - Response caching with TTL (future)
- **Metrics** - Prometheus/OpenTelemetry (future)
- **Auth** - JWT/OAuth2 token management (future)

## Protocol Implementations

### VAST 3.0-4.2 (Issue #2)

```python
class VastUpstream(BaseUpstream[VastResponse]):
    """VAST video ad serving upstream."""
    
    async def fetch(
        self,
        *,
        params: dict[str, Any] | None = None,
        context: SessionContext | None = None,
        **kwargs: Any,
    ) -> VastResponse:
        # Substitute VAST macros
        if context:
            params = self._substitute_macros(params, context)
        
        # Delegate to BaseUpstream
        return await super().fetch(params=params, **kwargs)
    
    def _substitute_macros(
        self,
        params: dict[str, Any],
        context: SessionContext,
    ) -> dict[str, Any]:
        """Substitute VAST macros per IAB VAST 4.2 §4.1."""
        return {
            k: str(v)
                .replace("[CACHEBUSTING]", context.cachebusting)
                .replace("[TIMESTAMP]", str(context.timestamp))
            for k, v in params.items()
        }
```

### OpenRTB 2.6 (Issue #3)

```python
class OpenRtbUpstream(BaseUpstream[BidResponse]):
    """OpenRTB real-time bidding upstream."""
    
    async def fetch(
        self,
        bid_request: BidRequest,
        *,
        timeout: float = 0.3,  # per OpenRTB 2.6 §4.1
        **kwargs: Any,
    ) -> BidResponse:
        # Encode bid request to JSON
        data = self._encoder(bid_request)
        
        # Send via transport
        response_bytes = await self._transport.send(
            data=data,
            url=self._config.endpoint,
            timeout=timeout,
        )
        
        # Decode bid response
        return self._decoder(response_bytes)
```

## Design Patterns

### 1. Protocol-Based Design

Use `Protocol` for structural typing:

```python
class MyCustomUpstream:
    """Custom upstream without inheriting from base class."""
    
    async def fetch(self, **kwargs: Any) -> MyResponse:
        # Implementation
        ...
    
    async def close(self) -> None:
        ...
    
    async def health_check(self) -> bool:
        ...
```

✅ Satisfies `Upstream[MyResponse]` protocol automatically

### 2. TypedDict Schemas

Use `TypedDict` for protocol-agnostic data:

```python
class VastAdSchema(TypedDict):
    """VAST ad schema (protocol-agnostic)."""
    
    id: str
    duration: int
    creative_url: str
    tracking_urls: list[str]
```

### 3. Dependency Injection

Inject transport and config:

```python
# Production
transport = HttpTransport(pool_size=100)
upstream = VastUpstream(transport=transport, config=config)

# Testing
transport = MemoryTransport(fixture_data)
upstream = VastUpstream(transport=transport, config=config)
```

## Error Handling

### Exception Hierarchy

```python
class XspError(Exception):
    """Base exception for xsp-lib."""

class TransportError(XspError):
    """Transport-level error (network, I/O)."""

class ProtocolError(XspError):
    """Protocol-level error (parsing, validation)."""

class UpstreamError(XspError):
    """Upstream service error (HTTP 4xx/5xx)."""

class TimeoutError(XspError):
    """Request timeout."""

class CircuitBreakerOpen(XspError):
    """Circuit breaker is open (upstream degraded)."""
```

### Error Handling Pattern

```python
try:
    response = await upstream.fetch(params=params)
except TimeoutError:
    logger.error("Request timeout", extra={"params": params})
    # Fallback logic
except UpstreamError as e:
    logger.error("Upstream error", extra={"status": e.status_code})
    # Return default ad
except XspError as e:
    logger.exception("Unexpected error")
    # Re-raise or handle
```

## Testing Strategy

### Unit Tests

```python
@pytest.mark.asyncio
async def test_vast_upstream():
    transport = MemoryTransport(fixture_data=VAST_XML)
    upstream = VastUpstream(transport=transport)
    
    response = await upstream.fetch(params={"placement_id": "123"})
    
    assert response.ad.duration == 30
    assert len(response.ad.tracking_urls) > 0
```

### Integration Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_vast_upstream_real_service():
    transport = HttpTransport()
    upstream = VastUpstream(
        transport=transport,
        config=UpstreamConfig(timeout=5.0),
    )
    
    response = await upstream.fetch(
        params={"app_id": "test"},
    )
    
    assert response.ad is not None
```

## Performance Considerations

### Connection Pooling

```python
# HttpTransport uses aiohttp with connection pooling
transport = HttpTransport(
    pool_size=100,  # Max concurrent connections
    keepalive=True,  # Reuse connections
)
```

### Timeouts

```python
# Per-request timeout
await upstream.fetch(timeout=0.3)  # 300ms for OpenRTB

# Default timeout in config
config = UpstreamConfig(timeout=30.0)  # 30s for VAST
```

### Caching (Future)

```python
# Cache middleware for VAST responses
cached_upstream = CacheMiddleware(
    upstream=vast_upstream,
    ttl=3600,  # 1 hour
)
```

## Configuration Management

### Environment-Based Configuration

```python
# .env file
XSP_ENV=production
XSP_VAST_ENDPOINT=https://ads.example.com/vast
XSP_VAST_TIMEOUT=30.0
XSP_OPENRTB_ENDPOINT=https://bidder.example.com/openrtb
XSP_OPENRTB_TIMEOUT=0.3

# Application
from xsp.core.config import get_settings

settings = get_settings()
vast_config = UpstreamConfig(
    endpoint=settings.vast_endpoint,
    timeout=settings.vast_timeout,
)
```

### Per-Protocol Configuration

```python
# VAST configuration
vast_config = UpstreamConfig(
    timeout=30.0,
    encoding="utf-8",
    default_headers={"X-API-Key": "secret"},
)

# OpenRTB configuration
openrtb_config = UpstreamConfig(
    timeout=0.3,  # Low latency for RTB
    encoding="utf-8",
    default_headers={"X-Bidder-ID": "123"},
)
```

## Directory Structure

```
src/xsp/
├── core/
│   ├── __init__.py
│   ├── upstream.py         # Upstream[T] protocol
│   ├── transport.py        # Transport protocol
│   ├── base.py             # BaseUpstream[T]
│   ├── session.py          # SessionContext, UpstreamSession (NEW)
│   ├── config.py           # XspSettings, UpstreamConfig (UPDATED)
│   ├── exceptions.py       # Exception hierarchy
│   └── types.py            # Common type aliases
├── transports/
│   ├── http.py             # HttpTransport
│   ├── file.py             # FileTransport
│   └── memory.py           # MemoryTransport
├── middleware/
│   ├── retry.py            # RetryMiddleware
│   ├── circuit_breaker.py  # CircuitBreakerMiddleware (future)
│   └── cache.py            # CacheMiddleware (future)
├── protocols/
│   ├── vast/
│   │   ├── types.py        # VAST TypedDict schemas
│   │   ├── upstream.py     # VastUpstream
│   │   └── macros.py       # VAST macro substitution
│   ├── openrtb/
│   │   ├── types.py        # OpenRTB TypedDict schemas
│   │   └── upstream.py     # OpenRtbUpstream
│   └── daast/              # DEPRECATED (use VAST 4.1+ adType="audio")
└── utils/
    ├── encoding.py         # Cyrillic preservation
    └── validation.py       # Schema validation
```

## Migration Guide

### From Legacy "fetch" to Session-Aware

**Before:**
```python
response = await upstream.fetch(params={"placement_id": "123"})
```

**After (with SessionContext):**
```python
from xsp.core.session import SessionContext

context = SessionContext.create()  # Auto-generates correlator, etc.
response = await upstream.fetch(params={"placement_id": "123"}, context=context)
```

**After (with UpstreamSession):**
```python
session = UpstreamSession(upstream=upstream)
response = await session.request(
    context=context,
    params={"placement_id": "123"},
)
```

### Backward Compatibility

All existing code continues to work:
- `fetch()` without `context` parameter works as before
- `SessionContext` is optional for all upstreams
- `UpstreamSession` is opt-in for stateful scenarios

## Future Roadmap

1. **OpenRTB 3.0 + AdCOM** (after OpenRTB 2.6)
2. **CATS** - Common AdTech Services
3. **gRPC Transport** - Binary protocols
4. **Circuit Breaker Middleware** - Fault tolerance
5. **Cache Middleware** - Response caching
6. **Metrics Middleware** - Prometheus/OpenTelemetry
7. **WebSocket Transport** - Real-time streaming
8. **Auth Middleware** - JWT/OAuth2

## References

- [VAST 4.2 Specification](https://iabtechlab.com/standards/vast/) - IAB Tech Lab
- [OpenRTB 2.6 Specification](https://iabtechlab.com/standards/openrtb/) - IAB Tech Lab
- [AdCOM Specification](https://iabtechlab.com/standards/openmedia/) - IAB Tech Lab
- [Python Type Hints](https://docs.python.org/3/library/typing.html) - Python.org
- [Structural Typing with Protocols](https://peps.python.org/pep-0544/) - PEP 544

## Related Documentation

- [Session Management Architecture](./session-management.md)
- [Terminology Guide](./terminology.md)
- [Protocol-Agnostic Design](./protocol-agnostic-design.md)
- [Session Management Guide](../guides/session-management.md)
- [Stateful Ad Serving Guide](../guides/stateful-ad-serving.md)
