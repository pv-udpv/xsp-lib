# Session Management Guide

This comprehensive guide explains how to use xsp-lib's session management system for stateful ad serving, including frequency capping, budget tracking, and multi-ad pod handling.

## Table of Contents

1. [What is a Session?](#what-is-a-session)
2. [When to Use Sessions](#when-to-use-sessions)
3. [Creating Sessions](#creating-sessions)
4. [Session Lifecycle](#session-lifecycle)
5. [Testing Sessions](#testing-sessions)
6. [Production Deployment](#production-deployment)
7. [Best Practices](#best-practices)

## What is a Session?

A **session** in xsp-lib represents a stateful interaction with an upstream AdTech service across multiple ad requests. Sessions maintain context and state, enabling features like frequency capping, budget tracking, and coordinated multi-ad pods.

### SessionContext vs UpstreamSession

xsp-lib separates session concerns into two complementary abstractions:

#### SessionContext (Immutable)

`SessionContext` is an **immutable** dataclass that represents the fixed context of a session:

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class SessionContext:
    """Immutable session context for ad requests.
    
    Attributes:
        session_id: Unique session identifier (UUID recommended)
        user_id: User identifier for frequency capping and personalization
        device_id: Device identifier (IDFA, Android ID, etc.)
        ip_address: Client IP address for geo-targeting
        user_agent: User agent string for device detection
        content_url: URL of content where ad will be shown
        metadata: Additional session metadata (arbitrary key-value pairs)
    """
    session_id: str
    user_id: str | None = None
    device_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    content_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

**Key characteristics:**
- **Frozen**: Cannot be modified after creation (`frozen=True`)
- **Thread-safe**: Safe to share across async tasks
- **Descriptive**: Contains all session identifiers and context
- **Immutable updates**: Use `with_metadata()` to create new instances

**Example:**
```python
from uuid import uuid4

# Create immutable context
context = SessionContext(
    session_id=str(uuid4()),
    user_id="user_12345",
    device_id="IDFA-ABC-123",
    ip_address="203.0.113.42",
    metadata={"placement": "pre-roll", "app": "mobile"}
)

# Cannot modify: This raises FrozenInstanceError
# context.user_id = "other_user"  # ❌ Error!

# Create new context with additional metadata
new_context = context.with_metadata(position="midroll", ad_format="video")
# Original context unchanged ✅
```

#### UpstreamSession (Mutable State)

`UpstreamSession` is a **protocol** defining how upstreams manage mutable session state:

```python
from typing import Any, Protocol

class UpstreamSession(Protocol):
    """Stateful session protocol for upstream services."""
    
    async def start_session(self, context: SessionContext) -> None:
        """Initialize session with context."""
        ...
    
    async def fetch_with_session(
        self,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Fetch using session state."""
        ...
    
    async def update_session_state(self, state: dict[str, Any]) -> None:
        """Update mutable session state."""
        ...
    
    async def get_session_state(self) -> dict[str, Any]:
        """Get current session state."""
        ...
    
    async def end_session(self) -> None:
        """Clean up session resources."""
        ...
```

**Key characteristics:**
- **Mutable**: Internal state changes across requests
- **Stateful**: Tracks impressions, spend, caps, etc.
- **Persistent**: Can save state to Redis, DynamoDB, etc.
- **Lifecycle managed**: Clear creation → usage → cleanup flow

**Why separate immutable context from mutable state?**

1. **Clarity**: Context describes "who/what/where", state tracks "how many/how much"
2. **Safety**: Immutable context prevents bugs from unintended changes
3. **Concurrency**: Context can be safely shared across tasks
4. **Flexibility**: State can be persisted, cached, or held in-memory
5. **Testing**: Easy to mock state independently of context

### Relationship Diagram

```
┌─────────────────────────────────┐
│     SessionContext (Immutable)   │
│  - session_id: "sess_123"       │
│  - user_id: "user_456"          │
│  - device_id: "IDFA-ABC"        │
│  - metadata: {...}              │
└─────────────┬───────────────────┘
              │
              │ Passed to
              ▼
┌─────────────────────────────────┐
│  UpstreamSession (Mutable State) │
│  - _context: SessionContext     │
│  - _session_state: {            │
│      "impressions_shown": 3,    │
│      "total_spend": 1.50,       │
│      "last_request": 1234567890 │
│    }                            │
└─────────────────────────────────┘
```

## When to Use Sessions

Use sessions when you need:

### ✅ Use Sessions For

- **Frequency Capping**: Limit impressions per user/campaign/creative
- **Budget Tracking**: Monitor and enforce campaign spend limits
- **Ad Pods**: Coordinate multiple ads in a single viewing session (VMAP)
- **User Experience**: Ensure ad diversity and prevent ad fatigue
- **Personalization**: Build user profiles across requests
- **Analytics**: Track user journey and engagement metrics
- **Compliance**: Meet advertiser requirements and IAB standards

### ❌ Don't Use Sessions For

- **Single ad requests**: Use stateless `BaseUpstream.fetch()` instead
- **Server-to-server only**: Sessions are for user-facing scenarios
- **Read-only data**: If you're not tracking state, sessions add overhead
- **High-throughput RTB**: OpenRTB bidding is typically stateless

### Comparison Table

| Scenario | Stateless | Session | Reason |
|----------|-----------|---------|--------|
| Single VAST ad | ✅ | ❌ | No state to track |
| Frequency capped ads | ❌ | ✅ | Must count impressions |
| OpenRTB bid request | ✅ | ❌ | Typically stateless |
| VMAP ad pod | ❌ | ✅ | Coordinated multi-ad |
| Budget tracking | ❌ | ✅ | Must track spend |
| Video player session | ❌ | ✅ | Multiple interactions |

## Creating Sessions

### Basic Session Creation

```python
import asyncio
from uuid import uuid4
from xsp.core.base import BaseUpstream
from xsp.transports.http import HttpTransport

# Example session-aware upstream (conceptual)
class SessionUpstream(BaseUpstream[str]):
    """Upstream with session support."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._context: SessionContext | None = None
        self._session_state: dict[str, Any] = {}
    
    async def start_session(self, context: SessionContext) -> None:
        """Initialize session."""
        self._context = context
        self._session_state = {"request_count": 0}
    
    async def fetch_with_session(
        self,
        params: dict[str, Any] | None = None,
        **kwargs,
    ) -> str:
        """Fetch using session context."""
        if self._context is None:
            raise ValueError("Session not started")
        
        # Increment request counter
        self._session_state["request_count"] += 1
        
        # Merge context into params
        merged_params = params or {}
        if self._context.user_id:
            merged_params["user_id"] = self._context.user_id
        
        return await self.fetch(params=merged_params, **kwargs)
    
    async def get_session_state(self) -> dict[str, Any]:
        """Get current state."""
        return self._session_state.copy()
    
    async def end_session(self) -> None:
        """Clean up session."""
        self._context = None
        self._session_state = {}
        await self.close()

async def main():
    # Create upstream
    upstream = SessionUpstream(
        transport=HttpTransport(),
        decoder=lambda b: b.decode('utf-8'),
        endpoint="https://ads.example.com/vast"
    )
    
    # Create session context
    context = SessionContext(
        session_id=str(uuid4()),
        user_id="user_12345",
        device_id="IDFA-ABC-123"
    )
    
    # Initialize session
    await upstream.start_session(context)
    
    try:
        # Make session-aware request
        ad = await upstream.fetch_with_session(
            params={"w": "640", "h": "480"}
        )
        print(f"Fetched ad: {ad[:100]}...")
        
        # Check state
        state = await upstream.get_session_state()
        print(f"Requests: {state['request_count']}")
    
    finally:
        # Always clean up
        await upstream.end_session()

if __name__ == "__main__":
    asyncio.run(main())
```

For complete working examples, see:
- **[examples/session_management.py](../../examples/session_management.py)** - Complete session lifecycle examples
- **[examples/frequency_capping.py](../../examples/frequency_capping.py)** - Frequency capping integration
- **[examples/budget_tracking.py](../../examples/budget_tracking.py)** - Budget tracking implementation

### Session with State Backend

For production use, persist session state to a backend like Redis:

```python
from typing import Any, Protocol

class StateBackend(Protocol):
    """Persistent state backend interface."""
    
    async def get(self, key: str) -> Any | None:
        """Retrieve value by key."""
        ...
    
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store value with optional TTL."""
        ...

class PersistentSessionUpstream(SessionUpstream):
    """Session upstream with persistent state."""
    
    def __init__(self, *args, state_backend: StateBackend, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_backend = state_backend
    
    async def start_session(self, context: SessionContext) -> None:
        """Initialize session, loading persisted state."""
        self._context = context
        
        # Load existing state from backend
        key = f"session:{context.session_id}"
        persisted_state = await self.state_backend.get(key)
        
        if persisted_state:
            self._session_state = persisted_state
        else:
            self._session_state = {"request_count": 0}
    
    async def fetch_with_session(self, params=None, **kwargs):
        """Fetch and persist updated state."""
        result = await super().fetch_with_session(params, **kwargs)
        
        # Persist state after each request
        if self._context:
            key = f"session:{self._context.session_id}"
            await self.state_backend.set(
                key, 
                self._session_state, 
                ttl=3600  # 1 hour TTL
            )
        
        return result
```

### Context Manager Pattern

For cleaner resource management, use sessions as async context managers:

```python
class SessionUpstream(BaseUpstream[str]):
    """Session upstream with context manager support."""
    
    async def __aenter__(self):
        """Enter context."""
        if self._context is None:
            raise ValueError("Call start_session() before using as context manager")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context, cleaning up."""
        await self.end_session()
        return False

async def main():
    upstream = SessionUpstream(...)
    context = SessionContext(session_id=str(uuid4()))
    
    await upstream.start_session(context)
    
    # Use as context manager for automatic cleanup
    async with upstream:
        ad1 = await upstream.fetch_with_session()
        ad2 = await upstream.fetch_with_session()
        # Session automatically ended on exit
```

## Session Lifecycle

Sessions follow a four-phase lifecycle: **Creation → Requests → State Updates → Cleanup**

### Lifecycle Diagram

```
┌─────────────┐
│   Created   │
│             │
│ Context set │
│ State init  │
└──────┬──────┘
       │ start_session(context)
       ▼
┌─────────────┐
│   Active    │◄─────┐
│             │      │
│ Fetch ads   │      │
│ Track state │      │
└──────┬──────┘      │
       │             │
       │ fetch_with_session()
       │ update_session_state()
       │             │
       └─────────────┘
       │
       │ end_session()
       ▼
┌─────────────┐
│    Ended    │
│             │
│ State saved │
│ Resources   │
│ released    │
└─────────────┘
```

### Phase 1: Creation

Initialize the session with context:

```python
# Create upstream instance
upstream = SessionUpstream(
    transport=HttpTransport(),
    decoder=lambda b: b.decode('utf-8'),
    endpoint="https://ads.example.com/vast"
)

# Create immutable context
context = SessionContext(
    session_id=str(uuid4()),
    user_id="user_12345",
    device_id="IDFA-ABC-123",
    ip_address="203.0.113.42",
    metadata={
        "placement": "pre-roll",
        "content_id": "video_789"
    }
)

# Start session (loads persisted state if available)
await upstream.start_session(context)
```

**What happens:**
- Context stored (immutable)
- State initialized (mutable)
- Persisted state loaded (if backend configured)
- Resources allocated

### Phase 2: Requests

Make one or more requests using the session:

```python
# First ad request
ad1 = await upstream.fetch_with_session(
    params={"w": "640", "h": "480", "position": "1"}
)

# State automatically updated
state = await upstream.get_session_state()
print(f"Request count: {state['request_count']}")  # 1

# Second ad request
ad2 = await upstream.fetch_with_session(
    params={"w": "640", "h": "480", "position": "2"}
)

# State incremented again
state = await upstream.get_session_state()
print(f"Request count: {state['request_count']}")  # 2
```

**What happens each request:**
1. Context merged into request params
2. Request sent to upstream
3. Response received and decoded
4. State updated (counters, timestamps, etc.)
5. State persisted to backend (if configured)

### Phase 3: State Updates

Explicitly update session state outside of fetches:

```python
# Record impression after ad plays
await upstream.update_session_state({
    "impressions_shown": 2,
    "last_impression_time": time.time(),
    "total_watch_time_seconds": 45,
})

# Record campaign exposure
await upstream.update_session_state({
    "campaign_ids_seen": ["camp_1", "camp_2"],
    "advertiser_ids_seen": ["adv_1"],
})

# Update budget tracking
await upstream.update_session_state({
    "total_spend": 1.50,  # $1.50 total
})
```

**Use cases for explicit updates:**
- Recording impressions after ad plays
- Tracking video completion events
- Updating budget spend
- Logging user interactions
- Accumulating analytics data

### Phase 4: Cleanup

End the session and release resources:

```python
# End session (always call this!)
await upstream.end_session()
```

**What happens:**
- Final state persisted to backend
- Resources released (connections, memory)
- Context cleared
- State reset

**Always use try/finally:**

```python
await upstream.start_session(context)

try:
    # Your session operations
    ad = await upstream.fetch_with_session()
    
except Exception as e:
    print(f"Error: {e}")
    
finally:
    # Always clean up, even on error
    await upstream.end_session()
```

### Complete Lifecycle Example

See **[examples/session_management.py](../../examples/session_management.py)** for a complete working example demonstrating all four phases.

## Testing Sessions

Testing session-based code requires mocking both the transport and state backend.

### In-Memory State Backend

For tests, use an in-memory backend instead of Redis:

```python
import time
from typing import Any

class MemoryBackend:
    """In-memory state backend for testing."""
    
    def __init__(self) -> None:
        self._data: dict[str, tuple[Any, float | None]] = {}
    
    async def get(self, key: str) -> Any | None:
        """Get value, checking expiration."""
        if key not in self._data:
            return None
        
        value, expires_at = self._data[key]
        
        # Check if expired
        if expires_at is not None and time.time() > expires_at:
            del self._data[key]
            return None
        
        return value
    
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value with optional TTL."""
        expires_at = None
        if ttl is not None:
            expires_at = time.time() + ttl
        
        self._data[key] = (value, expires_at)
    
    async def increment(self, key: str, delta: int = 1) -> int:
        """Atomically increment counter."""
        current = await self.get(key)
        if current is None:
            current = 0
        
        new_value = current + delta
        await self.set(key, new_value)
        return new_value
    
    async def delete(self, key: str) -> None:
        """Delete key."""
        self._data.pop(key, None)
    
    def clear(self) -> None:
        """Clear all data (testing utility)."""
        self._data.clear()
```

### Test Session Creation

```python
import pytest
from uuid import uuid4

@pytest.mark.asyncio
async def test_session_creation():
    """Test session initialization."""
    # Setup
    backend = MemoryBackend()
    upstream = PersistentSessionUpstream(
        transport=MemoryTransport(b"mock response"),
        decoder=lambda b: b.decode('utf-8'),
        endpoint="memory://test",
        state_backend=backend
    )
    
    context = SessionContext(
        session_id=str(uuid4()),
        user_id="test_user"
    )
    
    # Execute
    await upstream.start_session(context)
    
    # Verify
    state = await upstream.get_session_state()
    assert state["request_count"] == 0
    
    # Cleanup
    await upstream.end_session()
```

### Test Session State Updates

```python
@pytest.mark.asyncio
async def test_session_state_updates():
    """Test state updates and persistence."""
    backend = MemoryBackend()
    upstream = PersistentSessionUpstream(
        transport=MemoryTransport(b"ad data"),
        decoder=lambda b: b.decode('utf-8'),
        endpoint="memory://test",
        state_backend=backend
    )
    
    context = SessionContext(session_id="sess_123")
    await upstream.start_session(context)
    
    # Make request
    await upstream.fetch_with_session()
    
    # Update state
    await upstream.update_session_state({"impressions": 1})
    
    # Verify state
    state = await upstream.get_session_state()
    assert state["request_count"] == 1
    assert state["impressions"] == 1
    
    # Verify persistence
    persisted = await backend.get("session:sess_123")
    assert persisted["impressions"] == 1
    
    await upstream.end_session()
```

### Test Session Persistence

```python
@pytest.mark.asyncio
async def test_session_persistence():
    """Test session state survives across instances."""
    backend = MemoryBackend()
    context = SessionContext(session_id="persistent_sess")
    
    # First session: create and update state
    upstream1 = PersistentSessionUpstream(
        transport=MemoryTransport(b"data"),
        decoder=lambda b: b.decode('utf-8'),
        endpoint="memory://test",
        state_backend=backend
    )
    
    await upstream1.start_session(context)
    await upstream1.fetch_with_session()
    await upstream1.update_session_state({"impressions": 5})
    await upstream1.end_session()
    
    # Second session: load persisted state
    upstream2 = PersistentSessionUpstream(
        transport=MemoryTransport(b"data"),
        decoder=lambda b: b.decode('utf-8'),
        endpoint="memory://test",
        state_backend=backend
    )
    
    await upstream2.start_session(context)
    state = await upstream2.get_session_state()
    
    # Verify state was persisted and loaded
    assert state["request_count"] == 1  # From first session
    assert state["impressions"] == 5    # From update
    
    await upstream2.end_session()
```

### Mock Transport for Testing

```python
from xsp.transports.memory import MemoryTransport

@pytest.mark.asyncio
async def test_session_with_mock_transport():
    """Test session with predictable responses."""
    # Mock VAST XML response
    mock_vast = b"""<?xml version="1.0"?>
<VAST version="4.2">
    <Ad id="test123">
        <InLine>
            <AdTitle>Test Ad</AdTitle>
        </InLine>
    </Ad>
</VAST>"""
    
    upstream = SessionUpstream(
        transport=MemoryTransport(mock_vast),
        decoder=lambda b: b.decode('utf-8'),
        endpoint="memory://vast"
    )
    
    context = SessionContext(session_id="test_session")
    await upstream.start_session(context)
    
    # Fetch returns our mock data
    result = await upstream.fetch_with_session()
    assert "Test Ad" in result
    
    await upstream.end_session()
```

### Testing Complete Example

```python
import pytest
from uuid import uuid4

@pytest.fixture
def memory_backend():
    """Provide clean in-memory backend for each test."""
    backend = MemoryBackend()
    yield backend
    backend.clear()

@pytest.fixture
def mock_transport():
    """Provide mock transport."""
    return MemoryTransport(b"mock ad response")

@pytest.mark.asyncio
async def test_complete_session_workflow(memory_backend, mock_transport):
    """Test complete session workflow."""
    # Setup
    upstream = PersistentSessionUpstream(
        transport=mock_transport,
        decoder=lambda b: b.decode('utf-8'),
        endpoint="memory://test",
        state_backend=memory_backend
    )
    
    context = SessionContext(
        session_id=str(uuid4()),
        user_id="test_user_123"
    )
    
    # Phase 1: Start session
    await upstream.start_session(context)
    initial_state = await upstream.get_session_state()
    assert initial_state["request_count"] == 0
    
    # Phase 2: Make requests
    for i in range(3):
        result = await upstream.fetch_with_session()
        assert result == "mock ad response"
    
    # Phase 3: Check state
    state = await upstream.get_session_state()
    assert state["request_count"] == 3
    
    # Phase 4: Update state
    await upstream.update_session_state({"custom_field": "test_value"})
    
    # Verify update
    final_state = await upstream.get_session_state()
    assert final_state["custom_field"] == "test_value"
    
    # Phase 5: End session
    await upstream.end_session()
```

## Production Deployment

### Redis Backend

For production, use Redis for distributed state:

```python
import json
from typing import Any
import aioredis

class RedisBackend:
    """Production Redis state backend."""
    
    def __init__(
        self, 
        host: str = "localhost", 
        port: int = 6379, 
        db: int = 0,
        password: str | None = None
    ):
        """Initialize Redis backend.
        
        Args:
            host: Redis server hostname
            port: Redis server port
            db: Redis database number
            password: Optional Redis password
        """
        url = f"redis://{host}:{port}/{db}"
        if password:
            url = f"redis://:{password}@{host}:{port}/{db}"
        
        self.redis = aioredis.from_url(url, decode_responses=False)
    
    async def get(self, key: str) -> Any | None:
        """Get value from Redis."""
        value = await self.redis.get(key)
        if value is None:
            return None
        return json.loads(value)
    
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in Redis with optional TTL."""
        serialized = json.dumps(value)
        if ttl:
            await self.redis.setex(key, ttl, serialized)
        else:
            await self.redis.set(key, serialized)
    
    async def increment(self, key: str, delta: int = 1) -> int:
        """Atomically increment counter."""
        return await self.redis.incrby(key, delta)
    
    async def delete(self, key: str) -> None:
        """Delete key from Redis."""
        await self.redis.delete(key)
    
    async def close(self) -> None:
        """Close Redis connection."""
        await self.redis.close()
```

### Production Configuration

```python
import os
from xsp.core.config import get_settings

async def create_production_upstream():
    """Create production-ready session upstream."""
    settings = get_settings()
    
    # Redis backend with connection pooling
    redis = RedisBackend(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        password=os.getenv("REDIS_PASSWORD")
    )
    
    # Session upstream with production config
    upstream = PersistentSessionUpstream(
        transport=HttpTransport(
            timeout=settings.vast_timeout,  # From XspSettings
            pool_size=settings.http_pool_size
        ),
        decoder=lambda b: b.decode('utf-8'),
        endpoint=settings.vast_endpoint,
        state_backend=redis
    )
    
    return upstream
```

### Error Handling

```python
from xsp.core.exceptions import XspError

async def production_session_with_error_handling():
    """Production session with comprehensive error handling."""
    upstream = await create_production_upstream()
    context = SessionContext(
        session_id=str(uuid4()),
        user_id="user_12345"
    )
    
    try:
        await upstream.start_session(context)
        
        try:
            # Main session logic
            ad = await upstream.fetch_with_session()
            
        except TransportError as e:
            # Handle network errors
            print(f"Network error: {e}")
            # Log to monitoring system
            # Return fallback ad
            
        except XspError as e:
            # Handle session errors
            print(f"Session error: {e}")
            # Reset session if corrupted
            
    finally:
        # Always clean up, even on error
        try:
            await upstream.end_session()
        except Exception as e:
            print(f"Error during cleanup: {e}")
            # Log but don't raise - cleanup is best-effort
```

### Monitoring and Metrics

```python
import time
from typing import Any

class MetricsSessionUpstream(PersistentSessionUpstream):
    """Session upstream with metrics tracking."""
    
    async def fetch_with_session(self, params=None, **kwargs):
        """Fetch with timing metrics."""
        start_time = time.time()
        
        try:
            result = await super().fetch_with_session(params, **kwargs)
            
            # Record success metric
            duration = time.time() - start_time
            await self._record_metric("session.fetch.success", duration)
            
            return result
            
        except Exception as e:
            # Record error metric
            duration = time.time() - start_time
            await self._record_metric("session.fetch.error", duration)
            raise
    
    async def _record_metric(self, name: str, value: float) -> None:
        """Record metric to monitoring system."""
        # Send to Prometheus, StatsD, CloudWatch, etc.
        print(f"METRIC: {name} = {value:.3f}s")
```

## Best Practices

### 1. Always Clean Up Sessions

Use `try/finally` or async context managers:

```python
# ✅ Good: Cleanup guaranteed
await upstream.start_session(context)
try:
    await upstream.fetch_with_session()
finally:
    await upstream.end_session()

# ✅ Better: Use context manager
await upstream.start_session(context)
async with upstream:
    await upstream.fetch_with_session()
```

### 2. Set Appropriate TTLs

Configure TTLs based on use case:

```python
# Short TTL for active sessions (1 hour)
await backend.set(key, state, ttl=3600)

# Longer TTL for historical data (24 hours)
await backend.set(key, final_state, ttl=86400)

# No TTL for permanent data
await backend.set(key, user_profile, ttl=None)
```

### 3. Use Immutable Context

Never mutate `SessionContext` - create new instances:

```python
# ❌ Bad: Cannot mutate frozen context
context.user_id = "new_user"  # Raises error!

# ✅ Good: Create new context
new_context = context.with_metadata(additional_field="value")
```

### 4. Validate State on Load

Check persisted state for corruption:

```python
async def start_session(self, context: SessionContext) -> None:
    """Start session with state validation."""
    self._context = context
    
    key = f"session:{context.session_id}"
    persisted = await self.state_backend.get(key)
    
    if persisted:
        # Validate state structure
        if not isinstance(persisted.get("request_count"), int):
            # State corrupted, reset
            self._session_state = {"request_count": 0}
        else:
            self._session_state = persisted
    else:
        self._session_state = {"request_count": 0}
```

### 5. Separate Concerns

Keep context (immutable) separate from state (mutable):

```python
# ✅ Good: Clear separation
context = SessionContext(user_id="user_123")  # Immutable
state = {"impressions": 0}  # Mutable

# ❌ Bad: Mixing concerns
state = {
    "user_id": "user_123",  # Should be in context
    "impressions": 0
}
```

### 6. Use Type Hints

Full type annotations help catch bugs:

```python
from typing import Any

async def fetch_with_session(
    self,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> str:
    """Fetch with explicit types."""
    ...
```

### 7. Test with Real Scenarios

Test production-like scenarios:

```python
@pytest.mark.asyncio
async def test_session_under_load():
    """Test session with multiple rapid requests."""
    upstream = SessionUpstream(...)
    await upstream.start_session(context)
    
    # Simulate rapid requests
    tasks = [
        upstream.fetch_with_session()
        for _ in range(100)
    ]
    
    results = await asyncio.gather(*tasks)
    assert len(results) == 100
    
    state = await upstream.get_session_state()
    assert state["request_count"] == 100
```

### 8. Document State Schema

Document expected state structure:

```python
async def start_session(self, context: SessionContext) -> None:
    """Initialize session.
    
    State schema:
        {
            "request_count": int,  # Number of requests made
            "impressions_shown": int,  # Number of impressions
            "total_spend": float,  # Total spend in currency units
            "campaign_ids": list[str],  # Campaigns shown
            "last_request_time": float,  # Unix timestamp
        }
    """
    self._context = context
    self._session_state = {
        "request_count": 0,
        "impressions_shown": 0,
        "total_spend": 0.0,
        "campaign_ids": [],
        "last_request_time": time.time(),
    }
```

## Related Documentation

- **[Architecture: Session Management](../architecture/session-management.md)** - Technical architecture details
- **[Guide: Stateful Ad Serving](./stateful-ad-serving.md)** - Frequency capping and budget tracking
- **[Examples: Session Management](../../examples/session_management.py)** - Complete working examples
- **[Examples: Frequency Capping](../../examples/frequency_capping.py)** - Frequency cap integration
- **[Examples: Budget Tracking](../../examples/budget_tracking.py)** - Budget tracking implementation

## Summary

Session management in xsp-lib enables stateful ad serving through:

- **SessionContext**: Immutable session identifiers and metadata
- **UpstreamSession**: Protocol for stateful upstream interactions  
- **State Backends**: Pluggable persistence (Redis, memory, etc.)
- **Lifecycle Management**: Clear creation → usage → cleanup flow
- **Testing Support**: In-memory backends and mocks
- **Production Ready**: Error handling, monitoring, and best practices

For hands-on learning:
1. Run **[examples/session_management.py](../../examples/session_management.py)** to see basic session usage
2. Explore **[examples/frequency_capping.py](../../examples/frequency_capping.py)** for frequency capping
3. Review **[examples/budget_tracking.py](../../examples/budget_tracking.py)** for budget management
4. Read **[stateful-ad-serving.md](./stateful-ad-serving.md)** for advanced production scenarios

---

**Document Version**: 1.0  
**Last Updated**: 2025-12-10  
**Status**: Production Ready
