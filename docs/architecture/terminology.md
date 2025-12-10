# Terminology Guide

This document defines the precise terminology used throughout xsp-lib to describe operations at each architectural layer. Consistent terminology is critical for understanding code behavior and API design.

## Table of Contents

1. [Overview](#overview)
2. [Terminology Table](#terminology-table)
3. [Term Definitions](#term-definitions)
4. [Code Examples](#code-examples)
5. [Migration Guide](#migration-guide)

## Overview

xsp-lib uses specific verbs to describe operations at different architectural layers. Each term has a precise meaning and should be used consistently:

- **Transport Layer**: `dial()` - Establish connections
- **Upstream Layer**: `request()` - Exchange data
- **Protocol Layer**: `resolve()` - Handle protocol complexity
- **Orchestrator Layer**: `serve()` - Deliver ads to users

These terms align with industry standards and make code self-documenting.

## Terminology Table

| Term | Layer | Meaning | IAB/Industry Usage |
|------|-------|---------|-------------------|
| `dial()` | Transport | Establish network connection to endpoint | Common in gRPC, Go networking |
| `request()` | Upstream | Send request and receive response | HTTP terminology |
| `fetch()` | Upstream | **DEPRECATED** - Use `request()` instead | Legacy term, avoid in new code |
| `resolve()` | Protocol | Recursively resolve wrapper chains or complex protocol sequences | VAST wrapper resolution (VAST 4.2 §2.4.3.4) |
| `serve()` | Orchestrator | Deliver final ad to end user after waterfall/orchestration | Ad serving terminology |
| `track()` | Analytics | Record event (impression, click, etc.) | Standard analytics term |
| `validate()` | Schema | Check data against schema/spec | Schema validation |

### Deprecated Terms

| Deprecated Term | Replacement | Reason |
|----------------|-------------|---------|
| `fetch()` | `request()` | More precise - distinguishes from protocol resolution |
| `get()` | `request()` | Too generic - conflicts with dict/object access |
| `call()` | `request()` | Too generic - conflicts with function calling |

## Term Definitions

### `dial()` - Transport Layer

**Definition**: Establish a network connection to a remote endpoint.

**Etymology**: Borrowed from telecommunications (dial a phone number) and popularized by gRPC and Go's `net.Dial()`.

**Usage**:
- Opening TCP/HTTP connections
- Establishing WebSocket connections
- Connecting to gRPC services
- Mounting file systems

**Key Characteristics**:
- **Low-level operation**: Direct network I/O
- **No application logic**: Pure connection establishment
- **Returns connection handle**: Not response data
- **May fail**: Network errors, DNS failures, timeouts

**Example**:
```python
class HttpTransport:
    """HTTP transport implementation."""
    
    async def dial(self, endpoint: str) -> httpx.AsyncClient:
        """Dial HTTP endpoint and return client.
        
        Establishes persistent HTTP/2 connection if supported.
        
        Args:
            endpoint: Base URL to connect to
        
        Returns:
            Connected HTTP client
        
        Raises:
            TransportError: If connection fails
        """
        try:
            client = httpx.AsyncClient(base_url=endpoint)
            # Test connection
            await client.get("/health")
            return client
        except Exception as e:
            raise TransportError(f"Failed to dial {endpoint}: {e}")
```

**When to use `dial()`**:
- Implementing Transport protocol
- Managing connection pools
- Establishing long-lived connections
- Testing connectivity

### `request()` - Upstream Layer

**Definition**: Send a request to an upstream service and receive a response.

**Etymology**: Standard HTTP terminology - "HTTP request/response cycle".

**Usage**:
- Fetching data from REST APIs
- Calling RPC methods
- Querying databases
- Reading files

**Key Characteristics**:
- **Request/response pattern**: Send data, get data back
- **Application-level**: Includes params, headers, payload
- **Returns typed data**: Decoded response (not raw bytes)
- **Handles serialization**: Encode request, decode response

**Example**:
```python
class BaseUpstream(Generic[T]):
    """Base upstream implementation."""
    
    async def request(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        payload: Any = None,
        timeout: float | None = None,
    ) -> T:
        """Request data from upstream service.
        
        Sends request with params/headers/payload and returns
        decoded response of type T.
        
        Args:
            params: Query parameters
            headers: HTTP headers
            payload: Request body
            timeout: Request timeout in seconds
        
        Returns:
            Decoded response of type T
        
        Raises:
            UpstreamTimeout: If request times out
            TransportError: If network fails
            DecodeError: If response decoding fails
        """
        # Merge default params/headers
        merged_params = {**self.default_params, **(params or {})}
        merged_headers = {**self.default_headers, **(headers or {})}
        
        # Encode payload if provided
        encoded_payload = None
        if payload is not None:
            encoded_payload = self.encoder(payload)
        
        # Send via transport
        raw_response = await self.transport.send(
            endpoint=self.endpoint,
            payload=encoded_payload,
            metadata=merged_headers,
            timeout=timeout or self.default_timeout,
        )
        
        # Decode and return
        return self.decoder(raw_response)
```

**When to use `request()`**:
- Implementing Upstream protocol
- Fetching data from APIs
- Standard request/response patterns
- Non-protocol-specific operations

### `fetch()` - **DEPRECATED**

**Definition**: Legacy term for requesting data. **Use `request()` instead.**

**Deprecation Reason**: 
- Ambiguous - doesn't distinguish between simple requests and complex protocol operations
- Conflicts with JavaScript `fetch()` API semantics
- Not standard in HTTP/networking terminology

**Migration**:
```python
# ❌ Old (deprecated)
result = await upstream.fetch(params={"key": "value"})

# ✅ New (preferred)
result = await upstream.request(params={"key": "value"})
```

**Note**: Some existing code still uses `fetch()` for backward compatibility. New code should use `request()`.

### `resolve()` - Protocol Layer

**Definition**: Recursively resolve complex protocol sequences, especially VAST wrapper chains.

**Etymology**: DNS resolution (resolve domain to IP), VAST wrapper resolution.

**Usage**:
- VAST wrapper chain resolution (per VAST 4.2 §2.4.3.4)
- OpenRTB deal resolution
- Recursive data fetching
- Protocol state machines

**Key Characteristics**:
- **Recursive**: May involve multiple requests
- **Protocol-specific**: Understands protocol semantics
- **Stateful**: Tracks resolution depth, visited URLs
- **Terminal condition**: Stops at inline/final response

**Example**:
```python
class VastUpstream(BaseUpstream[str]):
    """VAST protocol upstream."""
    
    async def resolve(
        self,
        params: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        max_depth: int = 5,
    ) -> VastResponse:
        """Resolve VAST wrapper chain to final inline ad.
        
        Recursively follows VASTAdTagURI elements until reaching
        an InLine ad or hitting max_depth. Per VAST 4.2 §2.4.3.4.
        
        Args:
            params: Initial request parameters
            context: Macro substitution context
            max_depth: Maximum wrapper depth (default 5 per spec)
        
        Returns:
            Final VAST response with inline ad
        
        Raises:
            VastError: If max depth exceeded or invalid wrapper
            TransportError: If network request fails
        
        Example:
            >>> upstream = VastUpstream(...)
            >>> response = await upstream.resolve(
            ...     params={"w": "640", "h": "480"}
            ... )
            >>> assert response.is_inline  # Terminal condition
        """
        visited_urls: set[str] = set()
        current_url = self._build_url(params)
        
        for depth in range(max_depth):
            # Prevent infinite loops
            if current_url in visited_urls:
                raise VastError(f"Circular wrapper reference: {current_url}")
            visited_urls.add(current_url)
            
            # Request VAST XML
            xml = await self.request(endpoint=current_url)
            
            # Parse and check type
            vast = self._parse_vast(xml)
            
            if vast.is_inline:
                # Terminal condition - return final ad
                return vast
            
            if vast.is_wrapper:
                # Extract next URL and continue
                current_url = vast.wrapper.vast_ad_tag_uri
                
                # Substitute macros if context provided
                if context and self.macro_substitutor:
                    current_url = self.macro_substitutor.substitute(
                        current_url, context
                    )
            else:
                raise VastError("VAST response is neither Inline nor Wrapper")
        
        raise VastError(f"Max wrapper depth {max_depth} exceeded")
```

**When to use `resolve()`**:
- VAST wrapper resolution
- Recursive data fetching
- Protocol state machines
- Multi-step protocol flows

### `serve()` - Orchestrator Layer

**Definition**: Deliver final ad to end user after waterfall logic and orchestration.

**Etymology**: Standard ad serving terminology - "serve an ad impression".

**Usage**:
- Final ad delivery to client
- Waterfall orchestration result
- Multi-upstream coordination
- Business logic completion

**Key Characteristics**:
- **High-level operation**: End-to-end ad delivery
- **Orchestrates multiple upstreams**: Primary, fallback, analytics
- **Applies business logic**: Frequency capping, budget tracking
- **Returns final result**: Ready for client rendering

**Example**:
```python
class AdServerOrchestrator:
    """Ad server orchestrator coordinating multiple upstreams."""
    
    def __init__(
        self,
        primary_upstream: VastUpstream,
        fallback_upstream: VastUpstream,
        analytics: AnalyticsUpstream,
        frequency_capper: FrequencyCapper,
    ):
        self.primary = primary_upstream
        self.fallback = fallback_upstream
        self.analytics = analytics
        self.frequency_capper = frequency_capper
    
    async def serve(
        self,
        user_id: str,
        campaign_id: str,
        params: dict[str, Any],
    ) -> AdResponse:
        """Serve ad to user with waterfall logic.
        
        Coordinates multiple upstreams to deliver final ad:
        1. Check frequency cap
        2. Try primary upstream
        3. Fall back if primary fails
        4. Track impression
        5. Return final ad
        
        Args:
            user_id: User identifier
            campaign_id: Campaign identifier
            params: Ad request parameters
        
        Returns:
            Final ad response ready for rendering
        
        Raises:
            FrequencyCapExceeded: If user has seen too many ads
            NoAdAvailable: If both primary and fallback fail
        """
        # Check frequency cap
        can_serve = await self.frequency_capper.check_cap(user_id, campaign_id)
        if not can_serve:
            raise FrequencyCapExceeded(f"User {user_id} capped for {campaign_id}")
        
        ad_response = None
        
        try:
            # Try primary upstream
            vast_xml = await self.primary.resolve(params=params)
            ad_response = self._parse_to_ad_response(vast_xml)
        except Exception as e:
            logger.warning(f"Primary upstream failed: {e}")
            
            try:
                # Fallback upstream
                vast_xml = await self.fallback.resolve(params=params)
                ad_response = self._parse_to_ad_response(vast_xml)
                ad_response.metadata["source"] = "fallback"
            except Exception as fallback_error:
                logger.error(f"Fallback upstream failed: {fallback_error}")
                raise NoAdAvailable("Both primary and fallback failed")
        
        # Record impression
        await self.frequency_capper.record_impression(user_id, campaign_id)
        await self.analytics.track(
            event="impression",
            user_id=user_id,
            campaign_id=campaign_id,
            ad_id=ad_response.id,
        )
        
        return ad_response
```

**When to use `serve()`**:
- Implementing orchestrators
- Waterfall ad serving
- Multi-upstream coordination
- Final ad delivery to users

### `track()` - Analytics Layer

**Definition**: Record an event (impression, click, error) for analytics.

**Etymology**: Standard analytics terminology - "track an event".

**Usage**:
- Recording impressions
- Tracking clicks
- Logging errors
- Sending beacons

**Example**:
```python
class AnalyticsUpstream:
    """Analytics tracking upstream."""
    
    async def track(
        self,
        event: str,
        user_id: str | None = None,
        campaign_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Track analytics event.
        
        Args:
            event: Event type (impression, click, error)
            user_id: User identifier
            campaign_id: Campaign identifier
            metadata: Additional event metadata
        """
        payload = {
            "event": event,
            "timestamp": time.time(),
            "user_id": user_id,
            "campaign_id": campaign_id,
            **(metadata or {}),
        }
        
        await self.request(payload=payload)
```

### `validate()` - Schema Layer

**Definition**: Check data against schema or IAB specification.

**Etymology**: Standard validation terminology.

**Usage**:
- XML schema validation
- JSON schema validation
- IAB spec compliance checks
- Request/response validation

**Example**:
```python
def validate(xml: str, version: VastVersion) -> bool:
    """Validate VAST XML against schema.
    
    Args:
        xml: VAST XML string
        version: VAST version (2.0, 3.0, 4.0, 4.1, 4.2)
    
    Returns:
        True if valid
    
    Raises:
        ValidationError: If XML is invalid
    """
    schema = load_vast_schema(version)
    return schema.validate(xml)
```

## Code Examples

### Complete Example: All Terms

```python
"""Complete example demonstrating all terminology."""
import asyncio
from xsp.protocols.vast import VastUpstream
from xsp.transports.http import HttpTransport

async def complete_example() -> None:
    # Transport Layer: dial()
    transport = HttpTransport()
    # Internally calls dial() to establish connection pool
    
    # Upstream Layer: request()
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
    )
    
    # Simple request (no wrapper resolution)
    vast_xml = await upstream.request(
        params={"w": "640", "h": "480"}
    )
    
    # Protocol Layer: resolve()
    # Follows wrapper chain to terminal inline ad
    vast_response = await upstream.resolve(
        params={"w": "640", "h": "480"},
        context={"timestamp": "1234567890"},
        max_depth=5,
    )
    
    # Orchestrator Layer: serve()
    orchestrator = AdServerOrchestrator(
        primary_upstream=upstream,
        fallback_upstream=fallback_upstream,
        analytics=analytics_upstream,
        frequency_capper=frequency_capper,
    )
    
    ad_response = await orchestrator.serve(
        user_id="user_12345",
        campaign_id="camp_1",
        params={"w": "640", "h": "480"},
    )
    
    # Analytics: track()
    await analytics_upstream.track(
        event="impression",
        user_id="user_12345",
        campaign_id="camp_1",
        ad_id=ad_response.id,
    )

asyncio.run(complete_example())
```

### Layer-Specific Examples

#### Transport Layer

```python
class HttpTransport:
    """HTTP transport with explicit dial() method."""
    
    async def dial(self, endpoint: str) -> None:
        """Establish HTTP connection pool.
        
        Called once during initialization to set up persistent
        connections. Subsequent send() operations reuse connections.
        """
        self.client = httpx.AsyncClient(base_url=endpoint)
        # Warm up connection pool
        await self.client.get("/health")
    
    async def send(
        self,
        endpoint: str,
        payload: bytes | None = None,
        metadata: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> bytes:
        """Send request using established connection."""
        # Connection already dialed
        response = await self.client.request(...)
        return response.content
```

#### Upstream Layer

```python
class BaseUpstream(Generic[T]):
    """Base upstream with request() method."""
    
    async def request(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> T:
        """Request data from upstream.
        
        Standard request/response pattern. Use for simple
        operations without protocol-specific complexity.
        """
        # Merge params/headers
        # Send via transport
        # Decode response
        ...
```

#### Protocol Layer

```python
class VastUpstream(BaseUpstream[str]):
    """VAST protocol with resolve() method."""
    
    async def resolve(
        self,
        params: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        max_depth: int = 5,
    ) -> VastResponse:
        """Resolve VAST wrapper chain.
        
        Protocol-specific operation that may involve multiple
        request() calls to follow wrapper chain.
        """
        # Recursive wrapper resolution
        # Macro substitution
        # Depth limiting
        ...
```

#### Orchestrator Layer

```python
class AdServerOrchestrator:
    """Ad server orchestrator with serve() method."""
    
    async def serve(
        self,
        user_id: str,
        campaign_id: str,
        params: dict[str, Any],
    ) -> AdResponse:
        """Serve ad to user.
        
        High-level operation coordinating multiple upstreams,
        frequency capping, and analytics.
        """
        # Check frequency cap
        # Try primary upstream with resolve()
        # Fallback if needed
        # Track impression
        # Return final ad
        ...
```

## Migration Guide

### Migrating from `fetch()` to `request()`

#### Step 1: Identify Usage

```bash
# Find all fetch() usage
grep -r "\.fetch(" src/
```

#### Step 2: Update Method Calls

```python
# ❌ Before
result = await upstream.fetch(params={"key": "value"})

# ✅ After
result = await upstream.request(params={"key": "value"})
```

#### Step 3: Update Method Definitions

```python
# ❌ Before
class MyUpstream(BaseUpstream[str]):
    async def fetch(self, *, params: dict[str, Any] | None = None) -> str:
        return await super().fetch(params=params)

# ✅ After
class MyUpstream(BaseUpstream[str]):
    async def request(self, *, params: dict[str, Any] | None = None) -> str:
        return await super().request(params=params)
```

#### Step 4: Update Tests

```python
# ❌ Before
async def test_fetch():
    result = await upstream.fetch()
    assert result is not None

# ✅ After
async def test_request():
    result = await upstream.request()
    assert result is not None
```

### Backward Compatibility

For backward compatibility during migration, provide both methods:

```python
class BaseUpstream(Generic[T]):
    """Base upstream with both request() and fetch()."""
    
    async def request(
        self,
        *,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> T:
        """Request data from upstream (preferred)."""
        # Implementation
        ...
    
    async def fetch(
        self,
        *,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> T:
        """Fetch data from upstream.
        
        .. deprecated:: 1.0
            Use :meth:`request` instead.
        """
        import warnings
        warnings.warn(
            "fetch() is deprecated, use request() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return await self.request(params=params, **kwargs)
```

### Migration Checklist

- [ ] Search codebase for `fetch()` usage
- [ ] Update method calls from `fetch()` to `request()`
- [ ] Update method definitions in custom upstreams
- [ ] Update tests
- [ ] Update documentation
- [ ] Run full test suite
- [ ] Update type hints if needed
- [ ] Remove deprecated `fetch()` after grace period

## Best Practices

### 1. Use Correct Term for Layer

```python
# ✅ Good: Correct term for each layer
class HttpTransport:
    async def dial(self, endpoint: str) -> None:
        """Transport: dial connection."""
        ...

class BaseUpstream:
    async def request(self, **kwargs: Any) -> T:
        """Upstream: request data."""
        ...

class VastUpstream(BaseUpstream):
    async def resolve(self, **kwargs: Any) -> VastResponse:
        """Protocol: resolve wrapper chain."""
        ...

class Orchestrator:
    async def serve(self, **kwargs: Any) -> AdResponse:
        """Orchestrator: serve ad to user."""
        ...
```

### 2. Don't Mix Terms Across Layers

```python
# ❌ Bad: Using "serve" at transport layer
class HttpTransport:
    async def serve(self, endpoint: str) -> bytes:  # Wrong!
        ...

# ❌ Bad: Using "dial" at orchestrator layer
class Orchestrator:
    async def dial(self, user_id: str) -> AdResponse:  # Wrong!
        ...
```

### 3. Document Term Usage

```python
def resolve_vast_wrapper(xml: str, max_depth: int = 5) -> VastResponse:
    """Resolve VAST wrapper chain to inline ad.
    
    Uses recursive request() calls to follow VASTAdTagURI
    elements until reaching terminal InLine ad.
    
    Args:
        xml: Initial VAST XML (may be Wrapper)
        max_depth: Maximum resolution depth per VAST 4.2 §2.4.3.4
    
    Returns:
        Final VAST response with inline ad
    
    Note:
        This is a protocol-level resolve() operation, not a simple
        upstream request(). Use request() for single-fetch operations.
    """
    ...
```

## References

- [Final Architecture Documentation](./final-architecture.md)
- [Session Management](./session-management.md)
- [VAST 4.2 Specification §2.4.3.4 - Wrapper Resolution](https://iabtechlab.com/wp-content/uploads/2019/06/VAST_4.2_final_june26.pdf)
- [gRPC Connection Management](https://grpc.io/docs/guides/connection-management/)
- [HTTP/1.1 Specification - RFC 7231](https://tools.ietf.org/html/rfc7231)

---

**Document Version**: 1.0  
**Last Updated**: 2025-12-10  
**Status**: Production Ready
