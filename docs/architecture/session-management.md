# Session Management Architecture

This document describes the session management layer in xsp-lib, including `SessionContext` for request correlation and `UpstreamSession` for stateful ad serving.

## Overview

Session management enables:
- **Request Correlation** - Track requests across services with unique IDs
- **Cachebusting** - Prevent CDN/proxy caching with random values
- **Frequency Capping** - Limit ad impressions per user per time period
- **Budget Tracking** - Monitor campaign spend in real-time
- **Cookie Management** - Pass cookies for user identification

## Core Abstractions

### SessionContext (Immutable)

`SessionContext` is a frozen dataclass containing request metadata:

```python
from dataclasses import dataclass
from datetime import datetime
import uuid

@dataclass(frozen=True)
class SessionContext:
    """Immutable request context for session management.
    
    Used for:
    - VAST macro substitution (CACHEBUSTING, TIMESTAMP)
    - Request correlation across services
    - Cookie management for frequency capping
    - Analytics and debugging
    
    Example:
        >>> context = SessionContext.create()
        >>> context.correlator
        '550e8400-e29b-41d4-a716-446655440000'
        >>> context.timestamp
        1702224000000
    """
    
    timestamp: int  # Unix timestamp in milliseconds
    correlator: str  # UUID for request correlation
    cachebusting: str  # Random value for cache prevention
    cookies: dict[str, str]  # HTTP cookies
    request_id: str  # Unique request identifier
    
    @classmethod
    def create(
        cls,
        cookies: dict[str, str] | None = None,
    ) -> "SessionContext":
        """Create a new SessionContext with auto-generated values.
        
        Args:
            cookies: Optional HTTP cookies (default: empty dict)
        
        Returns:
            SessionContext with generated timestamp, correlator, etc.
        """
        now = datetime.utcnow()
        return cls(
            timestamp=int(now.timestamp() * 1000),
            correlator=str(uuid.uuid4()),
            cachebusting=str(uuid.uuid4()),
            cookies=cookies or {},
            request_id=f"req-{uuid.uuid4()}",
        )
```

**Key Design Decisions:**
- **Frozen dataclass** - Immutable to prevent accidental mutation
- **Timestamp in milliseconds** - Matches VAST macro format
- **UUID-based values** - Globally unique, collision-resistant
- **Factory method** - `create()` for convenient instantiation

### UpstreamSession (Protocol)

`UpstreamSession` is a protocol for stateful ad serving:

```python
from typing import Protocol, Any
from decimal import Decimal

class UpstreamSession(Protocol):
    """Protocol for stateful ad serving session.
    
    Provides:
    - Frequency capping (limit impressions per user)
    - Budget tracking (monitor campaign spend)
    - Session-aware requests (context propagation)
    
    Implementations must be thread-safe and async-compatible.
    
    Example:
        >>> session = RedisUpstreamSession(upstream=vast_upstream)
        >>> can_serve = await session.check_frequency_cap("user123", "campaign456")
        >>> if can_serve:
        ...     response = await session.request(context, params={...})
        ...     await session.track_budget("campaign456", Decimal("0.50"))
    """
    
    async def request(
        self,
        context: SessionContext,
        **kwargs: Any,
    ) -> Any:
        """Execute request with session state.
        
        Args:
            context: Request context (correlation, cachebusting, cookies)
            **kwargs: Additional parameters for upstream.fetch()
        
        Returns:
            Response from upstream service
        
        Raises:
            FrequencyCapExceeded: User exceeded frequency cap
            BudgetExceeded: Campaign budget exhausted
        """
        ...
    
    async def check_frequency_cap(
        self,
        user_id: str,
        campaign_id: str,
    ) -> bool:
        """Check if user has exceeded frequency cap.
        
        Args:
            user_id: User identifier (from cookies or device ID)
            campaign_id: Campaign identifier
        
        Returns:
            True if user can receive ad, False if cap exceeded
        """
        ...
    
    async def track_budget(
        self,
        campaign_id: str,
        cost: Decimal,
    ) -> bool:
        """Track campaign spend and check budget.
        
        Args:
            campaign_id: Campaign identifier
            cost: Cost of ad impression (CPM, CPC, etc.)
        
        Returns:
            True if budget sufficient, False if exhausted
        
        Raises:
            BudgetExceeded: Campaign budget exhausted
        """
        ...
```

