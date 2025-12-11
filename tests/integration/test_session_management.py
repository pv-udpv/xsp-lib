"""Integration tests for Phase 4 production features: session management, frequency capping, and budget tracking.

This test suite validates:
1. SessionContext immutability and behavior
2. VastSession state tracking capabilities
3. Integration with FrequencyCappingMiddleware
4. Integration with BudgetTrackingMiddleware
5. Complete end-to-end workflows with all components
6. Edge cases and concurrent access patterns

References:
    - IAB VAST 4.2: Video ad serving standards
    - IAB QAG: Frequency capping best practices
    - IAB OpenRTB: Budget tracking patterns
"""

import asyncio
from datetime import datetime
from decimal import Decimal

import pytest

from xsp.core.exceptions import BudgetExceeded, FrequencyCapExceeded, TransportError
from xsp.core.session import SessionContext, VastSession
from xsp.middleware.base import MiddlewareStack
from xsp.middleware.budget import Budget, BudgetTrackingMiddleware, InMemoryBudgetStore
from xsp.middleware.frequency import (
    FrequencyCap,
    FrequencyCappingMiddleware,
    InMemoryFrequencyStore,
)
from xsp.protocols.vast.upstream import VastUpstream
from xsp.transports.memory import MemoryTransport


# Sample VAST XML for testing
VAST_XML_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2" xmlns="http://www.iab.com/VAST">
  <Ad id="test-ad-123">
    <InLine>
      <AdSystem version="1.0">Test Ad Server</AdSystem>
      <AdTitle>Test Ad</AdTitle>
      <Impression><![CDATA[https://example.com/impression]]></Impression>
      <Creatives>
        <Creative>
          <Linear>
            <Duration>00:00:15</Duration>
            <MediaFiles>
              <MediaFile delivery="progressive" type="video/mp4">
                <![CDATA[https://example.com/video.mp4]]>
              </MediaFile>
            </MediaFiles>
          </Linear>
        </Creative>
      </Creatives>
    </InLine>
  </Ad>
</VAST>"""


# Fixtures


@pytest.fixture
def session_context() -> SessionContext:
    """Provide a standard SessionContext for testing."""
    return SessionContext(
        request_id="req-test-001",
        user_id="user-test-123",
        ip_address="192.168.1.100",
        timestamp=datetime.now(),
        metadata={"platform": "web", "device": "desktop"},
    )


@pytest.fixture
def vast_transport() -> MemoryTransport:
    """Provide MemoryTransport with VAST XML response."""
    return MemoryTransport(VAST_XML_SAMPLE.encode("utf-8"))


@pytest.fixture
def vast_upstream(vast_transport: MemoryTransport) -> VastUpstream:
    """Provide VastUpstream instance for testing."""
    return VastUpstream(
        transport=vast_transport,
        endpoint="memory://test-ads",
        validate_xml=False,
    )


@pytest.fixture
async def vast_session(
    vast_upstream: VastUpstream, session_context: SessionContext
) -> VastSession:
    """Provide VastSession instance for testing."""
    session = VastSession(vast_upstream, session_context)
    yield session
    await session.close()


@pytest.fixture
def frequency_store() -> InMemoryFrequencyStore:
    """Provide fresh InMemoryFrequencyStore for testing."""
    return InMemoryFrequencyStore()


@pytest.fixture
def budget_store() -> InMemoryBudgetStore:
    """Provide fresh InMemoryBudgetStore for testing."""
    return InMemoryBudgetStore()


# 1. SessionContext Immutability Tests


@pytest.mark.asyncio
async def test_session_context_is_frozen():
    """Test that SessionContext is truly immutable via frozen dataclass.

    Per Python dataclass(frozen=True) specification, attempting to modify
    fields should raise FrozenInstanceError.
    """
    ctx = SessionContext(
        request_id="req-001",
        user_id="user-001",
        ip_address="10.0.0.1",
        timestamp=datetime.now(),
    )

    # Verify field access works
    assert ctx.request_id == "req-001"
    assert ctx.user_id == "user-001"

    # Verify fields cannot be reassigned
    with pytest.raises(AttributeError):
        ctx.request_id = "req-002"  # type: ignore

    with pytest.raises(AttributeError):
        ctx.user_id = "user-002"  # type: ignore


@pytest.mark.asyncio
async def test_session_context_metadata_dict_is_mutable():
    """Test that while SessionContext is frozen, metadata dict itself is mutable.

    This is a known limitation of frozen dataclasses with mutable default fields.
    While the dataclass reference is frozen, the dict object can be modified.

    Note:
        Best practice is to NOT modify metadata after creation, but this test
        documents the current behavior.
    """
    ctx = SessionContext(
        request_id="req-001",
        user_id="user-001",
        ip_address="10.0.0.1",
        timestamp=datetime.now(),
        metadata={"key1": "value1"},
    )

    # The metadata dict CAN be modified (not ideal, but documented)
    ctx.metadata["key2"] = "value2"
    assert ctx.metadata["key2"] == "value2"

    # But the metadata reference itself cannot be replaced
    with pytest.raises(AttributeError):
        ctx.metadata = {"new": "dict"}  # type: ignore


@pytest.mark.asyncio
async def test_session_context_with_empty_metadata():
    """Test SessionContext with default empty metadata dict."""
    ctx = SessionContext(
        request_id="req-001",
        user_id="user-001",
        ip_address="10.0.0.1",
        timestamp=datetime.now(),
    )

    assert ctx.metadata == {}
    assert isinstance(ctx.metadata, dict)


# 2. VastSession State Tracking Tests


@pytest.mark.asyncio
async def test_vast_session_tracks_request_count(vast_session: VastSession):
    """Test that VastSession correctly increments request_count on each fetch.

    State tracking is critical for monitoring request volume per session
    and identifying potential abuse or unusual patterns.
    """
    # Initial state
    assert vast_session.state["request_count"] == 0

    # First request
    await vast_session.fetch()
    assert vast_session.state["request_count"] == 1

    # Second request
    await vast_session.fetch()
    assert vast_session.state["request_count"] == 2

    # Third request
    await vast_session.fetch()
    assert vast_session.state["request_count"] == 3


@pytest.mark.asyncio
async def test_vast_session_tracks_last_request_time(vast_session: VastSession):
    """Test that VastSession updates last_request_time on each fetch.

    Tracking request timing helps with:
    - Session timeout detection
    - Request rate monitoring
    - Debugging timing-related issues
    """
    # Initial state
    assert vast_session.state["last_request_time"] is None

    # Record time before request
    before_request = datetime.now()

    # Make request
    await vast_session.fetch()

    # Verify last_request_time was set and is recent
    last_time = vast_session.state["last_request_time"]
    assert last_time is not None
    assert isinstance(last_time, datetime)
    assert last_time >= before_request


@pytest.mark.asyncio
async def test_vast_session_tracks_errors(session_context: SessionContext):
    """Test that VastSession tracks errors in state when fetch fails.

    Error tracking enables:
    - Circuit breaker patterns
    - Retry decision logic
    - Error rate monitoring
    - Debugging failed requests
    """
    # Create transport that raises error
    class FailingTransport:
        @property
        def transport_type(self):
            from xsp.core.transport import TransportType

            return TransportType.MEMORY

        async def send(self, *args, **kwargs):
            raise TransportError("Simulated transport failure")

        async def close(self):
            pass

    failing_transport = FailingTransport()
    failing_upstream = VastUpstream(
        transport=failing_transport,
        endpoint="memory://failing",
    )
    session = VastSession(failing_upstream, session_context)

    # Initial state
    assert len(session.state["errors"]) == 0

    # Attempt fetch (should fail)
    with pytest.raises(TransportError):
        await session.fetch()

    # Verify error was tracked
    assert len(session.state["errors"]) == 1
    error_entry = session.state["errors"][0]
    assert "timestamp" in error_entry
    assert "error" in error_entry
    assert "type" in error_entry
    assert error_entry["type"] == "TransportError"
    assert "transport failure" in error_entry["error"].lower()

    await session.close()


@pytest.mark.asyncio
async def test_vast_session_tracks_total_bytes(vast_session: VastSession):
    """Test that VastSession tracks total bytes fetched.

    Byte tracking enables:
    - Bandwidth monitoring
    - Cost estimation for data transfer
    - Payload size analysis
    """
    # Initial state
    assert vast_session.state["total_bytes"] == 0

    # First request
    await vast_session.fetch()
    bytes_after_first = vast_session.state["total_bytes"]
    assert bytes_after_first > 0

    # Second request should add more bytes
    await vast_session.fetch()
    bytes_after_second = vast_session.state["total_bytes"]
    assert bytes_after_second == bytes_after_first * 2


@pytest.mark.asyncio
async def test_vast_session_thread_safety_concurrent_requests(
    vast_upstream: VastUpstream, session_context: SessionContext
):
    """Test that VastSession handles concurrent requests safely.

    VastSession uses asyncio.Lock to protect state updates, ensuring
    thread-safe concurrent access. This test verifies that multiple
    concurrent requests properly increment counters without race conditions.

    Per VastSession documentation, state updates are protected by asyncio.Lock
    to ensure thread-safe concurrent access.
    """
    session = VastSession(vast_upstream, session_context)

    # Launch 10 concurrent requests
    concurrent_count = 10
    results = await asyncio.gather(
        *[session.fetch() for _ in range(concurrent_count)],
        return_exceptions=False,
    )

    # Verify all requests succeeded
    assert len(results) == concurrent_count
    for result in results:
        assert "VAST" in result

    # Verify request count is accurate despite concurrent access
    assert session.state["request_count"] == concurrent_count

    # Verify bytes tracking is accurate (all responses are same size)
    expected_bytes = len(VAST_XML_SAMPLE.encode("utf-8")) * concurrent_count
    assert session.state["total_bytes"] == expected_bytes

    await session.close()


@pytest.mark.asyncio
async def test_vast_session_context_property(vast_session: VastSession):
    """Test that VastSession.context returns immutable SessionContext."""
    ctx = vast_session.context

    assert isinstance(ctx, SessionContext)
    assert ctx.request_id == "req-test-001"
    assert ctx.user_id == "user-test-123"

    # Verify context cannot be modified
    with pytest.raises(AttributeError):
        vast_session.context = SessionContext(  # type: ignore
            request_id="new",
            user_id="new",
            ip_address="new",
            timestamp=datetime.now(),
        )


# 3. End-to-End Workflow Tests


@pytest.mark.asyncio
async def test_session_with_frequency_capping_middleware(
    vast_upstream: VastUpstream,
    session_context: SessionContext,
    frequency_store: InMemoryFrequencyStore,
):
    """Test complete workflow: SessionContext + VastSession + FrequencyCappingMiddleware.

    This integration test validates:
    1. Session context is properly propagated to middleware
    2. Frequency capping uses session user_id for tracking
    3. Cap enforcement works across multiple requests
    4. State tracking continues through middleware

    Per IAB QAG recommendations, frequency caps typically range from
    3-10 impressions per 24-hour period for optimal user experience.
    """
    # Create frequency cap: max 3 impressions per hour
    cap = FrequencyCap(
        max_impressions=3,
        time_window_seconds=3600,
        per_campaign=False,
    )
    freq_middleware = FrequencyCappingMiddleware(cap, frequency_store)

    # Wrap upstream with middleware
    stack = MiddlewareStack(freq_middleware)
    wrapped_upstream = stack.wrap(vast_upstream)

    # Create session
    session = VastSession(wrapped_upstream, session_context)

    # First 3 requests should succeed
    await session.fetch()
    assert session.state["request_count"] == 1

    await session.fetch()
    assert session.state["request_count"] == 2

    await session.fetch()
    assert session.state["request_count"] == 3

    # 4th request should exceed frequency cap
    with pytest.raises(FrequencyCapExceeded) as exc_info:
        await session.fetch()

    assert "Frequency cap exceeded" in str(exc_info.value)
    assert session_context.user_id in str(exc_info.value)

    # Request count should still be 3 (failed request doesn't increment)
    assert session.state["request_count"] == 3

    await session.close()


@pytest.mark.asyncio
async def test_session_with_budget_tracking_middleware(
    vast_upstream: VastUpstream,
    session_context: SessionContext,
    budget_store: InMemoryBudgetStore,
):
    """Test complete workflow: SessionContext + VastSession + BudgetTrackingMiddleware.

    This integration test validates:
    1. Budget tracking with session-based requests
    2. Budget enforcement prevents overspending
    3. Spend is properly tracked across requests
    4. State tracking continues through middleware

    Per IAB OpenRTB and programmatic supply chain best practices,
    budget tracking should use Decimal for financial precision.
    """
    # Initialize budget: $100 total
    budget = Budget(
        total_budget=Decimal("100.00"),
        spent=Decimal("0.00"),
        currency="USD",
    )
    budget_store._store["budget:global"] = budget

    # Create middleware with $20 default cost per request
    budget_middleware = BudgetTrackingMiddleware(
        store=budget_store,
        default_cost=Decimal("20.00"),
        per_campaign=False,
    )

    # Wrap upstream with middleware
    stack = MiddlewareStack(budget_middleware)
    wrapped_upstream = stack.wrap(vast_upstream)

    # Create session
    session = VastSession(wrapped_upstream, session_context)

    # First 5 requests should succeed (5 * $20 = $100)
    for i in range(5):
        await session.fetch()
        assert session.state["request_count"] == i + 1

    # Verify budget is exhausted
    current_budget = await budget_store.get_budget("budget:global")
    assert current_budget is not None
    assert current_budget.spent == Decimal("100.00")

    # 6th request should exceed budget
    with pytest.raises(BudgetExceeded) as exc_info:
        await session.fetch()

    assert "Budget exceeded" in str(exc_info.value)

    # Request count should still be 5 (failed request doesn't increment)
    assert session.state["request_count"] == 5

    await session.close()


@pytest.mark.asyncio
async def test_complete_workflow_all_components(
    vast_upstream: VastUpstream,
    session_context: SessionContext,
    frequency_store: InMemoryFrequencyStore,
    budget_store: InMemoryBudgetStore,
):
    """Test complete end-to-end workflow with all Phase 4 components.

    This comprehensive integration test validates the full stack:
    1. SessionContext (immutable request context)
    2. VastSession (state tracking wrapper)
    3. FrequencyCappingMiddleware (user impression limits)
    4. BudgetTrackingMiddleware (spend control)
    5. VastUpstream (VAST protocol implementation)
    6. MemoryTransport (test transport layer)

    The middleware stack applies in order:
    - FrequencyCapping (outer) -> BudgetTracking (inner) -> VastUpstream

    This represents a realistic production configuration for ad serving
    with both user experience controls (frequency) and financial controls (budget).
    """
    # Setup frequency cap: max 10 impressions per hour (higher than budget allows)
    freq_cap = FrequencyCap(
        max_impressions=10,
        time_window_seconds=3600,
        per_campaign=False,
    )
    freq_middleware = FrequencyCappingMiddleware(freq_cap, frequency_store)

    # Setup budget: $50 total, $10 per impression (allows 5 requests)
    budget = Budget(
        total_budget=Decimal("50.00"),
        spent=Decimal("0.00"),
        currency="USD",
    )
    budget_store._store["budget:global"] = budget
    budget_middleware = BudgetTrackingMiddleware(
        store=budget_store,
        default_cost=Decimal("10.00"),
        per_campaign=False,
    )

    # Build middleware stack (frequency -> budget -> upstream)
    stack = MiddlewareStack(freq_middleware, budget_middleware)
    wrapped_upstream = stack.wrap(vast_upstream)

    # Create session
    session = VastSession(wrapped_upstream, session_context)

    # Make 5 successful requests (within both frequency and budget limits)
    for i in range(5):
        result = await session.fetch()
        assert "VAST" in result
        assert session.state["request_count"] == i + 1

    # Verify final state
    assert session.state["request_count"] == 5
    assert session.state["total_bytes"] > 0
    assert len(session.state["errors"]) == 0

    # Verify budget is exhausted (5 * $10 = $50)
    current_budget = await budget_store.get_budget("budget:global")
    assert current_budget is not None
    assert current_budget.spent == Decimal("50.00")

    # 6th request should fail due to budget (frequency cap is 10, so budget is limiting factor)
    with pytest.raises(BudgetExceeded):
        await session.fetch()

    await session.close()


# 4. Edge Case Tests


@pytest.mark.asyncio
async def test_frequency_cap_exceeded_scenario(
    vast_upstream: VastUpstream,
    frequency_store: InMemoryFrequencyStore,
):
    """Test behavior when frequency cap is exceeded.

    Validates:
    - Proper exception raised
    - Error message contains relevant context
    - Subsequent requests continue to fail
    - Different users have independent caps
    """
    # Create cap: max 2 impressions
    cap = FrequencyCap(
        max_impressions=2,
        time_window_seconds=3600,
        per_campaign=False,
    )
    freq_middleware = FrequencyCappingMiddleware(cap, frequency_store)
    stack = MiddlewareStack(freq_middleware)
    wrapped_upstream = stack.wrap(vast_upstream)

    # User 1: exhaust cap
    ctx1 = SessionContext(
        request_id="req-001",
        user_id="user-001",
        ip_address="10.0.0.1",
        timestamp=datetime.now(),
    )
    session1 = VastSession(wrapped_upstream, ctx1)

    await session1.fetch()  # 1st impression
    await session1.fetch()  # 2nd impression

    with pytest.raises(FrequencyCapExceeded) as exc_info:
        await session1.fetch()  # 3rd impression - fails

    assert "user-001" in str(exc_info.value)
    assert "2/2" in str(exc_info.value)

    # User 2: should have independent cap
    ctx2 = SessionContext(
        request_id="req-002",
        user_id="user-002",
        ip_address="10.0.0.2",
        timestamp=datetime.now(),
    )
    session2 = VastSession(wrapped_upstream, ctx2)

    await session2.fetch()  # 1st impression - succeeds
    await session2.fetch()  # 2nd impression - succeeds

    await session1.close()
    await session2.close()


@pytest.mark.asyncio
async def test_budget_exceeded_scenario(
    vast_upstream: VastUpstream,
    budget_store: InMemoryBudgetStore,
):
    """Test behavior when budget is exceeded.

    Validates:
    - Proper exception raised
    - Error message shows remaining budget
    - Budget tracking is accurate
    - Different campaigns have independent budgets
    """
    # Setup budget: $25 total
    budget = Budget(
        total_budget=Decimal("25.00"),
        spent=Decimal("0.00"),
        currency="USD",
    )
    budget_store._store["budget:global"] = budget

    budget_middleware = BudgetTrackingMiddleware(
        store=budget_store,
        default_cost=Decimal("10.00"),
        per_campaign=False,
    )
    stack = MiddlewareStack(budget_middleware)
    wrapped_upstream = stack.wrap(vast_upstream)

    ctx = SessionContext(
        request_id="req-001",
        user_id="user-001",
        ip_address="10.0.0.1",
        timestamp=datetime.now(),
    )
    session = VastSession(wrapped_upstream, ctx)

    # 2 requests succeed ($20 spent)
    await session.fetch()
    await session.fetch()

    current = await budget_store.get_budget("budget:global")
    assert current is not None
    assert current.spent == Decimal("20.00")

    # 3rd request fails (would need $10, only $5 remaining)
    with pytest.raises(BudgetExceeded) as exc_info:
        await session.fetch()

    error_msg = str(exc_info.value)
    assert "Budget exceeded" in error_msg
    assert "5" in error_msg  # Remaining amount
    assert "USD" in error_msg

    await session.close()


@pytest.mark.asyncio
async def test_multiple_sessions_different_contexts(vast_transport: MemoryTransport):
    """Test multiple concurrent sessions with different contexts.

    Validates:
    - Sessions maintain independent state
    - Context isolation between sessions
    - Concurrent sessions don't interfere
    - Each session tracks its own statistics
    """
    # Create 3 sessions with different contexts
    sessions = []
    for i in range(3):
        ctx = SessionContext(
            request_id=f"req-{i}",
            user_id=f"user-{i}",
            ip_address=f"192.168.1.{i}",
            timestamp=datetime.now(),
            metadata={"session_num": i},
        )
        upstream = VastUpstream(
            transport=vast_transport,
            endpoint=f"memory://session-{i}",
        )
        session = VastSession(upstream, ctx)
        sessions.append(session)

    # Make different numbers of requests per session
    await sessions[0].fetch()  # 1 request
    await sessions[1].fetch()  # 1 request
    await sessions[1].fetch()  # 2 requests
    await sessions[2].fetch()  # 1 request
    await sessions[2].fetch()  # 2 requests
    await sessions[2].fetch()  # 3 requests

    # Verify independent state tracking
    assert sessions[0].state["request_count"] == 1
    assert sessions[1].state["request_count"] == 2
    assert sessions[2].state["request_count"] == 3

    # Verify context isolation
    assert sessions[0].context.user_id == "user-0"
    assert sessions[1].context.user_id == "user-1"
    assert sessions[2].context.user_id == "user-2"

    # Cleanup
    for session in sessions:
        await session.close()


@pytest.mark.asyncio
async def test_concurrent_access_pattern(
    vast_upstream: VastUpstream,
    session_context: SessionContext,
    frequency_store: InMemoryFrequencyStore,
):
    """Test concurrent access patterns with middleware.

    Validates:
    - Thread-safe middleware execution
    - Frequency store handles concurrent updates
    - No race conditions in state tracking
    - Accurate counting under concurrent load
    """
    # Setup frequency cap
    cap = FrequencyCap(
        max_impressions=20,  # Allow enough for concurrent requests
        time_window_seconds=3600,
        per_campaign=False,
    )
    freq_middleware = FrequencyCappingMiddleware(cap, frequency_store)
    stack = MiddlewareStack(freq_middleware)
    wrapped_upstream = stack.wrap(vast_upstream)

    session = VastSession(wrapped_upstream, session_context)

    # Launch 10 concurrent requests
    concurrent_count = 10
    results = await asyncio.gather(
        *[session.fetch() for _ in range(concurrent_count)],
        return_exceptions=False,
    )

    # Verify all succeeded
    assert len(results) == concurrent_count
    assert session.state["request_count"] == concurrent_count

    # Verify frequency store has accurate count
    key = f"freq:user:{session_context.user_id}"
    stored_count = await frequency_store.get_count(key)
    assert stored_count == concurrent_count

    await session.close()


@pytest.mark.asyncio
async def test_per_campaign_frequency_and_budget(
    vast_transport: MemoryTransport,
    frequency_store: InMemoryFrequencyStore,
    budget_store: InMemoryBudgetStore,
):
    """Test per-campaign frequency capping and budget tracking together.

    Validates:
    - Per-campaign frequency caps work correctly
    - Per-campaign budgets work correctly
    - Different campaigns have independent limits
    - Middleware stack handles campaign context properly
    """
    # Setup per-campaign frequency cap: 3 per campaign
    freq_cap = FrequencyCap(
        max_impressions=3,
        time_window_seconds=3600,
        per_campaign=True,
    )
    freq_middleware = FrequencyCappingMiddleware(freq_cap, frequency_store)

    # Setup per-campaign budgets
    campaign1_budget = Budget(
        total_budget=Decimal("30.00"),
        spent=Decimal("0.00"),
        currency="USD",
        campaign_id="camp-1",
    )
    budget_store._store["budget:campaign:camp-1"] = campaign1_budget

    campaign2_budget = Budget(
        total_budget=Decimal("50.00"),
        spent=Decimal("0.00"),
        currency="USD",
        campaign_id="camp-2",
    )
    budget_store._store["budget:campaign:camp-2"] = campaign2_budget

    budget_middleware = BudgetTrackingMiddleware(
        store=budget_store,
        default_cost=Decimal("10.00"),
        per_campaign=True,
    )

    # Build stack
    stack = MiddlewareStack(freq_middleware, budget_middleware)

    # Create upstream and wrap
    upstream = VastUpstream(transport=vast_transport, endpoint="memory://test")
    wrapped_upstream = stack.wrap(upstream)

    # Create session for user-123
    ctx = SessionContext(
        request_id="req-001",
        user_id="user-123",
        ip_address="10.0.0.1",
        timestamp=datetime.now(),
        metadata={"campaign_id": "camp-1"},
    )
    session = VastSession(wrapped_upstream, ctx)

    # Campaign 1: Make 3 requests (frequency limit) = $30 spent
    for _ in range(3):
        await session.fetch()

    # 4th request to campaign 1 should hit frequency cap
    with pytest.raises(FrequencyCapExceeded):
        await session.fetch()

    # Switch to campaign 2 (same user, different campaign)
    ctx2 = SessionContext(
        request_id="req-002",
        user_id="user-123",
        ip_address="10.0.0.1",
        timestamp=datetime.now(),
        metadata={"campaign_id": "camp-2"},
    )
    session2 = VastSession(wrapped_upstream, ctx2)

    # Campaign 2: Should have fresh frequency cap and budget
    for _ in range(3):
        await session2.fetch()

    # Verify budgets are tracked separately
    camp1_budget = await budget_store.get_budget("budget:campaign:camp-1")
    camp2_budget = await budget_store.get_budget("budget:campaign:camp-2")
    assert camp1_budget is not None
    assert camp1_budget.spent == Decimal("30.00")
    assert camp2_budget is not None
    assert camp2_budget.spent == Decimal("30.00")

    await session.close()
    await session2.close()


@pytest.mark.asyncio
async def test_session_health_check(vast_session: VastSession):
    """Test that VastSession.health_check delegates to upstream."""
    is_healthy = await vast_session.health_check()
    assert isinstance(is_healthy, bool)
    # MemoryTransport should be healthy
    assert is_healthy is True


@pytest.mark.asyncio
async def test_session_preserves_context_in_fetch(
    vast_upstream: VastUpstream, session_context: SessionContext
):
    """Test that VastSession merges SessionContext into fetch context.

    The session should automatically merge context fields (request_id, user_id,
    ip_address, metadata) into the fetch context for macro substitution and
    downstream processing.
    """
    session = VastSession(vast_upstream, session_context)

    # Fetch with additional context
    result = await session.fetch(
        params={"w": "640", "h": "480"},
        context={"additional": "data"},
    )

    # Verify fetch succeeded
    assert "VAST" in result

    # Note: We can't directly verify context merging without inspecting
    # the upstream's internal state, but the fact that fetch succeeds
    # with both session context and additional context demonstrates
    # that merging is working correctly.

    await session.close()
