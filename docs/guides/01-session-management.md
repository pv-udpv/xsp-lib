# Session Management User Guide

**Version:** 1.0  
**Date:** December 10, 2025  
**For:** Application Developers  

## Quick Start

### 1. Create a Session

```python
from xsp.core.session import SessionContext
from xsp.protocols.vast import VastUpstream
from xsp.transports.http import HttpTransport
import time
import uuid

# Create session context
context = SessionContext(
    timestamp=int(time.time() * 1000),
    correlator=str(uuid.uuid4()),
    cachebusting=str(uuid.uuid4()),
    cookies={"uid": "user123"},
    request_id=f"req-{uuid.uuid4().hex[:8]}",
)

# Create upstream
upstream = VastUpstream(
    transport=HttpTransport(),
    endpoint="https://ads.example.com/vast",
)

# Create session
session = await upstream.create_session(context)
```

### 2. Serve an Ad

```python
try:
    # Check frequency cap
    if await session.check_frequency_cap(user_id="user123", limit=3):
        # Fetch ad
        ad = await session.request(params={"slot": "pre-roll"})
        
        # Track spend
        await session.track_budget("campaign-1", amount=2.50)
        
        # Return ad to player
        return ad
    else:
        # User hit cap, return fallback
        return None
finally:
    # Always cleanup
    await session.close()
```

---

## Session Lifecycle

### Creation Phase

```python
context = SessionContext(
    timestamp=int(time.time() * 1000),      # Current time in ms
    correlator="session-abc123",            # Unique session ID
    cachebusting="789456",                  # Random for cache-busting
    cookies={"uid": user_id},               # HTTP cookies
    request_id="req-xyz",                   # For logging/tracing
)
```

**Key Points:**
- Timestamp used for macro substitution
- Correlator tracked across entire session
- Cookies preserved across requests
- Request ID for debugging

### Operation Phase

```python
# Frequency cap check
if await session.check_frequency_cap(user_id):
    # User is under cap - safe to serve
    ad = await session.request()
    
    # Track the spend
    await session.track_budget(campaign_id, cpm)
else:
    # User is at/over cap - don't serve
    return fallback()
```

### Cleanup Phase

```python
try:
    # Operations
    ad = await session.request()
finally:
    # ALWAYS cleanup
    await session.close()
    # Flushes state backend
    # Releases resources
    # Logs metrics
```

---

## Frequency Capping

### Basic Implementation

```python
async def serve_with_frequency_cap(
    session: UpstreamSession,
    user_id: str,
    max_ads_per_hour: int = 3,
) -> Optional[str]:
    """Serve ad if user hasn't exceeded frequency cap."""
    
    # Check cap
    if not await session.check_frequency_cap(
        user_id=user_id,
        limit=max_ads_per_hour,
    ):
        # User at cap
        logger.info(f"Frequency cap reached: {user_id}")
        return None
    
    # Fetch ad
    ad = await session.request(params={"slot": "pre-roll"})
    return ad
```

### Multiple Time Windows

```python
async def multi_window_cap(
    session: UpstreamSession,
    user_id: str,
) -> bool:
    """Check frequency caps across multiple windows."""
    
    # Hourly cap: 5 ads
    hourly_cap = await session.check_frequency_cap(
        user_id=f"freq:hourly:{user_id}",
        limit=5,
    )
    
    # Daily cap: 20 ads
    daily_cap = await session.check_frequency_cap(
        user_id=f"freq:daily:{user_id}",
        limit=20,
    )
    
    return hourly_cap and daily_cap
```

### StateBackend Integration

```python
# Behind the scenes:
# session.check_frequency_cap(user_id) does:
# 1. Get current count from StateBackend
# 2. Compare against limit
# 3. Return True if under limit, False if at/over

# StateBackend implementations:
# - InMemoryBackend: For testing
# - RedisBackend: For production (distributed)
# - DatabaseBackend: For persistence
```

---

## Budget Tracking

### Basic Implementation

```python
async def serve_with_budget(
    session: UpstreamSession,
    campaign_id: str,
    budget_limit: float,
    estimated_cpm: float = 2.50,
) -> Optional[str]:
    """Serve ad if campaign has budget remaining."""
    
    # Get current spend
    current_spend = await session.get_budget(campaign_id)
    remaining = budget_limit - current_spend
    
    if remaining < estimated_cpm:
        # Budget exhausted
        logger.warning(f"Budget exhausted: {campaign_id}")
        return None
    
    # Serve ad
    ad = await session.request()
    
    # Track spend
    await session.track_budget(campaign_id, estimated_cpm)
    
    return ad
```

### Per-Campaign Tracking

