# Stateful Ad Serving Patterns

**Version:** 1.0  
**Date:** December 10, 2025  
**For:** Production Architects  

## Overview

Stateful ad serving maintains session state across multiple requests in a distributed system:

```
Request 1: Check cap, serve ad
Request 2: Check cap, serve ad (same user)
Request 3: Check cap, hit limit (same user)
Request 4: Try fallback (same user)
```

---

## Session Lifecycle in Production

### Session Creation

```python
class SessionFactory:
    def __init__(
        self,
        upstream: VastUpstream,
        state_backend: StateBackend,
        logger: Logger,
    ):
        self.upstream = upstream
        self.state_backend = state_backend
        self.logger = logger
    
    async def create_session(
        self,
        user_id: str,
        device_id: str,
        publisher_id: str,
    ) -> UpstreamSession:
        """Create new session for user."""
        context = SessionContext(
            timestamp=int(time.time() * 1000),
            correlator=f"{user_id}:{device_id}:{int(time.time())}",
            cachebusting=secrets.token_hex(8),
            cookies={
                "uid": user_id,
                "device_id": device_id,
                "publisher_id": publisher_id,
            },
            request_id=str(uuid.uuid4()),
        )
        
        # Log session creation
        self.logger.info(
            f"Creating session",
            extra={
                "user_id": user_id,
                "request_id": context.request_id,
            },
        )
        
        session = await self.upstream.create_session(
            context,
            state_backend=self.state_backend,
        )
        
        return session
```

### Session Operation

```python
class SessionOperator:
    async def serve_ad(
        self,
        session: UpstreamSession,
        campaign_id: str,
        budget_limit: float,
        frequency_cap: int = 3,
    ) -> Optional[VastResponse]:
        """Serve ad with state checks."""
        
        user_id = session.context.cookies.get("uid")
        request_id = session.context.request_id
        
        # Check frequency cap
        if not await session.check_frequency_cap(
            user_id=user_id,
            limit=frequency_cap,
        ):
            logger.info(
                f"Frequency cap exceeded",
                extra={"user_id": user_id, "request_id": request_id},
            )
            return None
        
        # Fetch ad
        try:
            ad = await session.request()
        except UpstreamError as e:
            logger.error(
                f"Upstream error",
                extra={"error": str(e), "request_id": request_id},
            )
            return None
        
        # Track budget
        try:
            await session.track_budget(campaign_id, amount=2.50)
        except StateBackendError:
            # Budget tracking failed but ad was served
            logger.warning(
                f"Budget tracking failed",
                extra={"campaign_id": campaign_id, "request_id": request_id},
            )
        
        return ad
```

### Session Cleanup

```python
class SessionManager:
    async def __aenter__(self) -> UpstreamSession:
        self.session = await self.factory.create_session(...)
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            await self.session.close()
        except Exception as e:
            # Log cleanup errors but don't raise
            logger.error(f"Session cleanup failed: {e}")
```

---

## Concurrent Session Handling

### Multiple Users

```python
async def serve_multiple_users(
    user_ids: list[str],
) -> dict[str, Optional[str]]:
    """Serve ads for multiple users concurrently."""
    tasks = []
    
    for user_id in user_ids:
        task = serve_single_user(user_id)
        tasks.append(task)
    
    # Serve all concurrently
    results = await asyncio.gather(*tasks)
    
    return dict(zip(user_ids, results))

async def serve_single_user(user_id: str) -> Optional[str]:
    """Serve single user with independent session."""
    session = await factory.create_session(user_id)
    
    try:
        if await session.check_frequency_cap(user_id):
            return await session.request()
    finally:
        await session.close()
```

### Rate Limiting

```python
class RateLimiter:
    def __init__(self, max_requests_per_second: float = 100):
        self.max_requests = max_requests_per_second
        self.semaphore = asyncio.Semaphore(int(max_requests_per_second))
    
    async def acquire(self):
        async with self.semaphore:
            yield

rate_limiter = RateLimiter(max_requests_per_second=100)

async def serve_with_rate_limit(user_id: str) -> Optional[str]:
    async with rate_limiter.acquire():
        session = await factory.create_session(user_id)
        try:
            return await session.request()
        finally:
            await session.close()
```

---

## Fallback Strategies

### Primary/Fallback Pattern

