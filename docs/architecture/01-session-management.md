# Session Management Architecture

**Version:** 1.0  
**Date:** December 10, 2025  
**Related:** [Final Architecture](00-final-architecture.md)  

## Overview

Sessions enable stateful ad serving workflows with:

- **SessionContext** - Immutable session identification and state
- **UpstreamSession** - Stateful operations (requests, frequency capping, budget tracking)
- **StateBackend** - Persistence layer for session state
- **Integrated Error Recovery** - Automatic recovery with fallbacks

---

## SessionContext: Immutable State

### Purpose

SessionContext carries immutable session metadata throughout the request chain:

```python
@dataclass(frozen=True)
class SessionContext:
    timestamp: int              # Unix milliseconds for [TIMESTAMP] macro
    correlator: str             # Unique ID for tracking across wrapper chain
    cachebusting: str           # Random value for [CACHEBUSTING] macro
    cookies: dict[str, str]     # HTTP cookies to preserve across requests
    request_id: str             # Request tracing ID for logging
```

### Why Immutable?

1. **Thread Safety** - Safe to share across concurrent wrappers
2. **Predictability** - No accidental mutation during processing
3. **Debugging** - Easy to log and trace complete session state
4. **Caching** - Can be used as hashable dictionary keys

### Creation

```python
import time

context = SessionContext(
    timestamp=int(time.time() * 1000),
    correlator="session-abc123",          # Unique per user/device
    cachebusting=str(random.randint(0, 999999999)),
    cookies={"uid": "user123", "session": "xyz"},
    request_id="req-001"                  # For logging
)
```

### Macro Substitution

VAST macros are substituted from session context:

```xml
<!-- Original URL with macros -->
<MediaFile>
  <![CDATA[https://ads.example.com/track?
    timestamp=[TIMESTAMP]
    &correlator=[CORRELATOR]
    &cachebusting=[CACHEBUSTING]
  ]]>
</MediaFile>

<!-- After substitution -->
<MediaFile>
  <![CDATA[https://ads.example.com/track?
    timestamp=1702275840000
    &correlator=session-abc123
    &cachebusting=456789
  ]]>
</MediaFile>
```

---

## UpstreamSession: Stateful Operations

### Protocol Definition

```python
class UpstreamSession(Protocol):
    @property
    def context(self) -> SessionContext:
        """Get immutable session context."""
    
    async def request(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        """Send request within session context."""
    
    async def check_frequency_cap(
        self,
        user_id: str,
        limit: int | None = None,
    ) -> bool:
        """Check if user exceeded frequency cap."""
    
    async def track_budget(
        self,
        campaign_id: str,
        amount: float,
    ) -> None:
        """Track budget spend for campaign."""
    
    async def close(self) -> None:
        """Release session resources."""
```

### Session Lifecycle

```
1. CREATE SESSION
   UpstreamSession created with immutable context
   StateBackend initialized
   
2. OPERATE
   check_frequency_cap() - Read from StateBackend
   request() - Send within session context
   track_budget() - Write to StateBackend
   
3. CLOSE
   Flush pending state changes
   Release resources
   Log session metrics
```

### Implementation Pattern

```python
class VastSession:
    def __init__(
        self,
        context: SessionContext,
        upstream: VastUpstream,
        state_backend: StateBackend,
    ):
        self._context = context
        self._upstream = upstream
        self._state_backend = state_backend
    
    @property
    def context(self) -> SessionContext:
        return self._context
    
    async def request(self, *, params: dict | None = None) -> str:
        # Merge session context with request params
        merged_params = {**params or {}}
        merged_params["correlator"] = self._context.correlator
        merged_params["timestamp"] = self._context.timestamp
        
        # Send request
        response = await self._upstream.fetch(params=merged_params)
        return response
    
    async def check_frequency_cap(self, user_id: str, limit: int | None = None) -> bool:
        limit = limit or 3  # Default: 3 ads per user
        count = await self._state_backend.get_count(user_id)
        return count < limit
    
    async def track_budget(self, campaign_id: str, amount: float) -> None:
        await self._state_backend.add_spend(campaign_id, amount)
    
    async def close(self) -> None:
        # Flush any pending writes
        await self._state_backend.flush()
```

---

## Frequency Capping

### Use Case