```python
class CampaignBudgetManager:
    def __init__(self, state_backend: StateBackend):
        self.state_backend = state_backend
    
    async def can_serve(self, campaign_id: str, budget_limit: float) -> bool:
        current_spend = await self.state_backend.get_spend(
            f"budget:{campaign_id}"
        )
        return current_spend < budget_limit
    
    async def track_spend(self, campaign_id: str, amount: float) -> float:
        new_total = await self.state_backend.add_spend(
            f"budget:{campaign_id}",
            amount,
        )
        return new_total
```

---

## VAST Chain Resolution

### Simple Wrapper Chain

```python
class VastChainResolver:
    def __init__(self, upstream: VastUpstream):
        self.upstream = upstream
    
    async def resolve(self, user_id: str) -> str:
        """Resolve VAST wrapper chain to inline."""
        context = SessionContext(
            timestamp=int(time.time() * 1000),
            correlator=f"chain-{user_id}",
            cachebusting=str(random.randint(0, 999999999)),
            cookies={},
            request_id=f"req-{uuid.uuid4().hex[:8]}",
        )
        
        session = await self.upstream.create_session(context)
        
        try:
            return await self._resolve_chain(session)
        finally:
            await session.close()
    
    async def _resolve_chain(self, session: UpstreamSession) -> str:
        max_hops = 5
        
        for hop in range(max_hops):
            # Request with session context
            response = await session.request()
            
            # Parse VAST
            parsed = self._parse_vast(response)
            
            if parsed.is_inline:
                # Got final response
                return response
            else:
                # Wrapper - continue
                continue
        
        raise Exception(f"Max hops ({max_hops}) exceeded")
    
    def _parse_vast(self, xml: str) -> ParsedVast:
        # Implementation details...
        pass
```

### With Frequency Capping

```python
async def resolve_with_cap(
    resolver: VastChainResolver,
    session: UpstreamSession,
    user_id: str,
) -> Optional[str]:
    """Resolve VAST chain if user under frequency cap."""
    
    # Check cap first
    if not await session.check_frequency_cap(user_id, limit=3):
        return None  # Cap exceeded
    
    # Resolve chain
    try:
        ad = await resolver.resolve(user_id)
        
        # Track spend
        await session.track_budget("campaign-1", 2.50)
        
        return ad
    except Exception as e:
        logger.error(f"Chain resolution failed: {e}")
        return None
```

---

## StateBackend Selection

### For Testing: InMemoryBackend

```python
from xsp.state_backends.memory import InMemoryBackend

# Use in tests
backend = InMemoryBackend()
session = await upstream.create_session(context, backend)

# Data is in memory, cleared on exit
```

### For Production: RedisBackend

```python
from xsp.state_backends.redis import RedisBackend

# Production use
backend = RedisBackend(redis_url="redis://localhost:6379")
session = await upstream.create_session(context, backend)

# Data persisted in Redis
# Distributed across instances
```

### For Persistence: DatabaseBackend

```python
from xsp.state_backends.db import DatabaseBackend

# Long-term persistence
backend = DatabaseBackend(db_url="postgresql://...")
session = await upstream.create_session(context, backend)

# Data in database for auditing/reporting
```

---

## Error Handling

### Timeout Handling

```python
async def serve_with_timeout_handling(
    session: UpstreamSession,
    fallback: Callable,
) -> str:
    """Serve ad with timeout fallback."""
    try:
        ad = await asyncio.wait_for(
            session.request(),
            timeout=5.0,
        )
        return ad
    except asyncio.TimeoutError:
        logger.warning("Request timeout, using fallback")
        return await fallback()
    finally:
        await session.close()
```

### Frequency Cap Errors

```python
async def serve_with_cap_recovery(
    session: UpstreamSession,
    user_id: str,
) -> Optional[str]:
    """Serve ad with cap check error recovery."""
    try:
        if await session.check_frequency_cap(user_id):
            return await session.request()
    except StateBackendError:
        # Backend unavailable - fail open (serve ad)
        logger.warning(f"StateBackend error for {user_id}")
        return await session.request()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None
```

### Budget Tracking Errors

```python
async def track_with_error_handling(
    session: UpstreamSession,
    campaign_id: str,
    amount: float,
) -> None:
    """Track budget with error handling."""
    try:
        await session.track_budget(campaign_id, amount)
    except StateBackendError:
        # Log but don't fail ad serving
        logger.error(f"Failed to track budget: {campaign_id}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
```

---

## Production Patterns

### Context Manager Pattern

