# Terminology Guide

This document defines the correct terminology used throughout xsp-lib to ensure consistency with AdTech industry standards and avoid confusion.

## Core Operations

### ✅ Correct: `dial()`, `request()`, `resolve()`, `serve()`

### ❌ Incorrect: `fetch()` (deprecated in favor of specific terms)

The term "fetch" is **deprecated** in xsp-lib because it's ambiguous and doesn't clearly indicate what operation is being performed. Instead, we use precise, protocol-specific terminology:

---

## Terminology Matrix

| Term | Meaning | When to Use | Protocol Examples |
|------|---------|-------------|-------------------|
| **dial()** | Establish connection to upstream service | Opening connections, handshakes | gRPC dial, WebSocket connect |
| **request()** | Send request and receive response | Bidding, querying | OpenRTB bid request, VAST ad request |
| **resolve()** | Resolve wrapper/redirect to final resource | VAST Wrapper resolution, URL redirects | VAST Wrapper → Inline Ad |
| **serve()** | Deliver ad creative to end-user | Final ad delivery, impression tracking | Serving VAST ad to player |
| **fetch()** | **DEPRECATED** - Use specific terms above | **Avoid in new code** | Legacy BaseUpstream.fetch() |

---

## Detailed Definitions

### dial()

**Definition:** Establish a connection to an upstream service.

**Use Cases:**
- Opening HTTP/2 connection pool
- gRPC channel establishment
- WebSocket connection handshake
- TCP connection setup

**Example:**
```python
# gRPC upstream
await grpc_upstream.dial(endpoint="bidder.example.com:50051")

# WebSocket upstream
await ws_upstream.dial(url="wss://realtime.example.com/stream")
```

**Why not "connect"?** 
- "dial" is the standard term in gRPC and Go networking
- Emphasizes establishing a persistent channel, not a one-off request

---

### request()

**Definition:** Send a request to an upstream service and receive a response.

**Use Cases:**
- OpenRTB bid request
- VAST ad request (initial call)
- API queries
- HTTP POST/GET operations

**Example:**
```python
# OpenRTB bid request
bid_response = await openrtb_upstream.request(bid_request)

# VAST ad request
vast_response = await vast_upstream.request(
    params={"placement_id": "123"},
    context=session_context,
)
```

**Why not "fetch"?**
- "request" clearly indicates a request/response pattern
- Aligns with HTTP terminology (HTTP request → HTTP response)
- Distinguishes from passive operations like "resolve"

---

### resolve()

**Definition:** Resolve a wrapper, redirect, or indirect reference to the final resource.

**Use Cases:**
- VAST Wrapper → Inline Ad resolution
- URL redirects (HTTP 301/302)
- DNS resolution (rare in AdTech)
- Ad pod assembly from multiple wrappers

**Example:**
```python
# VAST Wrapper resolution
inline_ad = await vast_upstream.resolve(wrapper_response)

# Resolve VAST ad pod (multiple wrappers)
ad_pod = await vast_upstream.resolve_pod(wrapper_responses)

# URL redirect resolution
final_url = await http_upstream.resolve_redirects(
    initial_url="https://short.link/abc",
    max_redirects=5,
)
```

**Why not "fetch"?**
- "resolve" emphasizes the indirection (Wrapper → Inline)
- Standard terminology in VAST specification: "resolving wrappers"
- Distinguishes from the initial request operation

**VAST Wrapper Resolution (per IAB VAST 4.2 §2.4.1):**
```
Client requests ad → VAST Wrapper (contains VASTAdTagURI)
    ↓ resolve()
Client follows VASTAdTagURI → VAST Inline Ad (final creative)
```

---

### serve()

**Definition:** Deliver ad creative to the end-user and track impressions.

**Use Cases:**
- Serving VAST ad to video player
- Delivering banner creative
- Tracking impression pixels
- Initiating ad playback

