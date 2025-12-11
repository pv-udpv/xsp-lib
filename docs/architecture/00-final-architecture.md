# xsp-lib Architecture Overview

**Version:** 1.0  
**Date:** December 10, 2025  
**Status:** Phase 1 Foundation Complete  

## Table of Contents

1. [System Overview](#system-overview)
2. [Design Principles](#design-principles)
3. [Layer Architecture](#layer-architecture)
4. [Core Abstractions](#core-abstractions)
5. [Protocol System](#protocol-system)
6. [Session Management](#session-management)
7. [Configuration System](#configuration-system)
8. [Middleware System](#middleware-system)
9. [Error Handling](#error-handling)
10. [Type Safety](#type-safety)
11. [Integration Patterns](#integration-patterns)
12. [Future Extensions](#future-extensions)

---

## System Overview

xsp-lib is a **universal AdTech service protocol library** providing pluggable support for multiple advertising protocols:

### Supported Protocols

- **VAST 4.2** - Video Advertising Serving Template
- **VPAID 2.0** - Video Player Ad Interface Definition
- **VMAP 1.0** - Video Multiple Ad Playlist
- **OpenRTB 2.6/3.0** - Real-Time Bidding
- **DAAST** - Digital Audio Ad Serving Template (deprecated)
- **CATS** - Common AdTech Services

### Core Capabilities

- **Pluggable Transports** - HTTP, gRPC, WebSocket, File, Memory
- **Middleware System** - Retry, Circuit Breaker, Cache, Metrics
- **Session Management** - Stateful ad serving with frequency capping
- **Configuration Abstraction** - Declarative, transport-agnostic config
- **Type Safety** - Full mypy strict compliance
- **Error Recovery** - Automatic retries with exponential backoff

---

## Design Principles

### 1. Protocol Abstraction

**Principle:** Each protocol is independent; the library doesn't force one "canonical" request/response format.

**Implementation:**
- Each protocol has its own handler (VastUpstream, OpenRtbUpstream, etc.)
- Type-safe request/response with TypedDict or dataclass per protocol
- Common middleware interface for all protocols

### 2. Transport Abstraction

**Principle:** Swappable transport layer; business logic doesn't care if it's HTTP or gRPC.

**Implementation:**
- Transport interface with send() method
- Supports HTTP, gRPC, WebSocket, File, Memory
- No protocol-specific transport logic
- Middleware wraps transport for cross-cutting concerns

### 3. Composition Over Inheritance

**Principle:** Build complex behaviors by composing simple pieces.

**Implementation:**
- Middleware chains (not decorator pattern)
- Session context passed through call stack (not stored globally)
- Protocol handlers are stateless; state lives in SessionContext

### 4. Immutability by Default

**Principle:** Prefer immutable data structures for safety in concurrent contexts.

**Implementation:**
- SessionContext is frozen dataclass
- UpstreamConfig is immutable
- State mutations only in dedicated StateBackend

### 5. Explicit Over Implicit

**Principle:** All behavior is explicit and configurable; no "magic".

**Implementation:**
- All retries/timeouts/limits are explicit parameters
- No global state except for configuration registry
- All errors are typed and handled explicitly

---

## Layer Architecture

```
┌─────────────────────────────────────────────┐
│         Application Layer                    │
│  (Your application code)                     │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│      Protocol Handler Layer                  │
│  • VastUpstream                              │
│  • OpenRtbUpstream                           │
│  • Type-safe request/response handling       │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│       Middleware Layer                       │
│  • Retry (exponential backoff)               │
│  • Circuit Breaker (failure detection)       │
│  • Cache (response caching)                  │
│  • Metrics (latency/error tracking)          │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│      Session Management Layer                │
│  • SessionContext (immutable state)          │
│  • UpstreamSession (stateful operations)     │
│  • StateBackend (persistence)                │
│  • Frequency capping                         │
│  • Budget tracking                           │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│      Transport Layer                         │
│  • HttpTransport                             │
│  • GrpcTransport                             │
│  • WebSocketTransport                        │
│  • FileTransport (testing)                   │
│  • MemoryTransport (testing)                 │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│       Network Layer                          │
│  (HTTP, gRPC, WebSocket, File, Memory)       │
└─────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Responsibility | Examples |
|-------|-----------------|----------|
| Application | Business logic | Ad selection, targeting decisions |
| Protocol | Protocol-specific handling | VAST XML parsing, OpenRTB bidding |
| Middleware | Cross-cutting concerns | Retry, circuit breaker, caching |
| Session | Stateful operations | Frequency capping, budget tracking |
| Transport | Protocol-agnostic delivery | HTTP requests, gRPC calls |
| Network | Physical communication | TCP/IP, DNS, TLS |

---

## Core Abstractions

### 1. Upstream

**Purpose:** Base class for all protocol upstreams.

```python
class BaseUpstream(Generic[ResponseT]):
    """Base class for all upstreams."""
    
    async def fetch(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> ResponseT:
        """Fetch from upstream with configuration applied."""
```

### 2. SessionContext

**Purpose:** Immutable session state shared across wrapper chain.

```python
@dataclass(frozen=True)
class SessionContext:
    """Immutable session context."""
    timestamp: int                  # Unix milliseconds
    correlator: str                 # Unique session ID
    cachebusting: str               # Random for cache-busting
    cookies: dict[str, str]         # HTTP cookies
    request_id: str                 # Request tracing ID
```

### 3. UpstreamConfig

**Purpose:** Transport-agnostic configuration.

```python
@dataclass
class UpstreamConfig:
    """Configuration for upstream services."""
    endpoint: str                   # Service endpoint
    params: dict[str, str]          # Default parameters
    headers: dict[str, str]         # Default headers
    encoding_config: dict[str, bool] # URL encoding options
    timeout: float                  # Request timeout
    max_retries: int                # Max retry attempts
```

### 4. Transport

**Purpose:** Protocol-agnostic request delivery.

```python
class Transport(Protocol):
    """Protocol for transport implementations."""
    
    async def send(
        self,
        *,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        """Send request and return response."""
```

---

## Protocol System

Each protocol handler manages protocol-specific logic:

### VAST Handler

```python
class VastUpstream(BaseUpstream[str]):
    """VAST protocol upstream."""
    
    async def fetch(self, *, params: dict | None = None) -> str:
        # Returns VAST XML response
        # Handles macro substitution
        # Manages wrapper chain resolution
```

### OpenRTB Handler

```python
class OpenRtbUpstream(BaseUpstream[OpenRtbResponse]):
    """OpenRTB protocol upstream."""
    
    async def fetch(self, *, params: dict | None = None) -> OpenRtbResponse:
        # Returns OpenRTB response object
        # Handles bid validation
        # Manages winner determination
```

### Type Safety

Each protocol defines its own request/response types:

```python
class VastRequest(TypedDict, total=False):
    """VAST request parameters."""
    adcount: int
    timestamp: int
    correlator: str
    # ... VAST-specific fields

class OpenRtbRequest(TypedDict, total=False):
    """OpenRTB request parameters."""
    id: str
    imp: list[dict]
    site: dict
    # ... OpenRTB-specific fields
```

---

## Session Management

### StatefulSession Pattern

```python
class UpstreamSession(Protocol):
    """Protocol for stateful sessions."""
    
    @property
    def context(self) -> SessionContext:
        """Get immutable session context."""
    
    async def request(self, *, params: dict | None = None) -> str:
        """Send request within session context."""
    
    async def check_frequency_cap(self, user_id: str) -> bool:
        """Check if user exceeded frequency cap."""
    
    async def track_budget(self, campaign_id: str, amount: float) -> None:
        """Track budget spend for campaign."""
    
    async def close(self) -> None:
        """Release session resources."""
```

### StateBackend

Sessions use StateBackend for persistence:

```python
class StateBackend(Protocol):
    """Protocol for state persistence."""
    
    async def get_frequency_cap(self, user_id: str) -> int:
        """Get ad count for user."""
    
    async def increment_frequency_cap(self, user_id: str) -> None:
        """Increment ad count for user."""
    
    async def get_budget(self, campaign_id: str) -> float:
        """Get spend for campaign."""
    
    async def add_spend(self, campaign_id: str, amount: float) -> None:
        """Add spend for campaign."""
```

Implementations:
- **RedisBackend** - For distributed systems
- **InMemoryBackend** - For testing/single-process
- **DatabaseBackend** - For persistence

---

## Configuration System

### Declarative Configuration

```toml
# config.toml
[vast]
endpoint = "https://ads.example.com/vast"
version = "4.2"
enable_macros = true
timeout = 30.0
max_retries = 3

[openrtb]
endpoint = "https://rtb.example.com/bid"
version = "2.6"
timeout = 100.0
max_retries = 2
```

### @configurable Decorator

```python
@configurable(namespace="vast", description="VAST upstream")
class VastUpstream:
    def __init__(
        self,
        transport: Transport,
        endpoint: str,
        *,
        version: str = "4.2",
        timeout: float = 30.0,
    ):
        self.version = version
        self.timeout = timeout
```

Automatically generates TOML template from parameters.

---

## Middleware System

### Middleware Chain

```
Request
  ↓
┌─────────────────────┐
│ Retry Middleware    │ (exponential backoff)
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Circuit Breaker     │ (failure detection)
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Cache Middleware    │ (response caching)
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Metrics Middleware  │ (latency/errors)
└──────────┬──────────┘
           ↓
      Transport
           ↓
     Network
           ↓
        Response
```

### Middleware Responsibilities

| Middleware | Purpose | Example |
|------------|---------|----------|
| Retry | Handle transient failures | 3 attempts with exponential backoff |
| Circuit Breaker | Prevent cascading failures | Open circuit after 5 errors |
| Cache | Reduce redundant requests | Cache 5-minute responses |
| Metrics | Track performance | Latency, error rate, throughput |

---

## Error Handling

### Error Hierarchy

```python
class XspError(Exception):
    """Base exception for xsp-lib."""

class UpstreamError(XspError):
    """Upstream service error."""

class TransportError(XspError):
    """Transport layer error."""

class TimeoutError(TransportError):
    """Request timeout."""

class CircuitBreakerOpen(UpstreamError):
    """Circuit breaker is open."""
```

### Error Recovery

1. **Automatic Retry** - Transient errors trigger retry with backoff
2. **Circuit Breaker** - Stops retrying when upstream is unhealthy
3. **Fallback** - Route to secondary upstream if primary fails
4. **Graceful Degradation** - Return cached response if all fail

---

## Type Safety

### mypy --strict Compliance

All code passes `mypy --strict`:

```bash
mypy src/xsp --strict
```

### No Any Types

Except where explicitly needed:
- Generic type parameters
- Protocol implementations
- Middleware wrapping

### Type Hints for All

```python
def fetch(
    self,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> str:
    """Type hints on all parameters and return."""
```

---

## Integration Patterns

### Basic Usage

```python
from xsp.protocols.vast import VastUpstream
from xsp.transports.http import HttpTransport
from xsp.core.config import UpstreamConfig

# Create configuration
config = UpstreamConfig(
    endpoint="https://ads.example.com/vast",
    timeout=30.0,
)

# Create upstream
upstream = VastUpstream(
    transport=HttpTransport(),
    config=config,
)

# Fetch response
response = await upstream.fetch(params={"publisher": "pub123"})
```

### With Session Management

```python
import time
from xsp.core.session import SessionContext

# Create session context
context = SessionContext(
    timestamp=int(time.time() * 1000),
    correlator="session-123",
    cachebusting="rand-456",
    cookies={"uid": "user-789"},
    request_id="req-001",
)

# Create session
session = await upstream.create_session(context)

try:
    # Check frequency cap
    if await session.check_frequency_cap("user-789"):
        response = await session.request()
        await session.track_budget("campaign-1", 2.50)
finally:
    await session.close()
```

### With Middleware

```python
from xsp.middleware.retry import RetryMiddleware
from xsp.middleware.cache import CacheMiddleware

# Wrap transport with middleware
transport = HttpTransport()
transport = RetryMiddleware(transport, max_retries=3)
transport = CacheMiddleware(transport, ttl=300)

# Use with upstream
upstream = VastUpstream(
    transport=transport,
    config=config,
)
```

---

## Future Extensions

### Phase 2: Protocol Handlers
- OpenRTB 2.6 complete implementation
- Terminology standardization
- Type-safe request/response schemas

### Phase 3: Advanced Features
- VAST chain resolution with sessions
- StateBackend abstraction (Redis, DB)
- Orchestrator enhancements

### Phase 4: Production Features
- Frequency capping implementation
- Budget tracking implementation
- Performance optimization
- Production examples

---

## Summary

xsp-lib architecture emphasizes:

1. **Pluggability** - Swap components without changing logic
2. **Type Safety** - Catch errors at development time
3. **Composition** - Build complex behavior from simple pieces
4. **Immutability** - Safe concurrent access
5. **Explicitness** - No hidden behavior or global state

This foundation enables rapid addition of new protocols while maintaining quality and type safety.

---

**Next:** See [Session Management Guide](../guides/session-management.md) for stateful ad serving patterns.