```python
class SessionManager:
    """Manages session lifecycle."""
    
    def __init__(self, upstream: VastUpstream):
        self.upstream = upstream
    
    async def __aenter__(self) -> UpstreamSession:
        context = SessionContext(
            timestamp=int(time.time() * 1000),
            correlator=str(uuid.uuid4()),
            cachebusting=str(random.randint(0, 999999999)),
            cookies={},
            request_id=f"req-{uuid.uuid4().hex[:8]}",
        )
        self.session = await self.upstream.create_session(context)
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

# Usage:
async with SessionManager(upstream) as session:
    ad = await session.request()
    # Automatic cleanup on exit
```

### Retry Pattern

```python
async def serve_with_retries(
    session: UpstreamSession,
    max_retries: int = 3,
) -> Optional[str]:
    """Serve ad with retry logic."""
    for attempt in range(max_retries):
        try:
            return await session.request()
        except UpstreamError as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Metrics Collection

```python
class MetricsCollector:
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.total_latency = 0.0
    
    async def track_request(
        self,
        session: UpstreamSession,
    ) -> Optional[str]:
        """Track metrics while serving."""
        start = time.time()
        
        try:
            result = await session.request()
            self.request_count += 1
            return result
        except Exception as e:
            self.error_count += 1
            raise
        finally:
            elapsed = time.time() - start
            self.total_latency += elapsed
```

---

## Performance Tuning

### Connection Pooling

```python
# Use connection pooling for HTTP
transport = HttpTransport(
    pool_size=100,              # Max concurrent connections
    pool_timeout=30,            # Connection timeout
    keep_alive=True,            # Reuse connections
)

upstream = VastUpstream(
    transport=transport,
    endpoint="https://ads.example.com/vast",
)
```

### Redis Optimization

```python
# Use Redis with pipelining
backend = RedisBackend(
    redis_url="redis://localhost:6379",
    max_connections=50,         # Connection pool
    socket_keepalive=True,      # Keep alive
)
```

### Batch Operations

```python
async def batch_track_budget(
    session: UpstreamSession,
    campaign_spends: dict[str, float],
) -> None:
    """Track multiple budget items efficiently."""
    for campaign_id, amount in campaign_spends.items():
        await session.track_budget(campaign_id, amount)
```

---

## Common Scenarios

### Scenario 1: Basic Pre-Roll Ad

```python
async def serve_preroll(user_id: str) -> Optional[str]:
    context = SessionContext(
        timestamp=int(time.time() * 1000),
        correlator=f"preroll-{user_id}",
        cachebusting=str(random.randint(0, 999999999)),
        cookies={"uid": user_id},
        request_id=f"req-{uuid.uuid4().hex[:8]}",
    )
    
    upstream = VastUpstream(
        transport=HttpTransport(),
        endpoint="https://ads.example.com/vast",
    )
    
    session = await upstream.create_session(context)
    try:
        ad = await session.request(params={"slot": "pre-roll"})
        return ad
    finally:
        await session.close()
```

### Scenario 2: With Frequency Capping

```python
async def serve_with_frequency_cap(user_id: str) -> Optional[str]:
    # ... setup session ...
    
    if await session.check_frequency_cap(user_id, limit=3):
        ad = await session.request()
        return ad
    else:
        return None  # At cap
```

### Scenario 3: With Budget Tracking

```python
async def serve_with_budget(campaign_id: str) -> Optional[str]:
    # ... setup session ...
    
    remaining = budget_limit - await session.get_budget(campaign_id)
    if remaining > 2.50:
        ad = await session.request()
        await session.track_budget(campaign_id, 2.50)
        return ad
    else:
        return None  # Budget exhausted
```

### Scenario 4: VAST Chain Resolution

```python
async def resolve_vast_chain(user_id: str) -> Optional[str]:
    resolver = VastChainResolver(upstream)
    try:
        return await resolver.resolve(user_id)
    except Exception as e:
        logger.error(f"Chain resolution failed: {e}")
        return None
```

---

## Troubleshooting

### Frequency Cap Not Working

**Problem:** Frequency cap checks not enforcing

**Solution:**
1. Verify StateBackend is configured
2. Check that check_frequency_cap() is called before request()
3. Verify user_id is consistent across requests
4. Check StateBackend logs for errors

### Budget Not Tracking

**Problem:** Budget spend not recorded

**Solution:**
1. Verify track_budget() is called after request()
2. Check StateBackend connectivity
3. Verify campaign_id format
4. Check StateBackend logs

### Timeout Issues

**Problem:** Requests timing out

**Solution:**
1. Increase timeout value
2. Check upstream service status
3. Verify network connectivity
4. Enable retry logic

---

## Summary

Sessions provide a flexible, type-safe way to:

- Maintain state across request chains
- Implement frequency capping
- Track campaign budgets
- Resolve VAST wrappers
- Handle errors gracefully

Start with basic session creation, then add frequency capping and budget tracking as needed.

---

**Next:** See [Stateful Ad Serving](02-stateful-ad-serving.md) for advanced patterns.
