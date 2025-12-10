# Stateful Ad Serving Guide

This guide demonstrates how to implement stateful ad serving with frequency capping and budget tracking using xsp-lib's `UpstreamSession` protocol.

## Table of Contents

- [Overview](#overview)
- [Frequency Capping](#frequency-capping)
- [Budget Tracking](#budget-tracking)
- [Complete Implementation](#complete-implementation)
- [Production Patterns](#production-patterns)
- [Performance Optimization](#performance-optimization)

## Overview

Stateful ad serving enables:
- **Frequency Capping** - Limit ad impressions per user per time period
- **Budget Tracking** - Monitor campaign spend in real-time
- **Pacing** - Control ad delivery rate
- **User Preferences** - Remember user opt-outs and preferences

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│               Application Layer                         │
│  (Ad Server, SSP, Frequency Cap Enforcement)           │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│           UpstreamSession (Redis-backed)                │
│  • check_frequency_cap(user_id, campaign_id)           │
│  • track_budget(campaign_id, cost)                     │
│  • request(context, **kwargs)                          │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│                 Redis (State Store)                     │
│  freq:{user_id}:{campaign_id} → impression_count       │
│  budget:{campaign_id} → total_spent                    │
│  budget:limit:{campaign_id} → budget_limit             │
└─────────────────────────────────────────────────────────┘
```

## Frequency Capping

### Basic Frequency Cap

Limit users to 3 impressions per campaign per hour:

```python
from decimal import Decimal
from typing import Any
from xsp.core.session import SessionContext, UpstreamSession
from xsp.core.upstream import Upstream
from redis.asyncio import Redis

class FrequencyCappedSession:
    """Frequency capping for ad delivery."""
    
    def __init__(
        self,
        upstream: Upstream,
        redis_client: Redis,
        max_impressions: int = 3,
        window_seconds: int = 3600,
    ):
        self._upstream = upstream
        self._redis = redis_client
        self._max_impressions = max_impressions
        self._window = window_seconds
    
    async def check_frequency_cap(
        self,
        user_id: str,
        campaign_id: str,
    ) -> bool:
        """Check if user can receive ad."""
        key = f"freq:{user_id}:{campaign_id}"
        count = await self._redis.get(key)
        
        if count is None:
            return True  # First impression
        
        return int(count) < self._max_impressions
    
    async def increment_frequency(
        self,
        user_id: str,
        campaign_id: str,
    ) -> None:
        """Increment impression counter."""
        key = f"freq:{user_id}:{campaign_id}"
        
        # Use pipeline for atomic operation
        async with self._redis.pipeline() as pipe:
            pipe.incr(key)
            pipe.expire(key, self._window)
            await pipe.execute()
    
    async def request(
        self,
        context: SessionContext,
        **kwargs: Any,
    ) -> Any:
        """Serve ad with frequency cap enforcement."""
        user_id = context.cookies.get("user_id", "anonymous")
        campaign_id = kwargs.get("params", {}).get("campaign_id", "default")
        
        # Check cap before serving
        if not await self.check_frequency_cap(user_id, campaign_id):
            raise FrequencyCapExceeded(f"User {user_id} exceeded cap for {campaign_id}")
        
        # Serve ad
        response = await self._upstream.fetch(context=context, **kwargs)
        
        # Track impression
        await self.increment_frequency(user_id, campaign_id)
        
        return response
```

### Usage Example

```python
from redis.asyncio import Redis
from xsp.core.session import SessionContext

# Initialize
redis = Redis(host="localhost", port=6379)
session = FrequencyCappedSession(
    upstream=vast_upstream,
    redis_client=redis,
    max_impressions=3,  # Max 3 per hour
    window_seconds=3600,
)

# Serve ad
async def serve_ad(request):
    context = SessionContext.create(cookies=request.cookies)
    user_id = context.cookies.get("user_id", "anonymous")
    
    # Check before serving
    can_serve = await session.check_frequency_cap(user_id, "campaign123")
    
    if not can_serve:
        logger.info(f"Frequency cap hit for user {user_id}")
        return None  # No-fill response
    
    # Serve and track
    return await session.request(
        context=context,
        params={"campaign_id": "campaign123"},
    )
```

### Per-User Per-Campaign Caps

Different caps for different campaigns:

```python
class MultiCampaignFrequencyCap:
    """Frequency caps with per-campaign limits."""
    
    def __init__(self, redis_client: Redis):
        self._redis = redis_client
        # Campaign-specific caps (can be loaded from database)
        self._caps = {
            "campaign_premium": {"max": 5, "window": 86400},  # 5/day
            "campaign_standard": {"max": 3, "window": 3600},  # 3/hour
            "campaign_budget": {"max": 10, "window": 3600},   # 10/hour
        }
    
    async def check_frequency_cap(
        self,
        user_id: str,
        campaign_id: str,
    ) -> bool:
        """Check cap with campaign-specific limits."""
        cap_config = self._caps.get(campaign_id, {"max": 3, "window": 3600})
        
        key = f"freq:{user_id}:{campaign_id}"
        count = await self._redis.get(key)
        
        if count is None:
            return True
        
        return int(count) < cap_config["max"]
    
    async def increment_frequency(
        self,
        user_id: str,
        campaign_id: str,
    ) -> None:
        """Increment with campaign-specific TTL."""
        cap_config = self._caps.get(campaign_id, {"max": 3, "window": 3600})
        key = f"freq:{user_id}:{campaign_id}"
        
        async with self._redis.pipeline() as pipe:
            pipe.incr(key)
            pipe.expire(key, cap_config["window"])
            await pipe.execute()
```

## Budget Tracking

### Real-Time Budget Monitoring

Track campaign spend in real-time:

```python
from decimal import Decimal
from redis.asyncio import Redis

class BudgetTracker:
    """Real-time campaign budget tracking."""
    
    def __init__(self, redis_client: Redis):
        self._redis = redis_client
    
    async def get_campaign_budget(self, campaign_id: str) -> Decimal:
        """Fetch campaign budget limit."""
        budget = await self._redis.get(f"budget:limit:{campaign_id}")
        return Decimal(budget) if budget else Decimal("1000.00")
    
    async def get_spent(self, campaign_id: str) -> Decimal:
        """Get current spend."""
        spent = await self._redis.get(f"budget:{campaign_id}")
        return Decimal(spent) if spent else Decimal("0.00")
    
    async def check_budget(
        self,
        campaign_id: str,
        cost: Decimal,
    ) -> bool:
        """Check if adding cost would exceed budget."""
        budget = await self.get_campaign_budget(campaign_id)
        spent = await self.get_spent(campaign_id)
        
        return spent + cost <= budget
    
    async def track_budget(
        self,
        campaign_id: str,
        cost: Decimal,
    ) -> bool:
        """Track spend and check budget atomically."""
        key = f"budget:{campaign_id}"
        
        # Check budget
        if not await self.check_budget(campaign_id, cost):
            raise BudgetExceeded(f"Campaign {campaign_id} budget exhausted")
        
        # Increment spend
        await self._redis.incrbyfloat(key, float(cost))
        return True
    
    async def get_remaining_budget(self, campaign_id: str) -> Decimal:
        """Get remaining budget."""
        budget = await self.get_campaign_budget(campaign_id)
        spent = await self.get_spent(campaign_id)
        return budget - spent
```

### Usage Example

```python
from decimal import Decimal

# Initialize tracker
tracker = BudgetTracker(redis_client=redis)

# Set campaign budget
await redis.set("budget:limit:campaign123", "1000.00")

# Serve ad and track spend
async def serve_with_budget_tracking(campaign_id: str, cpm: Decimal):
    # Check budget before serving
    cost = cpm / Decimal("1000")  # Cost per impression
    
    if not await tracker.check_budget(campaign_id, cost):
        logger.warning(f"Budget exceeded for {campaign_id}")
        return None
    
    # Serve ad
    response = await upstream.fetch(params={"campaign_id": campaign_id})
    
    # Track spend
    await tracker.track_budget(campaign_id, cost)
    
    # Log remaining budget
    remaining = await tracker.get_remaining_budget(campaign_id)
    logger.info(f"Remaining budget: ${remaining}")
    
    return response
```

## Complete Implementation

Full session implementation with both frequency capping and budget tracking:

```python
from decimal import Decimal
from typing import Any
from xsp.core.session import SessionContext, UpstreamSession
from xsp.core.upstream import Upstream
from redis.asyncio import Redis

class FullUpstreamSession:
    """Complete stateful session with frequency cap and budget tracking."""
    
    def __init__(
        self,
        upstream: Upstream,
        redis_client: Redis,
        frequency_cap: int = 3,
        frequency_window: int = 3600,
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
        """Check frequency cap."""
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
        """Track budget."""
        budget_key = f"budget:limit:{campaign_id}"
        spent_key = f"budget:{campaign_id}"
        
        # Get budget and spent
        budget = Decimal(await self._redis.get(budget_key) or "1000.00")
        spent = Decimal(await self._redis.get(spent_key) or "0.00")
        
        # Check if adding cost exceeds budget
        if spent + cost > budget:
            return False
        
        # Increment spend
        await self._redis.incrbyfloat(spent_key, float(cost))
        return True
    
    async def request(
        self,
        context: SessionContext,
        **kwargs: Any,
    ) -> Any:
        """Execute request with full session state management."""
        # Extract identifiers
        user_id = context.cookies.get("user_id", "anonymous")
        params = kwargs.get("params", {})
        campaign_id = params.get("campaign_id", "default")
        cpm = Decimal(params.get("cpm", "2.00"))
        
        # Check frequency cap
        if not await self.check_frequency_cap(user_id, campaign_id):
            raise FrequencyCapExceeded(
                f"User {user_id} exceeded cap for {campaign_id}"
            )
        
        # Check budget
        cost = cpm / Decimal("1000")  # CPM to cost per impression
        if not await self.track_budget(campaign_id, cost):
            raise BudgetExceeded(f"Campaign {campaign_id} budget exhausted")
        
        # Execute upstream request
        response = await self._upstream.fetch(context=context, **kwargs)
        
        # Track impression (increment frequency counter)
        key = f"freq:{user_id}:{campaign_id}"
        async with self._redis.pipeline() as pipe:
            pipe.incr(key)
            pipe.expire(key, self._frequency_window)
            await pipe.execute()
        
        return response
```

### Usage

```python
from redis.asyncio import Redis
from xsp.core.session import SessionContext

# Initialize
redis = Redis(host="localhost", port=6379, decode_responses=True)
session = FullUpstreamSession(
    upstream=vast_upstream,
    redis_client=redis,
    frequency_cap=3,
    frequency_window=3600,
)

# Set campaign budget
await redis.set("budget:limit:campaign123", "1000.00")

# Serve ad with full session management
async def serve_ad_full_session(request):
    context = SessionContext.create(cookies=request.cookies)
    
    try:
        response = await session.request(
            context=context,
            params={
                "campaign_id": "campaign123",
                "cpm": "5.00",  # $5 CPM
            },
        )
        
        logger.info(
            "Ad served successfully",
            extra={"request_id": context.request_id}
        )
        
        return response
        
    except FrequencyCapExceeded as e:
        logger.info(f"Frequency cap exceeded: {e}")
        return get_default_ad()
        
    except BudgetExceeded as e:
        logger.warning(f"Budget exceeded: {e}")
        await pause_campaign("campaign123")
        return None
```

## Production Patterns

### Graceful Degradation

Handle Redis failures gracefully:

```python
class ResilientSession(FullUpstreamSession):
    """Session with graceful degradation."""
    
    async def check_frequency_cap(
        self,
        user_id: str,
        campaign_id: str,
    ) -> bool:
        """Check frequency cap with fallback."""
        try:
            return await super().check_frequency_cap(user_id, campaign_id)
        except Exception as e:
            logger.error(
                "Frequency cap check failed, allowing request",
                exc_info=True
            )
            return True  # Allow request on Redis failure
    
    async def track_budget(
        self,
        campaign_id: str,
        cost: Decimal,
    ) -> bool:
        """Track budget with fallback."""
        try:
            return await super().track_budget(campaign_id, cost)
        except Exception as e:
            logger.error(
                "Budget tracking failed, allowing request",
                exc_info=True
            )
            return True  # Allow request on Redis failure
```

### Distributed Locking

Use Redis locks for atomic budget checks:

```python
from redis.asyncio import Redis
from redis.lock import Lock

class LockedBudgetTracker(BudgetTracker):
    """Budget tracker with distributed locking."""
    
    async def track_budget(
        self,
        campaign_id: str,
        cost: Decimal,
    ) -> bool:
        """Track budget with distributed lock."""
        lock_key = f"lock:budget:{campaign_id}"
        
        async with self._redis.lock(lock_key, timeout=5):
            # Check budget
            if not await self.check_budget(campaign_id, cost):
                raise BudgetExceeded(f"Campaign {campaign_id} budget exhausted")
            
            # Increment spend atomically
            await self._redis.incrbyfloat(f"budget:{campaign_id}", float(cost))
            return True
```

## Performance Optimization

### Pipeline Operations

Batch Redis commands:

```python
async def request_with_pipeline(
    self,
    context: SessionContext,
    **kwargs: Any,
) -> Any:
    """Request with pipelined Redis operations."""
    user_id = context.cookies.get("user_id", "anonymous")
    campaign_id = kwargs.get("params", {}).get("campaign_id", "default")
    
    # Execute checks in pipeline
    async with self._redis.pipeline() as pipe:
        # Get frequency count
        pipe.get(f"freq:{user_id}:{campaign_id}")
        # Get budget spent
        pipe.get(f"budget:{campaign_id}")
        # Get budget limit
        pipe.get(f"budget:limit:{campaign_id}")
        
        results = await pipe.execute()
    
    # Parse results
    freq_count = int(results[0] or 0)
    spent = Decimal(results[1] or "0.00")
    budget = Decimal(results[2] or "1000.00")
    
    # Check constraints
    if freq_count >= self._frequency_cap:
        raise FrequencyCapExceeded(...)
    
    cost = Decimal(kwargs.get("params", {}).get("cpm", "2.00")) / Decimal("1000")
    if spent + cost > budget:
        raise BudgetExceeded(...)
    
    # Serve ad and track in pipeline
    response = await self._upstream.fetch(context=context, **kwargs)
    
    async with self._redis.pipeline() as pipe:
        pipe.incr(f"freq:{user_id}:{campaign_id}")
        pipe.expire(f"freq:{user_id}:{campaign_id}", self._frequency_window)
        pipe.incrbyfloat(f"budget:{campaign_id}", float(cost))
        await pipe.execute()
    
    return response
```

### Caching Campaign Budgets

Cache budget limits to reduce Redis reads:

```python
from functools import lru_cache
from typing import Optional

class CachedBudgetTracker(BudgetTracker):
    """Budget tracker with in-memory cache."""
    
    @lru_cache(maxsize=1000)
    async def get_campaign_budget_cached(self, campaign_id: str) -> Decimal:
        """Get budget with caching."""
        return await self.get_campaign_budget(campaign_id)
    
    async def check_budget(
        self,
        campaign_id: str,
        cost: Decimal,
    ) -> bool:
        """Check budget using cached limit."""
        budget = await self.get_campaign_budget_cached(campaign_id)
        spent = await self.get_spent(campaign_id)
        return spent + cost <= budget
```

## Related Documentation

- [Session Management Guide](./session-management.md)
- [Session Management Architecture](../architecture/session-management.md)
- [Final Architecture](../architecture/final-architecture.md)