**Example:**
```python
# Serve VAST ad to player
await vast_upstream.serve(
    ad=inline_ad,
    player="video_player_1",
    session_context=context,
)

# Serve banner ad
await display_upstream.serve(
    creative_url="https://cdn.example.com/banner.jpg",
    placement_id="sidebar_300x250",
)
```

**Why not "fetch"?**
- "serve" indicates final delivery to user, not upstream retrieval
- Aligns with "ad serving" industry terminology
- Emphasizes impression tracking and analytics

---

### fetch() (DEPRECATED)

**Definition:** Generic data retrieval operation (ambiguous).

**Why Deprecated:**
- **Ambiguous** - Doesn't indicate if it's a request, resolve, or serve
- **Overloaded** - Used for too many different operations
- **Not protocol-specific** - Doesn't align with industry terminology

**Migration Path:**
```python
# OLD (deprecated)
response = await upstream.fetch(params=params)

# NEW (request)
response = await upstream.request(params=params, context=context)

# NEW (resolve)
inline_ad = await upstream.resolve(wrapper_response)

# NEW (serve)
await upstream.serve(ad=ad, player=player_id)
```

**Backward Compatibility:**
- `BaseUpstream.fetch()` remains for compatibility
- Will be removed in v2.0.0
- All new protocols should implement `request()` instead

---

## Protocol-Specific Terminology

### VAST (Video Ad Serving Template)

| Operation | Term | IAB Spec Reference |
|-----------|------|--------------------|
| Initial ad request | `request()` | VAST 4.2 §2.1 |
| Wrapper → Inline | `resolve()` | VAST 4.2 §2.4.1 |
| Ad delivery to player | `serve()` | VAST 4.2 §3.0 |
| Impression tracking | `track_impression()` | VAST 4.2 §3.9 |

**Example:**
```python
# Request ad from VAST endpoint
vast_response = await vast_upstream.request(
    params={"app_id": "my_app", "placement_id": "preroll"},
    context=session_context,
)

# Check if it's a Wrapper
if vast_response.is_wrapper:
    # Resolve Wrapper → Inline
    inline_ad = await vast_upstream.resolve(vast_response)
else:
    inline_ad = vast_response

# Serve ad to player
await vast_upstream.serve(ad=inline_ad, player="main_player")
```

---

### OpenRTB (Open Real-Time Bidding)

| Operation | Term | OpenRTB Spec Reference |
|-----------|------|--------------------|
| Send bid request | `request()` | OpenRTB 2.6 §3.2.1 |
| Receive bid response | `request()` (returns response) | OpenRTB 2.6 §3.2.2 |
| Win notification | `notify_win()` | OpenRTB 2.6 §4.6 |

**Example:**
```python
# Send bid request
bid_response = await openrtb_upstream.request(
    bid_request=BidRequest(
        id="bid-123",
        imp=[Impression(id="imp-1", ...)]
    ),
    timeout=0.3,  # 300ms per OpenRTB 2.6 §4.1
)

# If bid wins, send win notification
if bid_response.seatbid:
    await openrtb_upstream.notify_win(
        bid_id=bid_response.seatbid[0].bid[0].id,
        price=Decimal("2.50"),
    )
```

---

### DAAST (Digital Audio Ad Serving Template)

**Note:** DAAST is **deprecated** as of VAST 4.1. Use VAST with `adType="audio"` instead.

| Operation | Term | Migration to VAST |
|-----------|------|-------------------|
| Audio ad request | `request()` | Use `VastUpstream.request(adType="audio")` |
| Audio wrapper resolution | `resolve()` | Use `VastUpstream.resolve()` |

**Migration Example:**
```python
# OLD (DAAST - deprecated)
daast_response = await daast_upstream.request(params=params)

# NEW (VAST 4.1+ with adType="audio")
vast_response = await vast_upstream.request(
    params={"placement_id": "audio_preroll", "adType": "audio"},
    context=session_context,
)
```

