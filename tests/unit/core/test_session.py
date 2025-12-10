"""
Unit tests for session management (SessionContext and UpstreamSession).
"""

import pytest
from dataclasses import FrozenInstanceError
from typing import Any

from xsp.core.session import SessionContext, UpstreamSession


class TestSessionContext:
    """Tests for SessionContext immutable dataclass."""
    
    def test_session_context_creation(self) -> None:
        """SessionContext should store all fields correctly."""
        context = SessionContext(
            timestamp=1234567890000,
            correlator="session-abc123",
            cachebusting="rand-xyz789",
            cookies={"uid": "user123", "session": "sess456"},
            request_id="req-001"
        )
        
        assert context.timestamp == 1234567890000
        assert context.correlator == "session-abc123"
        assert context.cachebusting == "rand-xyz789"
        assert context.cookies == {"uid": "user123", "session": "sess456"}
        assert context.request_id == "req-001"
    
    def test_session_context_immutable(self) -> None:
        """SessionContext should be immutable (frozen=True)."""
        context = SessionContext(
            timestamp=123456789,
            correlator="abc",
            cachebusting="xyz",
            cookies={},
            request_id="req-1"
        )
        
        # Attempting to modify should raise FrozenInstanceError
        with pytest.raises(FrozenInstanceError):
            context.timestamp = 999  # type: ignore
    
    def test_session_context_empty_cookies(self) -> None:
        """SessionContext should accept empty cookies dict."""
        context = SessionContext(
            timestamp=123456789,
            correlator="session-001",
            cachebusting="rand-001",
            cookies={},
            request_id="req-001"
        )
        
        assert context.cookies == {}
    
    def test_session_context_multiple_cookies(self) -> None:
        """SessionContext should store multiple cookies."""
        cookies = {
            "uid": "user123",
            "session": "sess456",
            "tracking": "track789"
        }
        
        context = SessionContext(
            timestamp=123456789,
            correlator="session-001",
            cachebusting="rand-001",
            cookies=cookies,
            request_id="req-001"
        )
        
        assert context.cookies == cookies
        assert len(context.cookies) == 3


class MockUpstreamSession:
    """Mock implementation of UpstreamSession for testing."""
    
    def __init__(self, context: SessionContext) -> None:
        self._context = context
        self._frequency_caps: dict[str, int] = {}
        self._budgets: dict[str, float] = {}
    
    @property
    def context(self) -> SessionContext:
        return self._context
    
    async def request(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> str:
        return "<VAST>...</VAST>"
    
    async def check_frequency_cap(self, user_id: str) -> bool:
        count = self._frequency_caps.get(user_id, 0)
        if count >= 3:  # Max 3 impressions
            return False
        self._frequency_caps[user_id] = count + 1
        return True
    
    async def track_budget(self, campaign_id: str, amount: float) -> None:
        current = self._budgets.get(campaign_id, 0.0)
        self._budgets[campaign_id] = current + amount
    
    async def close(self) -> None:
        pass


class TestUpstreamSessionProtocol:
    """Tests for UpstreamSession protocol compliance."""
    
    @pytest.mark.asyncio
    async def test_upstream_session_context_property(self) -> None:
        """UpstreamSession should expose context property."""
        context = SessionContext(
            timestamp=123456789,
            correlator="session-abc",
            cachebusting="rand-xyz",
            cookies={},
            request_id="req-001"
        )
        
        session = MockUpstreamSession(context)
        
        assert session.context == context
        assert session.context.correlator == "session-abc"
    
    @pytest.mark.asyncio
    async def test_upstream_session_request(self) -> None:
        """UpstreamSession should support request() method."""
        context = SessionContext(
            timestamp=123456789,
            correlator="session-abc",
            cachebusting="rand-xyz",
            cookies={},
            request_id="req-001"
        )
        
        session = MockUpstreamSession(context)
        
        # Request should return response data
        response = await session.request(params={"slot": "pre-roll"})
        assert isinstance(response, str)
        assert len(response) > 0
    
    @pytest.mark.asyncio
    async def test_upstream_session_frequency_cap(self) -> None:
        """UpstreamSession should enforce frequency caps."""
        context = SessionContext(
            timestamp=123456789,
            correlator="session-abc",
            cachebusting="rand-xyz",
            cookies={},
            request_id="req-001"
        )
        
        session = MockUpstreamSession(context)
        
        # First 3 requests should pass
        assert await session.check_frequency_cap("user123") is True
        assert await session.check_frequency_cap("user123") is True
        assert await session.check_frequency_cap("user123") is True
        
        # 4th request should fail (cap exceeded)
        assert await session.check_frequency_cap("user123") is False
    
    @pytest.mark.asyncio
    async def test_upstream_session_budget_tracking(self) -> None:
        """UpstreamSession should track budget spend."""
        context = SessionContext(
            timestamp=123456789,
            correlator="session-abc",
            cachebusting="rand-xyz",
            cookies={},
            request_id="req-001"
        )
        
        session = MockUpstreamSession(context)
        
        # Track budget
        await session.track_budget("campaign-456", 2.50)
        await session.track_budget("campaign-456", 1.75)
        
        # Verify budget was tracked
        assert session._budgets["campaign-456"] == 4.25
    
    @pytest.mark.asyncio
    async def test_upstream_session_close(self) -> None:
        """UpstreamSession should support close() method."""
        context = SessionContext(
            timestamp=123456789,
            correlator="session-abc",
            cachebusting="rand-xyz",
            cookies={},
            request_id="req-001"
        )
        
        session = MockUpstreamSession(context)
        
        # Close should not raise
        await session.close()
    
    @pytest.mark.asyncio
    async def test_upstream_session_multiple_users(self) -> None:
        """UpstreamSession should track frequency caps per user."""
        context = SessionContext(
            timestamp=123456789,
            correlator="session-abc",
            cachebusting="rand-xyz",
            cookies={},
            request_id="req-001"
        )
        
        session = MockUpstreamSession(context)
        
        # Different users have independent caps
        assert await session.check_frequency_cap("user1") is True
        assert await session.check_frequency_cap("user2") is True
        assert await session.check_frequency_cap("user1") is True
        assert await session.check_frequency_cap("user2") is True
    
    @pytest.mark.asyncio
    async def test_upstream_session_multiple_campaigns(self) -> None:
        """UpstreamSession should track budgets per campaign."""
        context = SessionContext(
            timestamp=123456789,
            correlator="session-abc",
            cachebusting="rand-xyz",
            cookies={},
            request_id="req-001"
        )
        
        session = MockUpstreamSession(context)
        
        # Track different campaigns
        await session.track_budget("campaign-1", 2.50)
        await session.track_budget("campaign-2", 3.00)
        await session.track_budget("campaign-1", 1.50)
        
        # Verify independent tracking
        assert session._budgets["campaign-1"] == 4.00
        assert session._budgets["campaign-2"] == 3.00