**Key Design Decisions:**
- **Protocol-based** - Structural typing for flexibility
- **Async methods** - Compatible with async/await patterns
- **Decimal for money** - Precise financial calculations
- **Thread-safe contract** - Implementations must handle concurrency

## Session Lifecycle

### 1. Create SessionContext

```python
from xsp.core.session import SessionContext

# Auto-generate all values
context = SessionContext.create()

# With custom cookies
context = SessionContext.create(
    cookies={"user_id": "abc123", "session_id": "xyz789"}
)
```

### 2. Pass Context to Upstream

```python
from xsp.protocols.vast import VastUpstream

# Standard fetch (no session)
response = await vast_upstream.fetch(params={"placement_id": "123"})

# Session-aware fetch (with context)
response = await vast_upstream.fetch(
    params={"placement_id": "123"},
    context=context,
)
```

### 3. Session-Aware Request (Optional)

For stateful ad serving with frequency capping and budget tracking:

```python
from xsp.sessions import RedisUpstreamSession

# Create session wrapper
session = RedisUpstreamSession(
    upstream=vast_upstream,
    redis_client=redis_client,
)

# Check frequency cap
user_id = context.cookies.get("user_id", "anonymous")
can_serve = await session.check_frequency_cap(user_id, "campaign123")

if can_serve:
    # Execute request
    response = await session.request(
        context=context,
        params={"placement_id": "123"},
    )
    
    # Track budget
    await session.track_budget("campaign123", Decimal("0.50"))
```

## SessionContext vs UpstreamSession

### When to Use SessionContext

Use `SessionContext` when you need:
- ✅ Request correlation across services
- ✅ VAST macro substitution (CACHEBUSTING, TIMESTAMP)
- ✅ Cookie propagation
- ✅ Debugging and analytics
- ❌ **NO** stateful logic (frequency capping, budget tracking)

**Example:**
```python
context = SessionContext.create()
response = await vast_upstream.fetch(params=params, context=context)
logger.info("Request completed", extra={"request_id": context.request_id})
```

### When to Use UpstreamSession

Use `UpstreamSession` when you need:
- ✅ Frequency capping (limit impressions per user)
- ✅ Budget tracking (monitor campaign spend)
- ✅ Session state management (Redis, database)
- ✅ Cross-request coordination

**Example:**
```python
session = RedisUpstreamSession(upstream=vast_upstream, redis_client=redis)

# Check constraints before serving ad
can_serve = await session.check_frequency_cap(user_id, campaign_id)
budget_ok = await session.track_budget(campaign_id, cost)

if can_serve and budget_ok:
    response = await session.request(context, params=params)
```

## Implementation Patterns

### Stateless Upstream (SessionContext only)

```python
class VastUpstream(BaseUpstream[VastResponse]):
    """VAST upstream with macro substitution."""
    
    async def fetch(
        self,
        *,
        params: dict[str, Any] | None = None,
        context: SessionContext | None = None,
        **kwargs: Any,
    ) -> VastResponse:
        # Substitute VAST macros if context provided
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
                .replace("[CORRELATOR]", context.correlator)
            for k, v in params.items()
        }
```

### Stateful Session (UpstreamSession)