```python
class UpstreamSelector:
    def __init__(
        self,
        primary: VastUpstream,
        fallback1: VastUpstream,
        fallback2: VastUpstream,
    ):
        self.primary = primary
        self.fallback1 = fallback1
        self.fallback2 = fallback2
    
    async def serve_with_fallback(
        self,
        user_id: str,
    ) -> Optional[str]:
        """Try primary, then fallbacks."""
        
        # Try primary
        try:
            session = await self.primary.create_session(context)
            ad = await session.request()
            await session.close()
            logger.info(f"Served from primary: {user_id}")
            return ad
        except Exception as e:
            logger.warning(f"Primary failed: {e}")
        
        # Try fallback 1
        try:
            session = await self.fallback1.create_session(context)
            ad = await session.request()
            await session.close()
            logger.info(f"Served from fallback1: {user_id}")
            return ad
        except Exception as e:
            logger.warning(f"Fallback1 failed: {e}")
        
        # Try fallback 2
        try:
            session = await self.fallback2.create_session(context)
            ad = await session.request()
            await session.close()
            logger.info(f"Served from fallback2: {user_id}")
            return ad
        except Exception as e:
            logger.warning(f"Fallback2 failed: {e}")
        
        # All failed
        return None
```

### Circuit Breaker Pattern

```python
from pybreaker import CircuitBreaker

class FailureDetector:
    def __init__(self):
        self.breaker = CircuitBreaker(
            fail_max=5,              # Open after 5 failures
            reset_timeout=60,        # Try reset after 60s
        )
    
    async def serve_with_circuit_breaker(
        self,
        upstream: VastUpstream,
    ) -> Optional[str]:
        """Serve with circuit breaker protection."""
        try:
            return await self.breaker.call(
                self._fetch_ad,
                upstream,
            )
        except CircuitBreakerListener:
            logger.warning(f"Circuit breaker open for {upstream}")
            return None
    
    async def _fetch_ad(self, upstream: VastUpstream) -> str:
        session = await upstream.create_session(context)
        try:
            return await session.request()
        finally:
            await session.close()
```

---

## Caching Patterns

### Response Caching

```python
class ResponseCache:
    def __init__(self, ttl_seconds: int = 300):
        self.cache: dict[str, tuple[str, float]] = {}
        self.ttl = ttl_seconds
    
    async def get_or_fetch(
        self,
        cache_key: str,
        fetch_fn,
    ) -> Optional[str]:
        """Get from cache or fetch fresh."""
        now = time.time()
        
        # Check cache
        if cache_key in self.cache:
            response, cached_at = self.cache[cache_key]
            if now - cached_at < self.ttl:
                logger.info(f"Cache hit: {cache_key}")
                return response
        
        # Fetch fresh
        response = await fetch_fn()
        if response:
            self.cache[cache_key] = (response, now)
            logger.info(f"Cache miss, fetched: {cache_key}")
        
        return response

# Usage:
cache = ResponseCache(ttl_seconds=300)

async def serve_with_cache(
    session: UpstreamSession,
    user_id: str,
) -> Optional[str]:
    cache_key = f"vast:{user_id}"
    return await cache.get_or_fetch(
        cache_key,
        lambda: session.request(),
    )
```

---

## Monitoring and Metrics

### Request Metrics

```python
class RequestMetrics:
    def __init__(self):
        self.requests_total = 0
        self.requests_success = 0
        self.requests_failed = 0
        self.requests_capped = 0
        self.total_latency = 0.0
    
    async def track_request(
        self,
        session: UpstreamSession,
    ) -> Optional[str]:
        """Track metrics while serving."""
        start = time.time()
        
        try:
            ad = await session.request()
            self.requests_total += 1
            self.requests_success += 1
            return ad
        except Exception as e:
            self.requests_total += 1
            self.requests_failed += 1
            raise
        finally:
            elapsed = time.time() - start
            self.total_latency += elapsed
    
    def get_stats(self) -> dict:
        """Get current metrics."""
        return {
            "total": self.requests_total,
            "success": self.requests_success,
            "failed": self.requests_failed,
            "success_rate": (
                self.requests_success / self.requests_total
                if self.requests_total > 0
                else 0
            ),
            "avg_latency": (
                self.total_latency / self.requests_total
                if self.requests_total > 0
                else 0
            ),
        }
```

### Budget Metrics

```python
class BudgetMetrics:
    def __init__(self, state_backend: StateBackend):
        self.state_backend = state_backend
    
    async def get_campaign_metrics(
        self,
        campaign_id: str,
        budget_limit: float,
    ) -> dict:
        """Get budget metrics for campaign."""
        current_spend = await self.state_backend.get_spend(
            f"budget:{campaign_id}"
        )
        
        return {
            "campaign_id": campaign_id,
            "spent": current_spend,
            "limit": budget_limit,
            "remaining": budget_limit - current_spend,
            "percentage_spent": (current_spend / budget_limit * 100)
            if budget_limit > 0
            else 0,
        }
```

---

## Database Integration

### StateBackend with Database

