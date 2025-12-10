"""Tests for protocol-agnostic orchestrator."""


import pytest

from xsp.orchestrator.orchestrator import CacheBackend, Orchestrator
from xsp.orchestrator.protocol import ProtocolHandler
from xsp.orchestrator.schemas import AdRequest, AdResponse


class MockProtocolHandler(ProtocolHandler):
    """Mock protocol handler for testing."""

    def __init__(self, response: AdResponse | None = None):
        """Initialize with optional fixed response."""
        self.response = response or AdResponse(
            success=True,
            slot_id="test-slot",
            ad_id="mock-ad-123",
            creative_url="https://mock.example.com/creative.mp4",
        )
        self.fetch_called = False
        self.track_called = False
        self.validate_called = False

    async def fetch(self, request: AdRequest, **context: object) -> AdResponse:
        """Return mock response."""
        self.fetch_called = True
        # Echo slot_id from request
        response_copy = dict(self.response)
        response_copy["slot_id"] = request["slot_id"]
        return AdResponse(**response_copy)  # type: ignore

    async def track(
        self, event: str, response: AdResponse, **context: object
    ) -> None:
        """Mock tracking."""
        self.track_called = True

    def validate_request(self, request: AdRequest) -> bool:
        """Validate request has required fields."""
        self.validate_called = True
        return "slot_id" in request and "user_id" in request


class MockCache(CacheBackend):
    """Mock in-memory cache for testing."""

    def __init__(self):
        """Initialize empty cache."""
        self.cache: dict[str, AdResponse] = {}
        self.get_called = False
        self.set_called = False

    async def get(self, key: str) -> AdResponse | None:
        """Get from cache."""
        self.get_called = True
        return self.cache.get(key)

    async def set(self, key: str, value: AdResponse, ttl: int) -> None:
        """Set in cache."""
        self.set_called = True
        self.cache[key] = value


@pytest.mark.asyncio
async def test_orchestrator_fetch_success():
    """Test successful ad fetch."""
    handler = MockProtocolHandler()
    orchestrator = Orchestrator(
        protocol_handler=handler,
        enable_caching=False,
    )

    request: AdRequest = AdRequest(
        slot_id="pre-roll",
        user_id="user123",
    )

    response = await orchestrator.fetch_ad(request)

    assert response["success"] is True
    assert response["slot_id"] == "pre-roll"
    assert response["ad_id"] == "mock-ad-123"
    assert handler.fetch_called
    assert handler.validate_called


@pytest.mark.asyncio
async def test_orchestrator_validation_failure():
    """Test request validation failure."""
    handler = MockProtocolHandler()
    orchestrator = Orchestrator(protocol_handler=handler)

    # Missing user_id
    request: AdRequest = AdRequest(slot_id="pre-roll")  # type: ignore

    response = await orchestrator.fetch_ad(request)

    assert response["success"] is False
    assert "Invalid request" in response.get("error", "")
    assert not handler.fetch_called


@pytest.mark.asyncio
async def test_orchestrator_caching():
    """Test response caching."""
    handler = MockProtocolHandler()
    cache = MockCache()
    orchestrator = Orchestrator(
        protocol_handler=handler,
        cache=cache,
        enable_caching=True,
        cache_ttl=3600,
    )

    request: AdRequest = AdRequest(
        slot_id="pre-roll",
        user_id="user123",
    )

    # First fetch - should call handler
    response1 = await orchestrator.fetch_ad(request)
    assert response1["success"] is True
    assert handler.fetch_called
    assert cache.set_called
    assert response1.get("cached") is not True

    # Reset handler state
    handler.fetch_called = False

    # Second fetch - should use cache
    response2 = await orchestrator.fetch_ad(request)
    assert response2["success"] is True
    assert not handler.fetch_called  # Should not call handler again
    assert response2.get("cached") is True


@pytest.mark.asyncio
async def test_orchestrator_cache_disabled():
    """Test with caching disabled."""
    handler = MockProtocolHandler()
    cache = MockCache()
    orchestrator = Orchestrator(
        protocol_handler=handler,
        cache=cache,
        enable_caching=False,  # Disabled
    )

    request: AdRequest = AdRequest(
        slot_id="pre-roll",
        user_id="user123",
    )

    # Fetch twice
    await orchestrator.fetch_ad(request)
    handler.fetch_called = False
    await orchestrator.fetch_ad(request)

    # Handler should be called both times
    assert handler.fetch_called
    assert not cache.get_called


@pytest.mark.asyncio
async def test_orchestrator_track_event():
    """Test event tracking."""
    handler = MockProtocolHandler()
    orchestrator = Orchestrator(protocol_handler=handler)

    response: AdResponse = AdResponse(
        success=True,
        slot_id="pre-roll",
        ad_id="ad-123",
    )

    await orchestrator.track_event("impression", response)

    assert handler.track_called


def test_cache_key_generation():
    """Test cache key generation."""
    handler = MockProtocolHandler()
    orchestrator = Orchestrator(protocol_handler=handler)

    request1: AdRequest = AdRequest(
        slot_id="pre-roll",
        user_id="user123",
        device_type="mobile",
    )

    request2: AdRequest = AdRequest(
        slot_id="pre-roll",
        user_id="user123",
        device_type="mobile",
    )

    # Same request should produce same cache key
    key1 = orchestrator._make_cache_key(request1)
    key2 = orchestrator._make_cache_key(request2)

    assert key1 == key2
    assert key1.startswith("ad:")


def test_cache_key_different_requests():
    """Test cache keys differ for different requests."""
    handler = MockProtocolHandler()
    orchestrator = Orchestrator(protocol_handler=handler)

    request1: AdRequest = AdRequest(
        slot_id="pre-roll",
        user_id="user123",
    )

    request2: AdRequest = AdRequest(
        slot_id="mid-roll",
        user_id="user456",
    )

    key1 = orchestrator._make_cache_key(request1)
    key2 = orchestrator._make_cache_key(request2)

    assert key1 != key2


def test_from_config_not_implemented():
    """Test from_config raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        Orchestrator.from_config("config/test.yaml")
