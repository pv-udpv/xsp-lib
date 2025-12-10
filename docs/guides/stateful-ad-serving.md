# Stateful Ad Serving Guide

This guide demonstrates advanced stateful ad serving patterns with xsp-lib, including frequency capping, budget tracking, multi-ad pods (VMAP), and production deployment scenarios.

## Table of Contents

1. [Overview](#overview)
2. [Frequency Capping](#frequency-capping)
3. [Budget Tracking](#budget-tracking)
4. [Multi-Ad Pods (VMAP)](#multi-ad-pods-vmap)
5. [Production Scenarios](#production-scenarios)
6. [Best Practices](#best-practices)

## Overview

**Stateful ad serving** maintains state across multiple ad requests to provide better user experience, comply with advertiser requirements, and optimize campaign performance. xsp-lib's session management system enables sophisticated stateful patterns that are common in production AdTech systems.

### Why Stateful Ad Serving?

| Feature | Business Value | Technical Implementation |
|---------|---------------|--------------------------|
| **Frequency Capping** | Prevent ad fatigue, improve UX | Track impression counts per user/campaign |
| **Budget Tracking** | Protect advertiser spend, maximize ROI | Monitor campaign spend, enforce limits |
| **Ad Pods** | Coordinated multi-ad delivery (VMAP) | Sequence ads within single session |
| **Pacing** | Distribute impressions evenly over time | Track hourly/daily delivery rates |
| **Personalization** | Improve relevance and engagement | Build user profiles across requests |

### Key Patterns

This guide covers three core stateful patterns:

1. **Frequency Capping** - Limit impressions per user/campaign/creative
2. **Budget Tracking** - Monitor and enforce campaign spend limits  
3. **Multi-Ad Pods** - Coordinate multiple ads in a viewing session (VMAP)

## Frequency Capping

Frequency capping limits how often a user sees the same ad or campaign, preventing ad fatigue and improving user experience.

### Frequency Cap Types

| Cap Type | Description | Use Case | Window |
|----------|-------------|----------|--------|
| **Campaign** | Max impressions per campaign | Brand awareness | Daily/Weekly |
| **Creative** | Max impressions per specific ad | Creative testing | Daily |
| **Advertiser** | Max impressions across all campaigns | Overall exposure | Daily |
| **Category** | Max impressions for product category | Avoid saturation | Daily/Weekly |

### Basic Frequency Capping

```python
import asyncio
from decimal import Decimal
from uuid import uuid4
from dataclasses import dataclass, field
from typing import Any

from xsp.core.base import BaseUpstream
from xsp.core.exceptions import XspError
from xsp.transports.http import HttpTransport


class FrequencyCapExceeded(XspError):
    """Raised when frequency cap is exceeded."""
    pass


class FrequencyCapper:
    """Frequency capping enforcement."""
    
    def __init__(
        self,
        backend: StateBackend,
        default_cap: int = 3,
        window_seconds: int = 86400,  # 24 hours
    ):
        self.backend = backend
        self.default_cap = default_cap
        self.window_seconds = window_seconds
    
    async def check_cap(
        self,
        user_id: str,
        campaign_id: str,
        max_impressions: int | None = None,
    ) -> bool:
        """Check if user has exceeded frequency cap."""
        cap = max_impressions or self.default_cap
        key = f"freq_cap:{user_id}:{campaign_id}"
        
        count = await self.backend.get(key)
        if count is None:
            return True  # No impressions yet
        
        return count < cap
    
    async def record_impression(
        self,
        user_id: str,
        campaign_id: str,
    ) -> int:
        """Record impression and return new count."""
        key = f"freq_cap:{user_id}:{campaign_id}"
        
        # Atomic increment
        new_count = await self.backend.increment(key)
        
        # Set TTL on first impression
        if new_count == 1:
            await self.backend.set(key, new_count, ttl=self.window_seconds)
        
        return new_count
    
    async def get_remaining(
        self,
        user_id: str,
        campaign_id: str,
        max_impressions: int | None = None,
    ) -> int:
        """Get remaining impressions before cap."""
        cap = max_impressions or self.default_cap
        key = f"freq_cap:{user_id}:{campaign_id}"
        
        count = await self.backend.get(key) or 0
        remaining = cap - count
        return max(0, remaining)


class FrequencyCappedSessionUpstream(BaseUpstream[str]):
    """Session upstream with frequency capping."""
    
    def __init__(
        self,
        *args,
        frequency_capper: FrequencyCapper,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.frequency_capper = frequency_capper
        self._context = None
        self._session_state = {}
    
    async def start_session(self, context: SessionContext) -> None:
        """Initialize session."""
        self._context = context
        self._session_state = {"request_count": 0}
    
    async def fetch_with_session(
        self,
        campaign_id: str,
        params: dict[str, Any] | None = None,
        **kwargs,
    ) -> str:
        """Fetch with frequency cap check."""
        if not self._context or not self._context.user_id:
            raise XspError("Session context missing user_id")
        
        # Check frequency cap
        can_serve = await self.frequency_capper.check_cap(
            user_id=self._context.user_id,
            campaign_id=campaign_id,
        )
        
        if not can_serve:
            raise FrequencyCapExceeded(
                f"User {self._context.user_id} exceeded cap for campaign {campaign_id}"
            )
        
        # Fetch ad
        result = await self.fetch(params=params, **kwargs)
        
        # Record impression
        await self.frequency_capper.record_impression(
            user_id=self._context.user_id,
            campaign_id=campaign_id,
        )
        
        self._session_state["request_count"] += 1
        
        return result
    
    async def end_session(self) -> None:
        """Clean up session."""
        self._context = None
        self._session_state = {}
        await self.close()
```

### Usage Example

```python
async def serve_with_frequency_cap():
    """Serve ads with frequency capping."""
    from xsp.transports.memory import MemoryTransport
    
    # Setup backend and capper
    backend = MemoryBackend()  # Use RedisBackend in production
    capper = FrequencyCapper(
        backend=backend,
        default_cap=3,  # Max 3 impressions
        window_seconds=86400,  # Per 24 hours
    )
    
    mock_ad = b"<VAST><Ad><InLine><AdTitle>Ad</AdTitle></InLine></Ad></VAST>"
    
    upstream = FrequencyCappedSessionUpstream(
        transport=MemoryTransport(mock_ad),
        decoder=lambda b: b.decode('utf-8'),
        endpoint="memory://vast",
        frequency_capper=capper,
    )
    
    context = SessionContext(
        session_id=str(uuid4()),
        user_id="user_12345",
    )
    
    await upstream.start_session(context)
    
    try:
        # First 3 impressions succeed
        for i in range(3):
            ad = await upstream.fetch_with_session(campaign_id="camp_1")
            remaining = await capper.get_remaining("user_12345", "camp_1")
            print(f"Impression {i+1} served, {remaining} remaining")
        
        # 4th impression fails
        try:
            await upstream.fetch_with_session(campaign_id="camp_1")
        except FrequencyCapExceeded as e:
            print(f"Cap exceeded: {e}")
    
    finally:
        await upstream.end_session()
```

For a complete working example, see **[examples/frequency_capping.py](../../examples/frequency_capping.py)**.

### Advanced: Multi-Level Caps

Implement hierarchical caps (creative → campaign → advertiser):

```python
class MultiLevelFrequencyCapper:
    """Frequency capper with multiple levels."""
    
    def __init__(self, backend: StateBackend):
        self.backend = backend
        self.caps = {
            "creative": 2,    # Max 2 per creative
            "campaign": 5,    # Max 5 per campaign
            "advertiser": 10, # Max 10 per advertiser
        }
    
    async def check_all_caps(
        self,
        user_id: str,
        creative_id: str,
        campaign_id: str,
        advertiser_id: str,
    ) -> tuple[bool, str]:
        """Check all cap levels.
        
        Returns:
            (can_serve, reason) tuple
        """
        # Check creative cap
        creative_count = await self._get_count(user_id, "creative", creative_id)
        if creative_count >= self.caps["creative"]:
            return False, f"Creative cap exceeded ({creative_count}/{self.caps['creative']})"
        
        # Check campaign cap
        campaign_count = await self._get_count(user_id, "campaign", campaign_id)
        if campaign_count >= self.caps["campaign"]:
            return False, f"Campaign cap exceeded ({campaign_count}/{self.caps['campaign']})"
        
        # Check advertiser cap
        advertiser_count = await self._get_count(user_id, "advertiser", advertiser_id)
        if advertiser_count >= self.caps["advertiser"]:
            return False, f"Advertiser cap exceeded ({advertiser_count}/{self.caps['advertiser']})"
        
        return True, "OK"
    
    async def record_all_impressions(
        self,
        user_id: str,
        creative_id: str,
        campaign_id: str,
        advertiser_id: str,
    ) -> None:
        """Record impression at all levels."""
        await self._increment_count(user_id, "creative", creative_id)
        await self._increment_count(user_id, "campaign", campaign_id)
        await self._increment_count(user_id, "advertiser", advertiser_id)
    
    async def _get_count(self, user_id: str, level: str, entity_id: str) -> int:
        key = f"freq_cap:{level}:{user_id}:{entity_id}"
        return await self.backend.get(key) or 0
    
    async def _increment_count(self, user_id: str, level: str, entity_id: str) -> int:
        key = f"freq_cap:{level}:{user_id}:{entity_id}"
        new_count = await self.backend.increment(key)
        if new_count == 1:
            await self.backend.set(key, new_count, ttl=86400)  # 24h
        return new_count
```

## Budget Tracking

Budget tracking monitors campaign spend and enforces budget limits, protecting advertiser ROI.

### Budget Tracking Concepts

| Concept | Description | Implementation |
|---------|-------------|----------------|
| **Total Budget** | Maximum spend allowed | Set at campaign creation |
| **Spent** | Amount consumed so far | Incremented on each impression |
| **Remaining** | Budget left to spend | Calculated: total - spent |
| **Pacing** | Rate of spend over time | Track hourly/daily rates |

### Basic Budget Tracking

```python
from decimal import Decimal


class BudgetExceeded(XspError):
    """Raised when campaign budget is exceeded."""
    pass


class BudgetTracker:
    """Track campaign budget and spend."""
    
    def __init__(self, backend: StateBackend):
        self.backend = backend
    
    async def set_budget(
        self,
        campaign_id: str,
        budget: Decimal,
        currency: str = "USD",
    ) -> None:
        """Set campaign budget."""
        key = f"budget:{campaign_id}"
        await self.backend.set(key, {
            "total": float(budget),
            "spent": 0.0,
            "remaining": float(budget),
            "currency": currency,
            "impressions": 0,
        })
    
    async def record_spend(
        self,
        campaign_id: str,
        amount: Decimal,
        impressions: int = 1,
    ) -> dict[str, Any]:
        """Record spend and return updated budget."""
        key = f"budget:{campaign_id}"
        budget = await self.backend.get(key)
        
        if budget is None:
            raise ValueError(f"No budget set for campaign {campaign_id}")
        
        new_spent = budget["spent"] + float(amount)
        new_remaining = budget["total"] - new_spent
        
        if new_remaining < 0:
            raise BudgetExceeded(
                f"Campaign {campaign_id} budget exceeded: "
                f"attempted ${amount:.2f}, "
                f"remaining ${budget['remaining']:.2f}"
            )
        
        updated = {
            "total": budget["total"],
            "spent": new_spent,
            "remaining": new_remaining,
            "currency": budget["currency"],
            "impressions": budget["impressions"] + impressions,
        }
        
        await self.backend.set(key, updated)
        return updated
    
    async def get_remaining(self, campaign_id: str) -> Decimal:
        """Get remaining budget."""
        key = f"budget:{campaign_id}"
        budget = await self.backend.get(key)
        
        if budget is None:
            return Decimal("0")
        
        return Decimal(str(budget["remaining"]))
    
    async def check_available(
        self,
        campaign_id: str,
        required_amount: Decimal,
    ) -> bool:
        """Check if budget is available."""
        remaining = await self.get_remaining(campaign_id)
        return remaining >= required_amount


class BudgetTrackedSessionUpstream(BaseUpstream[str]):
    """Session upstream with budget tracking."""
    
    def __init__(
        self,
        *args,
        budget_tracker: BudgetTracker,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.budget_tracker = budget_tracker
        self._context = None
        self._session_state = {}
    
    async def start_session(self, context: SessionContext) -> None:
        """Initialize session."""
        self._context = context
        self._session_state = {"total_spend": Decimal("0")}
    
    async def fetch_with_session(
        self,
        campaign_id: str,
        cost: Decimal,
        params: dict[str, Any] | None = None,
        **kwargs,
    ) -> str:
        """Fetch ad with budget check."""
        if not self._context:
            raise XspError("Session not started")
        
        # Check budget availability
        available = await self.budget_tracker.check_available(campaign_id, cost)
        
        if not available:
            budget = await self.budget_tracker.get_budget(campaign_id)
            raise BudgetExceeded(
                f"Insufficient budget for campaign {campaign_id}: "
                f"need ${cost:.2f}, remaining ${budget['remaining']:.2f}"
            )
        
        # Fetch ad
        result = await self.fetch(params=params, **kwargs)
        
        # Record spend
        await self.budget_tracker.record_spend(
            campaign_id=campaign_id,
            amount=cost,
            impressions=1,
        )
        
        # Update session state
        current_spend = self._session_state.get("total_spend", Decimal("0"))
        self._session_state["total_spend"] = current_spend + cost
        
        return result
    
    async def end_session(self) -> None:
        """Clean up session."""
        self._context = None
        self._session_state = {}
        await self.close()
```

### Usage Example

```python
async def serve_with_budget_tracking():
    """Serve ads with budget tracking."""
    from xsp.transports.memory import MemoryTransport
    
    backend = MemoryBackend()
    tracker = BudgetTracker(backend)
    
    # Set campaign budget
    await tracker.set_budget("camp_1", Decimal("100.00"))
    
    mock_ad = b"<VAST><Ad><InLine><AdTitle>Ad</AdTitle></InLine></Ad></VAST>"
    
    upstream = BudgetTrackedSessionUpstream(
        transport=MemoryTransport(mock_ad),
        decoder=lambda b: b.decode('utf-8'),
        endpoint="memory://vast",
        budget_tracker=tracker,
    )
    
    context = SessionContext(session_id=str(uuid4()))
    await upstream.start_session(context)
    
    try:
        # Serve ads with CPM pricing
        cpm = Decimal("5.00")  # $5 CPM
        cost_per_impression = cpm / Decimal("1000")
        
        for i in range(10):
            try:
                await upstream.fetch_with_session(
                    campaign_id="camp_1",
                    cost=cost_per_impression,
                )
                remaining = await tracker.get_remaining("camp_1")
                print(f"Impression {i+1}: remaining ${remaining:.2f}")
            
            except BudgetExceeded:
                print(f"Budget exhausted after {i} impressions")
                break
    
    finally:
        await upstream.end_session()
```

For a complete working example, see **[examples/budget_tracking.py](../../examples/budget_tracking.py)**.

### Advanced: Budget Pacing

Implement budget pacing to distribute spend evenly over time:

```python
class BudgetPacer:
    """Budget pacing to distribute spend over time."""
    
    def __init__(
        self,
        backend: StateBackend,
        target_daily_spend: Decimal,
        hours_per_day: int = 24,
    ):
        self.backend = backend
        self.target_daily_spend = target_daily_spend
        self.hourly_target = target_daily_spend / Decimal(str(hours_per_day))
    
    async def should_serve(
        self,
        campaign_id: str,
        cost: Decimal,
    ) -> tuple[bool, str]:
        """Check if ad should be served based on pacing.
        
        Returns:
            (should_serve, reason) tuple
        """
        import time
        from datetime import datetime
        
        # Get current hour spend
        current_hour = datetime.now().hour
        hour_key = f"pacing:{campaign_id}:{current_hour}"
        hour_spend = await self.backend.get(hour_key) or Decimal("0")
        
        # Check if adding this cost would exceed hourly target
        new_hour_spend = Decimal(str(hour_spend)) + cost
        
        if new_hour_spend > self.hourly_target:
            return False, f"Hourly pacing limit reached (${hour_spend:.2f}/${self.hourly_target:.2f})"
        
        return True, "OK"
    
    async def record_spend(
        self,
        campaign_id: str,
        cost: Decimal,
    ) -> None:
        """Record spend for pacing."""
        from datetime import datetime
        
        current_hour = datetime.now().hour
        hour_key = f"pacing:{campaign_id}:{current_hour}"
        
        current = await self.backend.get(hour_key) or Decimal("0")
        new_spend = Decimal(str(current)) + cost
        
        # Set with TTL of 2 hours to allow for cleanup
        await self.backend.set(hour_key, float(new_spend), ttl=7200)
```

## Multi-Ad Pods (VMAP)

Multi-ad pods coordinate delivery of multiple ads in a single viewing session, typically used for video content.

### VMAP Concepts

**VMAP** (Video Multiple Ad Playlist) is an IAB standard for scheduling multiple ad breaks:

| Concept | Description | Example |
|---------|-------------|---------|
| **Ad Break** | Scheduled ad opportunity | Pre-roll, mid-roll, post-roll |
| **Ad Pod** | Multiple ads in a single break | 3 ads in mid-roll |
| **Pod Position** | Position within pod | Ad 1 of 3, Ad 2 of 3 |
| **Sequence** | Ordering constraint | Must play in order |

### Basic Ad Pod Management

```python
class AdPodManager:
    """Manage multi-ad pod delivery."""
    
    def __init__(
        self,
        backend: StateBackend,
        max_pod_size: int = 5,
    ):
        self.backend = backend
        self.max_pod_size = max_pod_size
    
    async def create_pod(
        self,
        session_id: str,
        pod_id: str,
        pod_size: int,
    ) -> None:
        """Initialize ad pod tracking."""
        if pod_size > self.max_pod_size:
            raise ValueError(f"Pod size {pod_size} exceeds max {self.max_pod_size}")
        
        key = f"pod:{session_id}:{pod_id}"
        await self.backend.set(key, {
            "pod_size": pod_size,
            "delivered": 0,
            "positions_filled": [],
        }, ttl=3600)
    
    async def record_position(
        self,
        session_id: str,
        pod_id: str,
        position: int,
        creative_id: str,
    ) -> dict[str, Any]:
        """Record ad delivered at position."""
        key = f"pod:{session_id}:{pod_id}"
        pod = await self.backend.get(key)
        
        if pod is None:
            raise ValueError(f"Pod {pod_id} not found")
        
        if position in pod["positions_filled"]:
            raise ValueError(f"Position {position} already filled")
        
        pod["positions_filled"].append(position)
        pod["delivered"] = len(pod["positions_filled"])
        
        await self.backend.set(key, pod, ttl=3600)
        return pod
    
    async def get_pod_status(
        self,
        session_id: str,
        pod_id: str,
    ) -> dict[str, Any]:
        """Get pod delivery status."""
        key = f"pod:{session_id}:{pod_id}"
        return await self.backend.get(key)


class AdPodSessionUpstream(BaseUpstream[str]):
    """Session upstream for ad pod delivery."""
    
    def __init__(
        self,
        *args,
        pod_manager: AdPodManager,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.pod_manager = pod_manager
        self._context = None
        self._session_state = {}
    
    async def start_session(self, context: SessionContext) -> None:
        """Initialize session."""
        self._context = context
        self._session_state = {"pods_delivered": 0}
    
    async def fetch_ad_pod(
        self,
        pod_id: str,
        pod_size: int,
        params: dict[str, Any] | None = None,
    ) -> list[str]:
        """Fetch multiple ads for ad pod."""
        if not self._context:
            raise XspError("Session not started")
        
        # Create pod tracking
        await self.pod_manager.create_pod(
            self._context.session_id,
            pod_id,
            pod_size,
        )
        
        ads: list[str] = []
        
        # Fetch each ad in pod
        for position in range(1, pod_size + 1):
            # Add position to params
            pod_params = {**(params or {}), "pod_position": str(position)}
            
            # Fetch ad
            ad = await self.fetch(params=pod_params)
            ads.append(ad)
            
            # Record position filled
            await self.pod_manager.record_position(
                self._context.session_id,
                pod_id,
                position,
                f"creative_{position}",  # Would be actual creative ID
            )
        
        self._session_state["pods_delivered"] = (
            self._session_state.get("pods_delivered", 0) + 1
        )
        
        return ads
    
    async def end_session(self) -> None:
        """Clean up session."""
        self._context = None
        self._session_state = {}
        await self.close()
```

### Usage Example

```python
async def serve_ad_pod():
    """Serve multi-ad pod."""
    from xsp.transports.memory import MemoryTransport
    
    backend = MemoryBackend()
    pod_manager = AdPodManager(backend, max_pod_size=5)
    
    mock_ad = b"<VAST><Ad><InLine><AdTitle>Pod Ad</AdTitle></InLine></Ad></VAST>"
    
    upstream = AdPodSessionUpstream(
        transport=MemoryTransport(mock_ad),
        decoder=lambda b: b.decode('utf-8'),
        endpoint="memory://vast",
        pod_manager=pod_manager,
    )
    
    context = SessionContext(
        session_id=str(uuid4()),
        metadata={"content_duration": 600}  # 10 minutes
    )
    
    await upstream.start_session(context)
    
    try:
        # Fetch 3-ad pod for mid-roll
        ads = await upstream.fetch_ad_pod(
            pod_id="midroll_1",
            pod_size=3,
            params={"content_id": "video_123"}
        )
        
        print(f"Fetched {len(ads)} ads for pod")
        
        # Check pod status
        status = await pod_manager.get_pod_status(
            context.session_id,
            "midroll_1"
        )
        print(f"Pod status: {status['delivered']}/{status['pod_size']} delivered")
    
    finally:
        await upstream.end_session()
```

## Production Scenarios

### Scenario 1: Combined Frequency Cap + Budget Tracking

Real production systems use both frequency capping and budget tracking together:

```python
class ProductionAdServer:
    """Production ad server with all stateful features."""
    
    def __init__(
        self,
        backend: StateBackend,
        frequency_capper: FrequencyCapper,
        budget_tracker: BudgetTracker,
    ):
        self.backend = backend
        self.frequency_capper = frequency_capper
        self.budget_tracker = budget_tracker
    
    async def serve_ad(
        self,
        user_id: str,
        campaign_id: str,
        cost: Decimal,
    ) -> tuple[bool, str, Any]:
        """Serve ad with all checks.
        
        Returns:
            (success, reason, ad_data) tuple
        """
        # Check frequency cap
        can_serve_freq = await self.frequency_capper.check_cap(
            user_id,
            campaign_id,
        )
        
        if not can_serve_freq:
            count = await self.frequency_capper.get_count(user_id, campaign_id)
            return False, f"Frequency cap exceeded ({count})", None
        
        # Check budget
        can_serve_budget = await self.budget_tracker.check_available(
            campaign_id,
            cost,
        )
        
        if not can_serve_budget:
            remaining = await self.budget_tracker.get_remaining(campaign_id)
            return False, f"Budget insufficient (${remaining:.2f})", None
        
        # Serve ad (placeholder)
        ad_data = {"campaign_id": campaign_id, "creative_id": "123"}
        
        # Record impression and spend
        await self.frequency_capper.record_impression(user_id, campaign_id)
        await self.budget_tracker.record_spend(campaign_id, cost)
        
        return True, "OK", ad_data


async def production_example():
    """Production ad serving example."""
    backend = MemoryBackend()  # Use RedisBackend in production
    
    capper = FrequencyCapper(backend, default_cap=3)
    tracker = BudgetTracker(backend)
    
    await tracker.set_budget("camp_1", Decimal("100.00"))
    
    server = ProductionAdServer(backend, capper, tracker)
    
    # Simulate ad requests
    for i in range(10):
        success, reason, ad_data = await server.serve_ad(
            user_id="user_12345",
            campaign_id="camp_1",
            cost=Decimal("2.00"),
        )
        
        if success:
            print(f"Request {i+1}: ✓ Served")
        else:
            print(f"Request {i+1}: ✗ Blocked - {reason}")
```

### Scenario 2: Redis with TTL and Error Recovery

Production systems need robust error handling and state recovery:

```python
import aioredis
import json
from typing import Any


class RedisBackend:
    """Production Redis backend with error handling."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        max_retries: int = 3,
    ):
        url = f"redis://{host}:{port}/{db}"
        if password:
            url = f"redis://:{password}@{host}:{port}/{db}"
        
        self.redis = aioredis.from_url(url, decode_responses=False)
        self.max_retries = max_retries
    
    async def get(self, key: str) -> Any | None:
        """Get value with retry logic."""
        for attempt in range(self.max_retries):
            try:
                value = await self.redis.get(key)
                if value is None:
                    return None
                return json.loads(value)
            
            except aioredis.RedisError as e:
                if attempt == self.max_retries - 1:
                    # Log error
                    print(f"Redis GET error after {self.max_retries} attempts: {e}")
                    return None  # Fail gracefully
                
                await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
        
        return None
    
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value with retry logic."""
        for attempt in range(self.max_retries):
            try:
                serialized = json.dumps(value)
                if ttl:
                    await self.redis.setex(key, ttl, serialized)
                else:
                    await self.redis.set(key, serialized)
                return
            
            except aioredis.RedisError as e:
                if attempt == self.max_retries - 1:
                    # Log error
                    print(f"Redis SET error after {self.max_retries} attempts: {e}")
                    raise  # Re-raise on final attempt
                
                await asyncio.sleep(0.1 * (attempt + 1))
    
    async def increment(self, key: str, delta: int = 1) -> int:
        """Atomically increment counter with retry logic."""
        for attempt in range(self.max_retries):
            try:
                return await self.redis.incrby(key, delta)
            
            except aioredis.RedisError as e:
                if attempt == self.max_retries - 1:
                    print(f"Redis INCR error after {self.max_retries} attempts: {e}")
                    # Return fallback value
                    return 0
                
                await asyncio.sleep(0.1 * (attempt + 1))
        
        return 0
    
    async def close(self) -> None:
        """Close Redis connection."""
        await self.redis.close()
```

### Scenario 3: Monitoring and Alerting

Production systems need comprehensive monitoring:

```python
import time
from typing import Any


class MonitoredAdServer(ProductionAdServer):
    """Ad server with monitoring."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metrics = {
            "requests": 0,
            "served": 0,
            "freq_cap_blocks": 0,
            "budget_blocks": 0,
            "errors": 0,
        }
    
    async def serve_ad(
        self,
        user_id: str,
        campaign_id: str,
        cost: Decimal,
    ) -> tuple[bool, str, Any]:
        """Serve ad with metrics tracking."""
        self.metrics["requests"] += 1
        start_time = time.time()
        
        try:
            success, reason, ad_data = await super().serve_ad(
                user_id,
                campaign_id,
                cost,
            )
            
            if success:
                self.metrics["served"] += 1
            elif "Frequency cap" in reason:
                self.metrics["freq_cap_blocks"] += 1
            elif "Budget" in reason:
                self.metrics["budget_blocks"] += 1
            
            # Record latency
            latency = time.time() - start_time
            await self._record_metric("ad_serve_latency", latency)
            
            return success, reason, ad_data
        
        except Exception as e:
            self.metrics["errors"] += 1
            print(f"Error serving ad: {e}")
            raise
    
    async def _record_metric(self, name: str, value: float) -> None:
        """Record metric to monitoring system."""
        # Send to Prometheus, StatsD, CloudWatch, etc.
        print(f"METRIC: {name} = {value:.3f}")
    
    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics."""
        metrics = self.metrics.copy()
        
        if metrics["requests"] > 0:
            metrics["serve_rate"] = metrics["served"] / metrics["requests"]
            metrics["freq_cap_block_rate"] = metrics["freq_cap_blocks"] / metrics["requests"]
            metrics["budget_block_rate"] = metrics["budget_blocks"] / metrics["requests"]
        
        return metrics
```

## Best Practices

### 1. Use Redis in Production

```python
# ✅ Good: Production with Redis
backend = RedisBackend(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD"),
    max_retries=3,
)

# ❌ Bad: In-memory backend in production
backend = MemoryBackend()  # Only for testing!
```

### 2. Set Appropriate TTLs

```python
# ✅ Good: TTLs match business rules
await backend.set(
    f"freq_cap:{user_id}:{campaign_id}",
    count,
    ttl=86400  # 24 hours for daily cap
)

await backend.set(
    f"session:{session_id}",
    state,
    ttl=3600  # 1 hour for active session
)

# ❌ Bad: No TTL (memory leak)
await backend.set(key, value)  # Never expires!
```

### 3. Handle Failures Gracefully

```python
# ✅ Good: Graceful degradation
try:
    can_serve = await frequency_capper.check_cap(user_id, campaign_id)
except Exception as e:
    # Log error
    print(f"Frequency cap check failed: {e}")
    # Allow ad to serve (fail open)
    can_serve = True

# ❌ Bad: Hard failure
can_serve = await frequency_capper.check_cap(user_id, campaign_id)
# Raises exception if Redis down - no ad served
```

### 4. Use Atomic Operations

```python
# ✅ Good: Atomic increment
count = await backend.increment(key)

# ❌ Bad: Read-modify-write (race condition)
count = await backend.get(key) or 0
count += 1
await backend.set(key, count)
```

### 5. Monitor Everything

```python
# ✅ Good: Comprehensive monitoring
metrics = {
    "requests": 0,
    "served": 0,
    "blocked_freq_cap": 0,
    "blocked_budget": 0,
    "errors": 0,
    "latency_p50": 0,
    "latency_p95": 0,
    "latency_p99": 0,
}

# Record all important events
await record_metric("ad_request", labels={"campaign": campaign_id})
await record_metric("freq_cap_check_latency", latency_ms)
```

### 6. Test Failure Scenarios

```python
@pytest.mark.asyncio
async def test_redis_failure_recovery():
    """Test behavior when Redis fails."""
    backend = RedisBackend(host="nonexistent_host")
    capper = FrequencyCapper(backend)
    
    # Should fail gracefully, not crash
    can_serve = await capper.check_cap("user_1", "camp_1")
    
    # System should still function (possibly with degraded behavior)
    assert can_serve in [True, False]
```

### 7. Use Decimal for Money

```python
# ✅ Good: Decimal for currency
cost = Decimal("2.50")
total = cost * Decimal("1000")

# ❌ Bad: Float for currency (rounding errors)
cost = 2.50  # Will accumulate rounding errors
```

### 8. Document State Schema

```python
# ✅ Good: Documented schema
"""
Budget state schema:
{
    "total": float,         # Total budget
    "spent": float,         # Amount spent
    "remaining": float,     # Remaining budget
    "currency": str,        # Currency code
    "impressions": int,     # Total impressions
    "last_updated": float,  # Unix timestamp
}
"""
```

## Related Documentation

- **[Session Management Guide](./session-management.md)** - Session fundamentals and lifecycle
- **[Architecture: Session Management](../architecture/session-management.md)** - Technical architecture
- **[Examples: Session Management](../../examples/session_management.py)** - Working examples
- **[Examples: Frequency Capping](../../examples/frequency_capping.py)** - Frequency cap examples
- **[Examples: Budget Tracking](../../examples/budget_tracking.py)** - Budget tracking examples

## Summary

Stateful ad serving with xsp-lib enables:

- **Frequency Capping**: Prevent ad fatigue with impression limits
- **Budget Tracking**: Protect advertiser spend with budget enforcement
- **Ad Pods**: Coordinate multi-ad delivery for video content
- **Production Ready**: Redis backend, error handling, monitoring
- **Best Practices**: Atomic operations, appropriate TTLs, graceful degradation

For hands-on learning:
1. Run **[examples/frequency_capping.py](../../examples/frequency_capping.py)** for frequency cap patterns
2. Run **[examples/budget_tracking.py](../../examples/budget_tracking.py)** for budget management
3. Review production scenarios in this guide
4. Read **[session-management.md](./session-management.md)** for session fundamentals

---

**Document Version**: 1.0  
**Last Updated**: 2025-12-10  
**Status**: Production Ready