---

## Session Management Terminology

### SessionContext

**Definition:** Immutable request context containing correlation metadata.

**Fields:**
- `timestamp` - Unix timestamp in milliseconds
- `correlator` - UUID for request correlation
- `cachebusting` - Random value for cache prevention
- `cookies` - HTTP cookies
- `request_id` - Unique request identifier

**Usage:**
```python
from xsp.core.session import SessionContext

context = SessionContext.create(cookies={"user_id": "123"})
response = await upstream.request(params=params, context=context)
```

---

### UpstreamSession

**Definition:** Protocol for stateful ad serving with frequency capping and budget tracking.

**Methods:**
- `request()` - Execute request with session state
- `check_frequency_cap()` - Check user impression limits
- `track_budget()` - Monitor campaign spend

**Usage:**
```python
from xsp.sessions import RedisUpstreamSession

session = RedisUpstreamSession(upstream=vast_upstream, redis_client=redis)
can_serve = await session.check_frequency_cap(user_id, campaign_id)

if can_serve:
    response = await session.request(context, params=params)
    await session.track_budget(campaign_id, cost)
```

---

## Transport Terminology

### send()

**Definition:** Low-level I/O operation to send data over transport layer.

**Use Cases:**
- HTTP POST/GET
- gRPC unary call
- WebSocket message send
- File write

**Example:**
```python
# HTTP transport
response_bytes = await http_transport.send(
    data=request_bytes,
    url="https://api.example.com/endpoint",
    headers={"Content-Type": "application/json"},
)

# gRPC transport
response_bytes = await grpc_transport.send(
    data=protobuf_bytes,
    method="BidService.Bid",
)
```

**Why "send" not "fetch"?**
- "send" emphasizes the bidirectional nature (send request → receive response)
- Standard terminology in network programming

---

## Configuration Terminology

### UpstreamConfig

**Definition:** Transport-agnostic configuration for upstream services.

**Fields:**
- `timeout` - Request timeout in seconds
- `max_retries` - Maximum retry attempts
- `encoding` - Character encoding (e.g., "utf-8")
- `encoding_config` - Encoding-specific settings (e.g., Cyrillic preservation)
- `default_headers` - Default HTTP headers
- `default_params` - Default query parameters

**Example:**
```python
from xsp.core.config import UpstreamConfig

config = UpstreamConfig(
    timeout=30.0,
    encoding="utf-8",
    encoding_config={"preserve_cyrillic": True},
    default_headers={"X-API-Key": "secret"},
)

upstream = VastUpstream(transport=http_transport, config=config)
```

---

## Error Terminology

### Exception Hierarchy

```python
XspError                    # Base exception
├── TransportError          # Network, I/O errors
├── ProtocolError           # Protocol parsing, validation errors
├── UpstreamError           # Upstream service errors (HTTP 4xx/5xx)
├── TimeoutError            # Request timeout
├── CircuitBreakerOpen      # Circuit breaker triggered
├── FrequencyCapExceeded    # User exceeded impression limit
└── BudgetExceeded          # Campaign budget exhausted
```

**Usage:**
```python
from xsp.core.exceptions import TimeoutError, FrequencyCapExceeded

try:
    response = await session.request(context, params=params)
except TimeoutError:
    logger.warning("Request timeout", extra={"timeout": config.timeout})
    response = get_default_ad()
except FrequencyCapExceeded as e:
    logger.info("Frequency cap hit", extra={"user_id": e.user_id})
    response = None
```

---

## Middleware Terminology

### wrap()

**Definition:** Wrap an upstream with middleware for cross-cutting concerns.

**Example:**
```python
from xsp.middleware import RetryMiddleware, CircuitBreakerMiddleware

# Wrap with retry middleware
retry_upstream = RetryMiddleware(
    upstream=vast_upstream,
    max_retries=3,
    backoff_factor=2.0,
)

# Wrap with circuit breaker
protected_upstream = CircuitBreakerMiddleware(
    upstream=retry_upstream,
    failure_threshold=5,
    recovery_timeout=60.0,
)
```

