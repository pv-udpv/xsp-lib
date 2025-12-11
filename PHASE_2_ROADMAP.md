# Phase 2 Roadmap: Protocol Handlers & Stateful Operations

**Version:** 1.0  
**Date:** December 11, 2025  
**Status:** Ready to Execute  
**Duration:** 9-13 weeks  
**Effort:** 40-50 hours  

## Table of Contents

1. [Phase 2 Overview](#phase-2-overview)
2. [Critical Gap Analysis](#critical-gap-analysis)
3. [Detailed Objectives](#detailed-objectives)
4. [Implementation Scope](#implementation-scope)
5. [OpenRTB 2.6 Strategy](#openrtb-26-strategy)
6. [VAST Chain Resolver](#vast-chain-resolver)
7. [Stateful Operations](#stateful-operations)
8. [StateBackend Implementations](#statebackend-implementations)
9. [Testing Strategy](#testing-strategy)
10. [Timeline & Milestones](#timeline--milestones)
11. [Risk Assessment](#risk-assessment)
12. [Success Criteria](#success-criteria)

---

## Phase 2 Overview

### What is Phase 2?

Phase 2 transforms the Phase 1 foundation into working protocol handlers with real-world capabilities:

**Input (from Phase 1):**
- ✅ SessionContext (immutable session state)
- ✅ UpstreamSession (stateful operations)
- ✅ UpstreamConfig (transport-agnostic config)
- ✅ HTTP/gRPC Transport
- ✅ @configurable decorator system

**Output (Phase 2 Goal):**
- 🎯 OpenRTB 2.6 complete implementation
- 🎯 VAST chain resolver with sessions
- 🎯 Frequency capping (working)
- 🎯 Budget tracking (working)
- 🎯 StateBackend implementations (Redis, DB)
- 🎯 Production-ready examples

### Phase 2 Success Criteria

| Criteria | Target | Metric |
|----------|--------|--------|
| **OpenRTB Coverage** | 100% | All 2.6 spec fields |
| **VAST Resolution** | Working | Multi-hop wrappers |
| **Frequency Capping** | Working | Per-user enforcement |
| **Budget Tracking** | Working | Per-campaign tracking |
| **StateBackend** | 2+ implementations | Redis + Database |
| **Test Coverage** | 90%+ | Protocol tests |
| **Performance** | <100ms p50 | Response latency |
| **Documentation** | 5000+ words | Implementation guides |
| **Examples** | 5+ working | Real-world scenarios |
| **Production Ready** | Yes | MVP criteria met |

---

## Critical Gap Analysis

### Current State (After Phase 1)

```
✅ Foundation: 100% (SessionContext, UpstreamSession, Config)
✅ VAST Support: 60% (Basic fetch, no chain resolution)
🔴 OpenRTB Support: 0% (NOT STARTED)
❌ Stateful Features: 0% (Frequency cap, budget tracking)
❌ StateBackend: 0% (Redis, Database implementations)
```

### Critical Gaps

#### Gap 1: OpenRTB 2.6 Missing (CRITICAL)

**Impact:** 50%+ of modern ad networks use OpenRTB

**Missing:**
- Request schema (Bid request)
- Response schema (Bid response)
- Validation logic
- Winner determination
- Price handling
- Deal negotiation

**Effort:** 15-20 hours  
**Priority:** 🔴 CRITICAL

#### Gap 2: Stateful Operations (HIGH)

**Impact:** Can't enforce business rules

**Missing:**
- Frequency cap enforcement
- Budget tracking
- Persistent state
- Session lifecycle

**Effort:** 10-15 hours  
**Priority:** 🔴 HIGH

#### Gap 3: StateBackend Implementations (HIGH)

**Impact:** Can't scale beyond single process

**Missing:**
- Redis implementation
- Database implementation
- Connection pooling
- Error recovery

**Effort:** 8-12 hours  
**Priority:** 🔴 HIGH

#### Gap 4: VAST Chain Resolution (MEDIUM)

**Impact:** Can't handle wrapper chains

**Missing:**
- Wrapper chain parsing
- Recursive resolution
- Macro substitution
- Tracking URL collection

**Effort:** 6-8 hours  
**Priority:** 🟡 MEDIUM

---

## Detailed Objectives

### Objective 1: Implement OpenRTB 2.6 (CRITICAL)

**Scope:**
- Complete BidRequest schema
- Complete BidResponse schema
- Validation logic
- Type-safe wrappers

**Deliverable:**
```python
# src/xsp/protocols/openrtb.py
class OpenRtbUpstream(BaseUpstream[BidResponse]):
    async def fetch(self, *, params: dict) -> BidResponse:
        # Full OpenRTB 2.6 implementation
        ...
```

**Testing:**
- 30+ unit tests
- 90%+ coverage
- IAB spec compliance

### Objective 2: Implement Stateful Operations (HIGH)

**Scope:**
- Frequency cap enforcement
- Budget tracking
- Session state persistence
- Error recovery

**Deliverable:**
```python
# Session with working frequency cap
if await session.check_frequency_cap(user_id, limit=3):
    ad = await session.request()
    await session.track_budget(campaign_id, 2.50)
```

**Testing:**
- 20+ unit tests
- State consistency
- Concurrent access safety

### Objective 3: StateBackend Implementations (HIGH)

**Scope:**
- Redis implementation (distributed)
- Database implementation (persistent)
- Connection pooling
- Expiry handling

**Deliverable:**
```python
# Redis backend
redis_backend = RedisBackend(redis_url="redis://...")

# Database backend
db_backend = DatabaseBackend(db_url="postgresql://...")
```

**Testing:**
- 15+ integration tests
- Load testing
- Failure scenarios

### Objective 4: VAST Chain Resolution (MEDIUM)

**Scope:**
- Parse wrapper chains
- Recursive resolution
- Macro substitution
- Tracking collection

**Deliverable:**
```python
resolver = VastChainResolver(upstream)
final_inline = await resolver.resolve(user_id="user123")
```

**Testing:**
- 15+ test cases
- Real wrapper chains
- Error handling

---

## Implementation Scope

### PR #71: OpenRTB 2.6 Implementation

**Effort:** 15-20 hours  
**Scope:**

```python
# src/xsp/protocols/openrtb.py

# Type-safe schemas
class BidRequest(TypedDict):
    id: str
    imp: List[Impression]
    site: Optional[Site]
    device: Optional[Device]
    user: Optional[User]
    # ... 20+ more fields

class BidResponse(TypedDict):
    id: str
    seatbid: List[SeatBid]
    bidid: str
    # ... more fields

# Upstream handler
class OpenRtbUpstream(BaseUpstream[BidResponse]):
    async def fetch(
        self,
        *,
        params: dict[str, Any] | None = None,
    ) -> BidResponse:
        # Complete implementation
        ...
```

**Deliverables:**
- ✅ Full BidRequest schema (25+ fields)
- ✅ Full BidResponse schema (20+ fields)
- ✅ Validation logic (IAB compliant)
- ✅ Winner determination logic
- ✅ 30+ unit tests
- ✅ 90%+ code coverage
- ✅ mypy --strict compliant
- ✅ Documentation (2000+ words)

### PR #72: Frequency Capping Implementation

**Effort:** 8-10 hours  
**Scope:**

```python
# Working frequency cap enforcement
class FrequencyCap:
    async def check_and_increment(
        self,
        user_id: str,
        limit: int,
        window: str = "hour",  # hour, day, week
    ) -> bool:
        # Check if under cap
        # Increment counter
        # Set expiry
        ...

# In session
if await session.check_frequency_cap(user_id, limit=3):
    ad = await session.request()
```

**Deliverables:**
- ✅ FrequencyCap class with enforcement
- ✅ Time window support (hour, day, week)
- ✅ StateBackend integration
- ✅ 15+ unit tests
- ✅ Concurrent access safety
- ✅ Documentation

### PR #73: Budget Tracking Implementation

**Effort:** 8-10 hours  
**Scope:**

```python
# Working budget tracking
class BudgetTracker:
    async def track_spend(
        self,
        campaign_id: str,
        amount: float,
    ) -> dict:
        # Add to spend
        # Return remaining budget
        # Check budget limit
        ...

# In session
await session.track_budget(campaign_id, cpm=2.50)
remaining = budget_limit - await session.get_budget(campaign_id)
```

**Deliverables:**
- ✅ BudgetTracker class
- ✅ Spend accumulation
- ✅ Budget remaining calculation
- ✅ Campaign-level tracking
- ✅ 15+ unit tests
- ✅ Documentation

### PR #74: StateBackend Implementations

**Effort:** 10-12 hours  
**Scope:**

```python
# Redis implementation
class RedisBackend(StateBackend):
    async def get_count(self, key: str) -> int: ...
    async def increment(self, key: str) -> int: ...
    async def get_spend(self, key: str) -> float: ...
    async def add_spend(self, key: str, amount: float) -> float: ...

# Database implementation
class DatabaseBackend(StateBackend):
    async def get_count(self, key: str) -> int: ...
    async def increment(self, key: str) -> int: ...
    # ... same interface
```

**Deliverables:**
- ✅ RedisBackend (distributed)
- ✅ DatabaseBackend (persistent)
- ✅ Connection pooling
- ✅ Error recovery
- ✅ 20+ integration tests
- ✅ Load testing
- ✅ Documentation

### PR #75: VAST Chain Resolver

**Effort:** 6-8 hours  
**Scope:**

```python
# VAST chain resolver with sessions
class VastChainResolver:
    async def resolve(
        self,
        user_id: str,
        max_hops: int = 5,
    ) -> VastInline:
        # Parse and follow wrapper chain
        # Maintain session context
        # Substitute macros
        # Collect tracking URLs
        ...
```

**Deliverables:**
- ✅ Chain resolution logic
- ✅ Macro substitution
- ✅ Tracking URL collection
- ✅ Session context preservation
- ✅ 15+ test cases
- ✅ Documentation

---

## OpenRTB 2.6 Strategy

### IAB Spec Compliance

**BidRequest Fields (25+):**
- `id` - Exchange-generated request ID
- `imp` - Array of impression objects
- `site` - Site object (web)
- `app` - App object (mobile)
- `device` - Device object
- `user` - User object
- `at` - Auction type (1st price, 2nd price)
- `tmax` - Max response time in ms
- `wseat` - Whitelist buyer seats
- `bseat` - Blacklist buyer seats
- `allimps` - All impressions required
- `cur` - Currencies accepted
- `wlang` - Whitelist languages
- `bcat` - Blocked categories
- `badv` - Blocked advertisers
- `bapp` - Blocked applications
- ... and more

**BidResponse Fields (20+):**
- `id` - Response to request ID
- `seatbid` - Array of seat bid objects
- `bidid` - Bidder-generated response ID
- `cur` - Currency of bids
- `customdata` - Optional custom data
- `nbr` - No-bid reason code
- ... and more

### Type Safety

```python
# Full type hints
class BidRequest(TypedDict, total=False):
    """OpenRTB 2.6 Bid Request."""
    id: str
    imp: list[Impression]
    site: Site
    device: Device
    user: User
    # All fields optional (total=False)

# Validation
class BidRequestValidator:
    def validate(self, request: BidRequest) -> ValidationResult:
        # Check required fields
        # Check field types
        # Check field ranges
        # Check enum values
        ...
```

### Winner Determination

```python
class WinnerDetermination:
    def determine_winner(
        self,
        bid_response: BidResponse,
        request: BidRequest,
    ) -> Optional[Bid]:
        """Determine highest valid bid."""
        # Get all bids
        # Filter by auction type
        # Handle pricing (net vs gross)
        # Apply deal requirements
        # Return winner
        ...
```

---

## VAST Chain Resolver

### How It Works

```
1. Request wrapper1 (with session context)
   └─ Get redirect to wrapper2

2. Request wrapper2 (same session context)
   └─ Get redirect to wrapper3

3. Request wrapper3 (same session context)
   └─ Get redirect to inline

4. Request inline (same session context)
   └─ Get final ad content

Result: Complete inline with all tracking URLs
```

### Session Preservation

```python
# Session context flows through entire chain
context = SessionContext(
    timestamp=...,
    correlator="session-123",  # Same throughout
    cachebusting="...",         # Same throughout
    cookies={...},               # Preserved
    request_id="...",            # Same for logging
)

# Each request uses same context
response1 = await session.request()  # wrapper1
response2 = await session.request()  # wrapper2
response3 = await session.request()  # wrapper3
response4 = await session.request()  # inline
```

---

## Stateful Operations

### Frequency Capping

**Use Case:**
```
User sees 3 ads per hour, then:
- 4th ad blocked (at cap)
- 5th ad blocked (over cap)
- After 1 hour: reset
```

**Implementation:**
```python
# Check and increment atomically
count = await state_backend.increment(f"freq:hour:{user_id}")
if count > 3:
    return None  # Don't serve
```

### Budget Tracking

**Use Case:**
```
Campaign budget $1000:
- Ad 1: Cost $2.50, remaining $997.50
- Ad 2: Cost $3.00, remaining $994.50
- Ad 500: Cost $2.50, remaining $0.00 (budget exhausted)
```

**Implementation:**
```python
# Add spend and get remaining
await state_backend.add_spend(f"budget:{campaign_id}", 2.50)
remaining = budget_limit - await state_backend.get_spend(...)
```

---

## StateBackend Implementations

### RedisBackend (Distributed)

**Pros:**
- ✅ Fast (sub-millisecond)
- ✅ Distributed (multiple instances)
- ✅ Atomic operations
- ✅ Expiry support built-in

**Cons:**
- ❌ Data lost on restart (without persistence)
- ❌ Requires Redis cluster

**Use For:** Production, distributed systems

### DatabaseBackend (Persistent)

**Pros:**
- ✅ Data persists
- ✅ Auditable
- ✅ Complex queries
- ✅ Works with existing databases

**Cons:**
- ❌ Slower (milliseconds)
- ❌ Needs connection pooling

**Use For:** Compliance, reporting, small to medium scale

### InMemoryBackend (Testing)

**Pros:**
- ✅ Fast (microseconds)
- ✅ No dependencies
- ✅ Perfect for testing

**Cons:**
- ❌ Lost on process exit
- ❌ Not distributed

**Use For:** Unit tests, development

---

## Testing Strategy

### Unit Tests (60 tests, 40-50 hours)

```python
# OpenRTB tests (30+)
- BidRequest validation
- BidResponse validation
- Winner determination
- Price handling
- Deal negotiation

# Frequency cap tests (15+)
- Single user, single window
- Multiple windows (hour/day/week)
- Cap enforcement
- Concurrent access
- Expiry handling

# Budget tracking tests (15+)
- Add spend
- Get remaining
- Multiple campaigns
- Concurrent tracking

# StateBackend tests (20+)
- Redis operations
- Database operations
- Connection pooling
- Error recovery
```

### Integration Tests (20 tests)

```python
# End-to-end scenarios
- Complete OpenRTB bid flow
- Frequency cap with sessions
- Budget tracking with sessions
- VAST chain resolution
- Multi-upstream fallback
```

### Performance Tests

```python
# Latency targets
- BidRequest validation: <5ms
- Winner determination: <5ms
- Frequency cap check: <10ms
- Budget tracking: <10ms
- Chain resolution: <100ms
```

---

## Timeline & Milestones

### Week 1-2: OpenRTB 2.6 (PR #71)
- Schema definition (15-20 hours)
- Validation logic
- Winner determination
- 30+ unit tests
- Documentation

### Week 3: Frequency Capping (PR #72)
- FrequencyCap class (8-10 hours)
- Time window support
- StateBackend integration
- 15+ unit tests

### Week 4: Budget Tracking (PR #73)
- BudgetTracker class (8-10 hours)
- Campaign tracking
- Remaining calculation
- 15+ unit tests

### Week 5: StateBackend (PR #74)
- Redis implementation (10-12 hours)
- Database implementation
- Connection pooling
- 20+ integration tests

### Week 6: VAST Chain Resolver (PR #75)
- Chain resolution (6-8 hours)
- Macro substitution
- Tracking collection
- 15+ test cases

### Week 7: Integration & Testing
- Full integration testing
- Performance testing
- Documentation
- Examples

**Total: 9 weeks (7 weeks active work + 2 weeks buffer)**

---

## Risk Assessment

### Risk 1: OpenRTB Spec Complexity (HIGH)

**Impact:** Misimplementation could cause bid rejections  
**Mitigation:**
- Use official IAB spec
- Reference implementations
- Comprehensive validation
- Real-world test cases

### Risk 2: StateBackend Consistency (MEDIUM)

**Impact:** Frequency caps or budget tracking fail  
**Mitigation:**
- Atomic operations
- Comprehensive testing
- Error recovery
- Monitoring

### Risk 3: Performance Regression (MEDIUM)

**Impact:** Latency increases, service degrades  
**Mitigation:**
- Performance tests
- Benchmarking
- Optimization early
- Load testing

### Risk 4: Session State Leaks (MEDIUM)

**Impact:** User data exposed or mixed  
**Mitigation:**
- Immutable SessionContext
- Isolated sessions
- Comprehensive testing
- Security review

---

## Success Criteria

### Functional Criteria

- ✅ OpenRTB 2.6 fully implemented
- ✅ Frequency capping working
- ✅ Budget tracking working
- ✅ VAST chain resolver working
- ✅ StateBackend implementations (Redis, DB)
- ✅ 5+ complete working examples

### Quality Criteria

- ✅ 90%+ code coverage
- ✅ mypy --strict compliant
- ✅ 0 linting errors
- ✅ 60+ unit tests passing
- ✅ 20+ integration tests passing

### Performance Criteria

- ✅ BidRequest validation <5ms
- ✅ Frequency cap check <10ms
- ✅ Budget tracking <10ms
- ✅ Chain resolution <100ms

### Documentation Criteria

- ✅ 5000+ words documentation
- ✅ 10+ code examples
- ✅ Integration guide
- ✅ Troubleshooting guide

---

## Summary

Phase 2 closes critical gaps in OpenRTB support, adds stateful operations (frequency capping, budget tracking), and implements persistent storage backends. This enables production-ready ad serving with real-world business logic.

**Current State:** Phase 1 complete, Phase 2 ready  
**Timeline:** 9 weeks (7 active + 2 buffer)  
**Effort:** 40-50 hours  
**Result:** Production-ready ad serving library  

---

**Next Step:** Begin Phase 2 PR #71 (OpenRTB 2.6) when ready.