```python
class DatabaseStateBackend:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
    
    async def get_count(self, key: str) -> int:
        """Get count from database."""
        async with self.Session() as session:
            result = await session.execute(
                select(FrequencyCap).where(FrequencyCap.key == key)
            )
            row = result.scalar_one_or_none()
            return row.count if row else 0
    
    async def increment(self, key: str) -> int:
        """Increment count in database."""
        async with self.Session() as session:
            result = await session.execute(
                select(FrequencyCap).where(FrequencyCap.key == key)
            )
            row = result.scalar_one_or_none()
            
            if row:
                row.count += 1
            else:
                row = FrequencyCap(key=key, count=1)
                session.add(row)
            
            await session.commit()
            return row.count

# Database models
class FrequencyCap(Base):
    __tablename__ = "frequency_caps"
    
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True)
    count = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=True)

class BudgetTracking(Base):
    __tablename__ = "budget_tracking"
    
    id = Column(Integer, primary_key=True)
    campaign_id = Column(String, index=True)
    spent = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)
```

---

## Real-World Example: Complete Ad Server

```python
class AdServer:
    def __init__(
        self,
        primary_upstream: VastUpstream,
        fallback_upstream: VastUpstream,
        state_backend: StateBackend,
    ):
        self.primary = primary_upstream
        self.fallback = fallback_upstream
        self.state_backend = state_backend
        self.metrics = RequestMetrics()
        self.cache = ResponseCache(ttl_seconds=300)
    
    async def serve_ad(
        self,
        user_id: str,
        device_id: str,
        campaign_id: str,
        budget_limit: float,
        frequency_cap: int = 3,
    ) -> Optional[str]:
        """Complete ad serving flow."""
        
        request_id = str(uuid.uuid4())
        logger.info(
            f"Ad request",
            extra={
                "user_id": user_id,
                "campaign_id": campaign_id,
                "request_id": request_id,
            },
        )
        
        # Try cache first
        cache_key = f"vast:{user_id}:{campaign_id}"
        cached = self.cache.cache.get(cache_key)
        if cached:
            return cached[0]
        
        # Create session
        context = SessionContext(
            timestamp=int(time.time() * 1000),
            correlator=f"{user_id}:{device_id}",
            cachebusting=secrets.token_hex(8),
            cookies={"uid": user_id},
            request_id=request_id,
        )
        
        # Try primary upstream
        try:
            session = await self.primary.create_session(
                context,
                state_backend=self.state_backend,
            )
            
            # Check frequency cap
            if not await session.check_frequency_cap(
                user_id=user_id,
                limit=frequency_cap,
            ):
                logger.info(
                    f"Frequency cap exceeded",
                    extra={"user_id": user_id, "request_id": request_id},
                )
                return None
            
            # Fetch ad
            ad = await self.metrics.track_request(session)
            
            # Track budget
            await session.track_budget(campaign_id, 2.50)
            
            # Cache result
            self.cache.cache[cache_key] = (ad, time.time())
            
            logger.info(
                f"Ad served from primary",
                extra={
                    "user_id": user_id,
                    "request_id": request_id,
                    "campaign_id": campaign_id,
                },
            )
            
            return ad
        
        except Exception as e:
            logger.warning(
                f"Primary failed: {e}",
                extra={"request_id": request_id},
            )
        
        finally:
            await session.close()
        
        # Try fallback
        try:
            session = await self.fallback.create_session(
                context,
                state_backend=self.state_backend,
            )
            
            ad = await self.metrics.track_request(session)
            
            logger.info(
                f"Ad served from fallback",
                extra={
                    "user_id": user_id,
                    "request_id": request_id,
                    "campaign_id": campaign_id,
                },
            )
            
            return ad
        
        except Exception as e:
            logger.error(
                f"Both upstreams failed: {e}",
                extra={"request_id": request_id},
            )
            return None
        
        finally:
            await session.close()

# Usage
server = AdServer(
    primary_upstream=primary_vast,
    fallback_upstream=fallback_vast,
    state_backend=redis_backend,
)

ad = await server.serve_ad(
    user_id="user123",
    device_id="device456",
    campaign_id="campaign789",
    budget_limit=1000.0,
    frequency_cap=3,
)
```

---

## Summary

Stateful ad serving requires:

1. **Session Management** - Lifecycle from creation to cleanup
2. **Concurrent Access** - Multiple users with independent sessions
3. **Fallback Strategies** - Primary + fallback upstreams
4. **Error Recovery** - Circuit breakers and retries
5. **Caching** - Reduce redundant requests
6. **Monitoring** - Track metrics and health
7. **Database Integration** - Persistent state tracking

This foundation enables production-grade ad serving at scale.

---

**Next:** See [Session Management](01-session-management.md) for basic patterns.