**Why "wrap" not "decorate"?**
- "wrap" is standard middleware terminology
- Emphasizes composition over inheritance

---

## Common Mistakes

### ❌ Incorrect

```python
# Using "fetch" ambiguously
response = await upstream.fetch(params=params)  # What operation is this?

# Using "get" for bidding
bid = await openrtb_upstream.get(bid_request)  # Sounds like HTTP GET

# Using "call" generically
result = await upstream.call(data)  # Too vague
```

### ✅ Correct

```python
# Specific operation names
response = await upstream.request(params=params, context=context)
inline_ad = await upstream.resolve(wrapper_response)
await upstream.serve(ad=ad, player=player_id)

# OpenRTB bidding
bid_response = await openrtb_upstream.request(bid_request, timeout=0.3)

# Clear intent
result = await upstream.request(params=params)
```

---

## Glossary

| Term | Definition | Example |
|------|------------|---------|
| **Upstream** | External AdTech service (VAST server, RTB bidder, etc.) | `VastUpstream`, `OpenRtbUpstream` |
| **Transport** | I/O layer abstraction (HTTP, gRPC, file, etc.) | `HttpTransport`, `MemoryTransport` |
| **Middleware** | Cross-cutting concern wrapper (retry, cache, etc.) | `RetryMiddleware`, `CircuitBreakerMiddleware` |
| **SessionContext** | Immutable request metadata | `SessionContext.create()` |
| **UpstreamSession** | Stateful ad serving session | `RedisUpstreamSession` |
| **UpstreamConfig** | Transport-agnostic configuration | `UpstreamConfig(timeout=30.0)` |
| **Cachebusting** | Random value to prevent caching | `[CACHEBUSTING]` VAST macro |
| **Correlator** | UUID for request correlation | `SessionContext.correlator` |
| **Frequency Cap** | Max impressions per user per campaign | `check_frequency_cap(user_id, campaign_id)` |
| **Budget Tracking** | Monitor campaign spend | `track_budget(campaign_id, cost)` |
| **VAST Wrapper** | Indirect ad reference requiring resolution | `resolve(wrapper_response)` |
| **VAST Inline** | Final ad creative with media files | Result of `resolve()` |
| **OpenRTB Bid Request** | RTB auction request | `request(bid_request)` |
| **OpenRTB Bid Response** | RTB auction response | Result of `request()` |

---

## Migration Checklist

When updating code to use correct terminology:

- [ ] Replace `fetch()` with `request()`, `resolve()`, or `serve()`
- [ ] Use `SessionContext` for VAST macro substitution
- [ ] Use `UpstreamSession` for frequency capping
- [ ] Use `UpstreamConfig` instead of per-protocol configs
- [ ] Update error handling to use specific exception types
- [ ] Replace `connect()` with `dial()` for persistent connections
- [ ] Document which IAB spec section each operation implements

---

## References

- [IAB VAST 4.2 Specification](https://iabtechlab.com/standards/vast/) - §2.4.1 (Wrapper resolution)
- [IAB OpenRTB 2.6 Specification](https://iabtechlab.com/standards/openrtb/) - §3.2 (Bid request/response)
- [IAB DAAST Deprecation Notice](https://iabtechlab.com/standards/daast/) - Use VAST 4.1+ adType="audio"
- [Python Naming Conventions](https://peps.python.org/pep-0008/) - PEP 8
- [gRPC Terminology](https://grpc.io/docs/what-is-grpc/core-concepts/) - dial, unary call

---

## Related Documentation

- [Final Architecture](./final-architecture.md) - Complete system design
- [Session Management](./session-management.md) - SessionContext and UpstreamSession
- [Protocol-Agnostic Design](./protocol-agnostic-design.md) - TypedDict schemas