```python
from decimal import Decimal
from redis.asyncio import Redis

class RedisUpstreamSession:
    """Redis-backed session for frequency capping and budget tracking."""
    
    def __init__(
        self,
        upstream: Upstream[T],
        redis_client: Redis,
        frequency_cap: int = 3,  # Max impressions per user per campaign
        frequency_window: int = 3600,  # Time window in seconds (1 hour)
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
            return True  # No impressions yet
        
        return int(count) < self._frequency_cap
    
    async def track_budget(
        self,
        campaign_id: str,
        cost: Decimal,
    ) -> bool:
        """Track campaign spend and check budget."""
        key = f"budget:{campaign_id}"
        spent = await self._redis.get(key)
        
        if spent is None:
            spent = Decimal("0")
        else:
            spent = Decimal(spent)
        
        # Check if adding cost would exceed budget (assumed stored separately)
        budget = await self._get_campaign_budget(campaign_id)
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
        """Execute request with session state."""
        # Extract user_id from cookies
        user_id = context.cookies.get("user_id", "anonymous")
        
        # Extract campaign_id from params (simplified)
        campaign_id = kwargs.get("params", {}).get("campaign_id")
        
        # Check frequency cap
        if not await self.check_frequency_cap(user_id, campaign_id):
            raise FrequencyCapExceeded(user_id, campaign_id)
        
        # Execute upstream request
        response = await self._upstream.fetch(context=context, **kwargs)
        
        # Increment frequency cap counter
        key = f"freq:{user_id}:{campaign_id}"
        await self._redis.incr(key)
        await self._redis.expire(key, self._frequency_window)
        
        return response
    
    async def _get_campaign_budget(self, campaign_id: str) -> Decimal:
        """Fetch campaign budget from storage."""
        # Simplified: assumes budget stored in Redis
        budget = await self._redis.get(f"budget:limit:{campaign_id}")
        return Decimal(budget) if budget else Decimal("1000.00")
```

## Data Flow

### Request with SessionContext

```
Application
    ↓ creates SessionContext
    ↓ context = SessionContext.create(cookies={"user_id": "123"})
VastUpstream
    ↓ fetch(params=params, context=context)
    ↓ _substitute_macros(params, context)
    ↓   - [CACHEBUSTING] → context.cachebusting
    ↓   - [TIMESTAMP] → context.timestamp
    ↓   - [CORRELATOR] → context.correlator
BaseUpstream
    ↓ fetch(params=substituted_params)
Transport (HttpTransport)
    ↓ send(data, url, headers)
VAST Ad Server
    ↓ XML response
Transport
    ↓ bytes
BaseUpstream
    ↓ decoder(bytes) → VastResponse
VastUpstream
    ↓ returns VastResponse
Application
```

### Request with UpstreamSession

```
Application
    ↓ creates SessionContext
    ↓ context = SessionContext.create(cookies={"user_id": "123"})
RedisUpstreamSession
    ↓ check_frequency_cap(user_id="123", campaign_id="abc")
    ↓ Redis: GET freq:123:abc → 2 (under cap of 3)
    ↓ returns True
    ↓ request(context, params=params)
VastUpstream
    ↓ fetch(params=params, context=context)
    ↓ _substitute_macros(params, context)
BaseUpstream → Transport → VAST Ad Server → Response
RedisUpstreamSession
    ↓ Redis: INCR freq:123:abc → 3
    ↓ Redis: EXPIRE freq:123:abc 3600
    ↓ track_budget(campaign_id="abc", cost=Decimal("0.50"))
    ↓ Redis: INCRBYFLOAT budget:abc 0.50
    ↓ returns response
Application
```

## Error Handling

### SessionContext Errors

```python
try:
    context = SessionContext.create()
except Exception as e:
    logger.exception("Failed to create session context")
    # Fallback: use None (context is optional)
    context = None
```

### UpstreamSession Errors

```python
from xsp.core.exceptions import FrequencyCapExceeded, BudgetExceeded

try:
    response = await session.request(context, params=params)
except FrequencyCapExceeded as e:
    logger.warning("Frequency cap exceeded", extra={"user_id": e.user_id})
    # Return default ad or no-fill response
except BudgetExceeded as e:
    logger.warning("Budget exceeded", extra={"campaign_id": e.campaign_id})
    # Pause campaign or return default ad
except Exception as e:
    logger.exception("Session request failed")
    raise
```

## Testing

### Unit Tests for SessionContext