Limit the number of ads shown to a user per time window:

```
User123: Ad1 ✓
User123: Ad2 ✓
User123: Ad3 ✓
User123: Ad4 ✗ (Cap reached: 3 ads per hour)
```

### Implementation

```python
async def serve_ad(user_id: str) -> Optional[str]:
    context = SessionContext(
        timestamp=int(time.time() * 1000),
        correlator=f"session-{user_id}",
        cachebusting=str(random.randint(0, 999999999)),
        cookies={"uid": user_id},
        request_id=generate_request_id(),
    )
    
    session = await upstream.create_session(context)
    
    try:
        # Check frequency cap
        if await session.check_frequency_cap(user_id, limit=3):
            # User hasn't hit cap
            ad = await session.request(params={"slot": "pre-roll"})
            
            # Track spend
            cpm = 2.50
            await session.track_budget("campaign-456", cpm)
            
            return ad
        else:
            # User hit cap, try fallback
            return await fallback_upstream.fetch()
    
    finally:
        await session.close()
```

### StateBackend Methods

```python
# Check count
count = await state_backend.get_count(f"freq_cap:{user_id}:hour")
if count >= 3:
    return False  # Cap exceeded

# Increment count
await state_backend.increment(f"freq_cap:{user_id}:hour")
await state_backend.set_expiry(f"freq_cap:{user_id}:hour", 3600)  # 1 hour
```

---

## Budget Tracking

### Use Case

Track total spend per campaign:

```
Campaign-1: $0.00 (start)
Campaign-1: Ad served (CPM $2.50) -> $2.50
Campaign-1: Ad served (CPM $3.00) -> $5.50
Campaign-1: Budget limit $10.00 -> Can serve 2 more ads
```

### Implementation

```python
async def serve_with_budget_check(
    campaign_id: str,
    campaign_budget: float,
) -> Optional[str]:
    session = await upstream.create_session(context)
    
    try:
        # Get current spend
        current_spend = await session.get_budget(campaign_id)
        remaining = campaign_budget - current_spend
        
        if remaining <= 0:
            return None  # Budget exhausted
        
        # Estimate CPM
        estimated_cpm = 2.50
        
        if remaining >= estimated_cpm:
            # Budget available, serve ad
            ad = await session.request()
            
            # Track actual spend
            await session.track_budget(campaign_id, estimated_cpm)
            
            return ad
        else:
            # Budget nearly exhausted
            return None
    
    finally:
        await session.close()
```

### StateBackend Methods

```python
# Get spend
spend = await state_backend.get_spend(f"budget:{campaign_id}")

# Add spend
await state_backend.add_spend(f"budget:{campaign_id}", 2.50)

# Get remaining (compute)
remaining = budget_limit - await state_backend.get_spend(...)
```

---

## VAST Chain Resolution with Sessions

### Problem

VAST wrappers create chain of requests:

```
1. Request wrapper1
   ├── Get redirect to wrapper2
2. Request wrapper2
   ├── Get redirect to wrapper3
3. Request wrapper3
   ├── Get redirect to inline (final)
4. Request inline
   ├── Get actual ad content
```

Each request must maintain session context.

### Solution: VastChainResolver

```python
class VastChainResolver:
    def __init__(
        self,
        upstream: VastUpstream,
        state_backend: StateBackend,
    ):
        self._upstream = upstream
        self._state_backend = state_backend
    
    async def resolve(self, *, params: dict | None = None) -> str:
        # Create session for entire chain
        context = SessionContext(
            timestamp=int(time.time() * 1000),
            correlator=str(uuid4()),
            cachebusting=str(random.randint(0, 999999999)),
            cookies={},
            request_id=f"req-{uuid4().hex[:8]}",
        )
        
        session = await self._upstream.create_session(context)
        
        try:
            return await self._resolve_chain(session, params)
        finally:
            await session.close()
    
    async def _resolve_chain(
        self,
        session: UpstreamSession,
        params: dict | None = None,
    ) -> str:
        max_hops = 5
        url = self._upstream.config.endpoint
        
        for hop in range(max_hops):
            # Request with session context
            response = await session.request(params=params)
            
            # Parse response
            parsed = parse_vast_xml(response)
            
            if parsed.is_inline:
                # Final response
                return response
            else:
                # Get next URL
                url = parsed.redirect_url
                # Continue loop
        
        raise Exception(f"Max hops ({max_hops}) exceeded")
```

