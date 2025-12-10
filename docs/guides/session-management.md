# Session Management Guide

This guide provides practical examples for using session management features in xsp-lib, including `SessionContext` for request correlation and `UpstreamSession` for stateful ad serving.

## Table of Contents

- [Quick Start](#quick-start)
- [SessionContext Basics](#sessioncontext-basics)
- [VAST Macro Substitution](#vast-macro-substitution)
- [Request Correlation](#request-correlation)
- [Cookie Management](#cookie-management)
- [Stateful Ad Serving](#stateful-ad-serving)
- [Advanced Patterns](#advanced-patterns)
- [Best Practices](#best-practices)

## Quick Start

### Basic SessionContext Usage

```python
from xsp.core.session import SessionContext
from xsp.protocols.vast import VastUpstream
from xsp.transports.http import HttpTransport

# Create session context
context = SessionContext.create()

# Create upstream
transport = HttpTransport()
upstream = VastUpstream(transport=transport)

# Make request with session context
response = await upstream.fetch(
    params={"placement_id": "preroll_video"},
    context=context,
)

print(f"Request ID: {context.request_id}")
print(f"Timestamp: {context.timestamp}")
```

## SessionContext Basics

### Creating a SessionContext

`SessionContext.create()` generates all required values automatically:

```python
from xsp.core.session import SessionContext

# Auto-generate all values
context = SessionContext.create()

# Inspect generated values
print(f"Timestamp (ms): {context.timestamp}")
print(f"Correlator: {context.correlator}")
print(f"Cachebusting: {context.cachebusting}")
print(f"Request ID: {context.request_id}")
print(f"Cookies: {context.cookies}")
```

**Output:**
```
Timestamp (ms): 1702224000000
Correlator: 550e8400-e29b-41d4-a716-446655440000
Cachebusting: 6ba7b810-9dad-11d1-80b4-00c04fd430c8
Request ID: req-a1b2c3d4-e5f6-7890-abcd-ef1234567890
Cookies: {}
```

### Adding Cookies

Pass cookies from HTTP requests:

```python
# From web framework (Flask, FastAPI, etc.)
def handle_ad_request(request):
    context = SessionContext.create(
        cookies={"user_id": request.cookies.get("user_id", "anonymous")}
    )
    
    response = await vast_upstream.fetch(
        params={"placement_id": "banner_300x250"},
        context=context,
    )
    
    return response
```

### Immutability

`SessionContext` is frozen (immutable):

```python
context = SessionContext.create()

# This will raise an error
try:
    context.timestamp = 999
except Exception as e:
    print(f"Error: {e}")  # FrozenInstanceError
```

**Why immutable?**
- Thread-safe (can share across async tasks)
- Prevents accidental modification
- Ensures consistent correlation values

## VAST Macro Substitution

VAST macros are automatically substituted when using `SessionContext`:

### Example: Cachebusting

```python
from xsp.core.session import SessionContext
from xsp.protocols.vast import VastUpstream

context = SessionContext.create()

# VAST URL with macro
vast_url = "https://ads.example.com/vast?cb=[CACHEBUSTING]&t=[TIMESTAMP]"

response = await vast_upstream.fetch(
    params={"ad_url": vast_url},
    context=context,
)

# Macros are substituted:
# [CACHEBUSTING] → context.cachebusting
# [TIMESTAMP] → context.timestamp
```

### Supported VAST Macros (per IAB VAST 4.2 §4.1)

| Macro | SessionContext Field | Example Value |
|-------|----------------------|---------------|
| `[CACHEBUSTING]` | `context.cachebusting` | `6ba7b810-9dad-11d1-80b4-00c04fd430c8` |
| `[TIMESTAMP]` | `context.timestamp` | `1702224000000` |
| `[CORRELATOR]` | `context.correlator` | `550e8400-e29b-41d4-a716-446655440000` |

### Custom Macro Substitution

For additional macros (device ID, IP address, etc.):

```python
def substitute_custom_macros(url: str, context: SessionContext, device_id: str) -> str:
    """Substitute VAST macros plus custom macros."""
    return (
        url
        .replace("[CACHEBUSTING]", context.cachebusting)
        .replace("[TIMESTAMP]", str(context.timestamp))
        .replace("[CORRELATOR]", context.correlator)
        .replace("[DEVICEID]", device_id)
    )

# Usage
vast_url = "https://ads.example.com/vast?device=[DEVICEID]&cb=[CACHEBUSTING]"
substituted_url = substitute_custom_macros(vast_url, context, "device-12345")
```

## Request Correlation

Use `request_id` and `correlator` for distributed tracing:

### Example: Logging Request IDs

```python
import logging
from xsp.core.session import SessionContext

logger = logging.getLogger(__name__)

async def serve_ad(placement_id: str):
    context = SessionContext.create()
    
    logger.info(
        "Ad request started",
        extra={
            "request_id": context.request_id,
            "correlator": context.correlator,
            "placement_id": placement_id,
        }
    )
    
    try:
        response = await vast_upstream.fetch(
            params={"placement_id": placement_id},
            context=context,
        )
        
        logger.info(
            "Ad request succeeded",
            extra={"request_id": context.request_id, "ad_id": response.ad.id}
        )
        
        return response
    except Exception as e:
        logger.error(
            "Ad request failed",
            extra={"request_id": context.request_id},
            exc_info=True,
        )
        raise
```

### Cross-Service Correlation

Pass `correlator` to downstream services:

```python
async def fetch_ad_with_analytics(placement_id: str):
    context = SessionContext.create()
    
    # Fetch ad
    ad_response = await vast_upstream.fetch(
        params={"placement_id": placement_id},
        context=context,
    )
    
    # Track analytics with same correlator
    await analytics_client.track_impression(
        ad_id=ad_response.ad.id,
        correlator=context.correlator,  # Same correlation ID
        timestamp=context.timestamp,
    )
    
    return ad_response
```

## Cookie Management

### User Identification

Extract user ID from cookies:

```python
from xsp.core.session import SessionContext

def create_session_from_request(http_request):
    """Create SessionContext from HTTP request."""
    cookies = {
        "user_id": http_request.cookies.get("user_id", "anonymous"),
        "session_id": http_request.cookies.get("session_id", ""),
    }
    
    return SessionContext.create(cookies=cookies)

# Usage in web endpoint
async def ad_endpoint(request):
    context = create_session_from_request(request)
    
    user_id = context.cookies.get("user_id", "anonymous")
    logger.info(f"Serving ad for user: {user_id}")
    
    response = await vast_upstream.fetch(
        params={"placement_id": "sidebar"},
        context=context,
    )
    
    return response
```

### GDPR/Privacy Compliance

Handle consent and privacy flags:

```python
def create_privacy_aware_context(http_request):
    """Create SessionContext with privacy compliance."""
    cookies = {}
    
    # Only track if consent given
    if http_request.cookies.get("gdpr_consent") == "1":
        cookies["user_id"] = http_request.cookies.get("user_id", "anonymous")
    else:
        cookies["user_id"] = "anonymous"  # Don't track
    
    return SessionContext.create(cookies=cookies)
```

## Stateful Ad Serving

For frequency capping and budget tracking, use `UpstreamSession`:

### Basic UpstreamSession Implementation

```python
from decimal import Decimal
from typing import Any
from xsp.core.session import SessionContext, UpstreamSession
from xsp.core.upstream import Upstream
from redis.asyncio import Redis

class RedisUpstreamSession:
    """Redis-backed session for frequency capping and budget tracking."""
    
    def __init__(
        self,
        upstream: Upstream,
        redis_client: Redis,
        frequency_cap: int = 3,  # Max impressions per user per campaign
        frequency_window: int = 3600,  # Time window in seconds
    ):
        self._upstream = upstream
        self._redis = redis_client
        self._frequency_cap = frequency_cap
        self._frequency_window = frequency_window
    
    async def check_frequency_cap(
        self,
        user_id: str,
        campaign_id: str,
    ) -> bool:
        """Check if user has exceeded frequency cap."""
        key = f"freq:{user_id}:{campaign_id}"
        count = await self._redis.get(key)
        
        if count is None:
            return True
        
        return int(count) < self._frequency_cap
    
    async def track_budget(
        self,
        campaign_id: str,
        cost: Decimal,
    ) -> bool:
        """Track campaign spend."""
        key = f"budget:{campaign_id}"
        
        # Check budget
        budget = Decimal(await self._redis.get(f"budget:limit:{campaign_id}") or "1000")
        spent = Decimal(await self._redis.get(key) or "0")
        
        if spent + cost > budget:
            return False
        
        # Increment spend
        await self._redis.incrbyfloat(key, float(cost))
        return True
    
    async def request(
        self,
        context: SessionContext,
        **kwargs: Any,
    ) -> Any:
        """Execute request with frequency cap enforcement."""
        user_id = context.cookies.get("user_id", "anonymous")
        campaign_id = kwargs.get("params", {}).get("campaign_id", "default")
        
        # Check frequency cap
        if not await self.check_frequency_cap(user_id, campaign_id):
            raise FrequencyCapExceeded(user_id, campaign_id)
        
        # Execute upstream request
        response = await self._upstream.fetch(context=context, **kwargs)
        
        # Increment frequency counter
        key = f"freq:{user_id}:{campaign_id}"
        await self._redis.incr(key)
        await self._redis.expire(key, self._frequency_window)
        
        return response
```

### Using UpstreamSession

```python
from redis.asyncio import Redis
from xsp.core.session import SessionContext

# Initialize Redis client
redis = Redis(host="localhost", port=6379)

# Create session-aware upstream
session = RedisUpstreamSession(
    upstream=vast_upstream,
    redis_client=redis,
    frequency_cap=3,  # Max 3 impressions per hour
    frequency_window=3600,
)

# Serve ad with frequency capping
async def serve_ad_with_cap(placement_id: str, user_cookies: dict):
    context = SessionContext.create(cookies=user_cookies)
    user_id = context.cookies.get("user_id", "anonymous")
    
    # Check frequency cap before serving
    can_serve = await session.check_frequency_cap(user_id, "campaign123")
    
    if not can_serve:
        logger.info(f"Frequency cap exceeded for user {user_id}")
        return None  # Return default ad or no-fill
    
    # Serve ad and track
    response = await session.request(
        context=context,
        params={"placement_id": placement_id, "campaign_id": "campaign123"},
    )
    
    return response
```

## Advanced Patterns

### Middleware Integration

Combine SessionContext with middleware:

```python
from xsp.middleware.retry import RetryMiddleware
from xsp.core.session import SessionContext

# Wrap upstream with retry middleware
retry_upstream = RetryMiddleware(
    upstream=vast_upstream,
    max_retries=3,
)

# Use with SessionContext
context = SessionContext.create()
response = await retry_upstream.fetch(
    params={"placement_id": "video_preroll"},
    context=context,
)
```

### Multiple Upstreams

Correlate requests across multiple upstreams:

```python
async def fetch_multi_format_ad(context: SessionContext):
    """Fetch video and display ads with same correlator."""
    
    # Video ad request
    video_response = await vast_upstream.fetch(
        params={"format": "video"},
        context=context,
    )
    
    # Display ad request (same correlator)
    display_response = await display_upstream.fetch(
        params={"format": "banner"},
        context=context,
    )
    
    logger.info(
        "Multi-format ad request completed",
        extra={"correlator": context.correlator}
    )
    
    return {
        "video": video_response,
        "display": display_response,
    }
```

### Session Context Propagation

Pass context through application layers:

```python
class AdServer:
    """Ad server with session propagation."""
    
    def __init__(self, vast_upstream, analytics_client):
        self.vast_upstream = vast_upstream
        self.analytics = analytics_client
    
    async def serve_ad(self, context: SessionContext, placement_id: str):
        """Serve ad with full session tracking."""
        
        # Fetch ad
        response = await self.vast_upstream.fetch(
            params={"placement_id": placement_id},
            context=context,
        )
        
        # Track impression
        await self.analytics.track_impression(
            ad_id=response.ad.id,
            request_id=context.request_id,
            correlator=context.correlator,
            timestamp=context.timestamp,
        )
        
        # Track user interaction
        await self.track_user_interaction(context, response.ad.id)
        
        return response
    
    async def track_user_interaction(
        self,
        context: SessionContext,
        ad_id: str,
    ):
        """Track user interaction with session context."""
        user_id = context.cookies.get("user_id", "anonymous")
        
        await self.analytics.track_event(
            event_type="ad_served",
            ad_id=ad_id,
            user_id=user_id,
            correlator=context.correlator,
        )
```

## Best Practices

### 1. Always Create Fresh Context Per Request

```python
# ✅ Good: Fresh context per request
async def handle_request():
    context = SessionContext.create()
    return await upstream.fetch(context=context)

# ❌ Bad: Reusing context across requests
context = SessionContext.create()  # Don't do this globally

async def handle_request():
    return await upstream.fetch(context=context)  # Stale correlator!
```

### 2. Log Request IDs for Debugging

```python
import logging

logger = logging.getLogger(__name__)

async def fetch_with_logging(params: dict):
    context = SessionContext.create()
    
    logger.info(
        "Starting ad request",
        extra={"request_id": context.request_id, "params": params}
    )
    
    try:
        response = await upstream.fetch(params=params, context=context)
        logger.info("Request succeeded", extra={"request_id": context.request_id})
        return response
    except Exception as e:
        logger.error(
            "Request failed",
            extra={"request_id": context.request_id},
            exc_info=True,
        )
        raise
```

### 3. Handle Anonymous Users

```python
def get_user_id_from_cookies(cookies: dict) -> str:
    """Extract user ID with fallback to anonymous."""
    return cookies.get("user_id", "anonymous")

context = SessionContext.create(cookies=request.cookies)
user_id = get_user_id_from_cookies(context.cookies)

# Use user_id for frequency capping
can_serve = await session.check_frequency_cap(user_id, campaign_id)
```

### 4. Set TTL on Redis Keys

```python
# Set expiration on frequency cap keys
key = f"freq:{user_id}:{campaign_id}"
await redis.incr(key)
await redis.expire(key, 3600)  # 1 hour TTL
```

### 5. Use Decimal for Money

```python
from decimal import Decimal

# ✅ Good: Use Decimal for currency
cost = Decimal("2.50")
await session.track_budget(campaign_id, cost)

# ❌ Bad: Use float (precision issues)
cost = 2.50  # Don't use float for money!
```

## Related Documentation

- [Session Management Architecture](../architecture/session-management.md)
- [Stateful Ad Serving Guide](./stateful-ad-serving.md)
- [Final Architecture](../architecture/final-architecture.md)
- [Terminology Guide](../architecture/terminology.md)