```python
import pytest
from xsp.core.session import SessionContext

def test_session_context_create():
    context = SessionContext.create()
    
    assert context.timestamp > 0
    assert context.correlator
    assert context.cachebusting
    assert context.request_id.startswith("req-")
    assert context.cookies == {}

def test_session_context_with_cookies():
    cookies = {"user_id": "123", "session_id": "abc"}
    context = SessionContext.create(cookies=cookies)
    
    assert context.cookies == cookies

def test_session_context_immutable():
    context = SessionContext.create()
    
    with pytest.raises(Exception):  # FrozenInstanceError
        context.timestamp = 999
```

### Unit Tests for UpstreamSession

```python
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from xsp.sessions import RedisUpstreamSession

@pytest.mark.asyncio
async def test_check_frequency_cap_under_limit():
    redis_mock = AsyncMock()
    redis_mock.get.return_value = "2"  # 2 impressions
    
    session = RedisUpstreamSession(
        upstream=AsyncMock(),
        redis_client=redis_mock,
        frequency_cap=3,
    )
    
    result = await session.check_frequency_cap("user123", "campaign456")
    assert result is True

@pytest.mark.asyncio
async def test_check_frequency_cap_exceeded():
    redis_mock = AsyncMock()
    redis_mock.get.return_value = "3"  # 3 impressions (cap is 3)
    
    session = RedisUpstreamSession(
        upstream=AsyncMock(),
        redis_client=redis_mock,
        frequency_cap=3,
    )
    
    result = await session.check_frequency_cap("user123", "campaign456")
    assert result is False

@pytest.mark.asyncio
async def test_track_budget():
    redis_mock = AsyncMock()
    redis_mock.get.side_effect = ["50.00", "1000.00"]  # spent, budget
    
    session = RedisUpstreamSession(
        upstream=AsyncMock(),
        redis_client=redis_mock,
    )
    
    result = await session.track_budget("campaign456", Decimal("10.00"))
    assert result is True
    redis_mock.incrbyfloat.assert_called_once_with("budget:campaign456", 10.00)
```

## Performance Considerations

### SessionContext

- **Cheap to create** - No I/O, just timestamp and UUID generation
- **Immutable** - Safe to share across threads/tasks
- **Small memory footprint** - ~200 bytes per instance

### UpstreamSession

- **Redis connection pooling** - Use async connection pool
- **TTL for frequency cap keys** - Auto-expire to prevent memory bloat
- **Pipeline operations** - Batch Redis commands for efficiency

Example:
```python
# Use Redis pipeline for atomic operations
async with self._redis.pipeline() as pipe:
    pipe.incr(freq_key)
    pipe.expire(freq_key, self._frequency_window)
    pipe.incrbyfloat(budget_key, float(cost))
    await pipe.execute()
```

## Best Practices

1. **Always use SessionContext for VAST macros** - Required for cachebusting
2. **Check frequency cap before budget** - Fail fast for blocked users
3. **Use Decimal for money** - Avoid floating-point precision issues
4. **Set TTL on Redis keys** - Prevent memory leaks
5. **Log request_id for debugging** - Enables request tracing
6. **Handle edge cases** - Anonymous users, missing cookies, etc.

## Migration from Legacy Code

### Before (no session)

```python
response = await vast_upstream.fetch(params={"placement_id": "123"})
```

### After (with SessionContext)

```python
context = SessionContext.create(cookies=request.cookies)
response = await vast_upstream.fetch(
    params={"placement_id": "123"},
    context=context,
)
logger.info("Request completed", extra={"request_id": context.request_id})
```

### After (with UpstreamSession)

```python
session = RedisUpstreamSession(upstream=vast_upstream, redis_client=redis)
context = SessionContext.create(cookies=request.cookies)

try:
    response = await session.request(context, params={"placement_id": "123"})
except FrequencyCapExceeded:
    response = get_default_ad()
```

## Related Documentation

- [Final Architecture](./final-architecture.md) - Complete system design
- [Terminology Guide](./terminology.md) - Correct terminology
- [Session Management Guide](../guides/session-management.md) - Practical examples
- [Stateful Ad Serving Guide](../guides/stateful-ad-serving.md) - Frequency capping examples