### Session Preservation

Session context flows through entire chain:

```python
# Wrapper 1 request
response1 = await session.request(params={"correlator": "session-123"})
# Response includes session cookies

# Wrapper 2 request
response2 = await session.request(params={"correlator": "session-123"})
# Same session context preserved

# Wrapper 3 request
response3 = await session.request(params={"correlator": "session-123"})
# Cookies maintained across chain
```

---

## StateBackend Abstraction

### Protocol

```python
class StateBackend(Protocol):
    """Protocol for state persistence."""
    
    async def get_count(self, key: str) -> int:
        """Get count value."""
    
    async def increment(self, key: str) -> int:
        """Increment count."""
    
    async def set_expiry(self, key: str, seconds: int) -> None:
        """Set expiry time in seconds."""
    
    async def get_spend(self, key: str) -> float:
        """Get spend value."""
    
    async def add_spend(self, key: str, amount: float) -> float:
        """Add to spend and return new total."""
    
    async def flush(self) -> None:
        """Flush pending changes."""
```

### Implementations

**InMemoryBackend** (Testing)
```python
class InMemoryBackend:
    """In-memory state backend for testing."""
    
    def __init__(self):
        self._data: dict[str, Any] = {}
        self._expiry: dict[str, float] = {}
```

**RedisBackend** (Production)
```python
class RedisBackend:
    """Redis state backend for distributed systems."""
    
    def __init__(self, redis_url: str):
        self._redis = redis.from_url(redis_url)
```

**DatabaseBackend** (Persistence)
```python
class DatabaseBackend:
    """Database state backend for persistence."""
    
    def __init__(self, db_url: str):
        self._db = create_engine(db_url)
```

---

## Error Recovery

### Session Errors

```python
try:
    response = await session.request()
except TimeoutError:
    # Timeout - try fallback
    return await fallback.fetch()
except UpstreamError:
    # Upstream error - increment error count
    await state_backend.increment(f"errors:{campaign_id}")
    return None
```

### Frequency Cap Errors

```python
try:
    if await session.check_frequency_cap(user_id):
        await session.track_budget(campaign_id, cpm)
    else:
        # Cap exceeded - try fallback
        return await fallback.fetch()
except StateBackendError:
    # Backend unavailable - fail open (serve ad)
    return await session.request()
```

### Budget Tracking Errors

```python
try:
    await session.track_budget(campaign_id, cpm)
except StateBackendError:
    # Backend unavailable
    # Log error but don't fail ad serving
    logger.error(f"Failed to track budget: {campaign_id}")
    # Still serve the ad
```

---

## Performance Considerations

### Session Context (Immutable)

✅ **Pros:**
- Zero-copy passing between functions
- Can be cached in memory
- Hashable for use in sets/dicts

⚠️ **Cons:**
- Must recreate for each session

### StateBackend Access

✅ **Optimization:**
- Batch operations (get/set multiple keys)
- Use Redis pipelines
- Connection pooling

⚠️ **Consider:**
- Network latency (Redis)
- Database queries (database backend)
- In-memory size (memory backend)

### Cleanup

```python
# Use context manager pattern
async with session:
    # Automatic cleanup on exit
    pass

# Or try/finally
try:
    ...
finally:
    await session.close()  # Always cleanup
```

---

## Best Practices

1. **Always Call close()** - Use try/finally or context managers
2. **Check Caps Before Serving** - Prevent over-serving
3. **Track Spend Accurately** - Log actual CPM, not estimated
4. **Use Immutable Context** - Don't mutate SessionContext
5. **Handle Backend Errors** - Degrade gracefully
6. **Log Session ID** - Use request_id for debugging
7. **Set Expiry on Caps** - Clean up old data

---

## Summary

Sessions enable sophisticated stateful ad serving by:

- Maintaining immutable context throughout request chain
- Supporting frequency capping per user
- Tracking budget per campaign
- Enabling graceful degradation on errors
- Preserving session state across VAST wrapper chain

This architecture supports production-scale ad networks with multiple upstreams, fallbacks, and complex business logic.

---

**Next:** See [Final Architecture](00-final-architecture.md) for complete system design.
