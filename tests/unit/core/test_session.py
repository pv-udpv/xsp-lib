"""Unit tests for session management abstractions.

Tests cover:
- SessionContext immutability and correctness
- UpstreamSession protocol compliance
- Session lifecycle
- Context preservation
"""

import time
from dataclasses import FrozenInstanceError
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from xsp.core.session import SessionContext, UpstreamSession


class TestSessionContext:
    """Tests for SessionContext immutable dataclass."""

    def test_session_context_creation(self):
        """Test basic SessionContext creation."""
        context = SessionContext(
            timestamp=1702275840000,
            correlator="session-abc123",
            cachebusting="rand-456789",
            cookies={"uid": "user123"},
            request_id="req-001"
        )

        assert context.timestamp == 1702275840000
        assert context.correlator == "session-abc123"
        assert context.cachebusting == "rand-456789"
        assert context.cookies == {"uid": "user123"}
        assert context.request_id == "req-001"

    def test_session_context_immutable(self):
        """Test that SessionContext is immutable (frozen)."""
        context = SessionContext(
            timestamp=1702275840000,
            correlator="session-abc",
            cachebusting="rand-123",
            cookies={},
            request_id="req-1"
        )

        # Attempt to modify should raise FrozenInstanceError
        with pytest.raises(FrozenInstanceError):
            context.timestamp = 9999

        with pytest.raises(FrozenInstanceError):
            context.correlator = "new-id"

        with pytest.raises(FrozenInstanceError):
            context.cachebusting = "new-cache"

        with pytest.raises(FrozenInstanceError):
            context.request_id = "new-req"

    def test_session_context_with_multiple_cookies(self):
        """Test SessionContext with multiple cookies."""
        cookies = {
            "uid": "user123",
            "session": "sess-xyz",
            "tracking": "track-456"
        }
        context = SessionContext(
            timestamp=int(time.time() * 1000),
            correlator="session-1",
            cachebusting="cache-1",
            cookies=cookies,
            request_id="req-1"
        )

        assert context.cookies == cookies
        assert len(context.cookies) == 3
        assert context.cookies["uid"] == "user123"

    def test_session_context_with_empty_cookies(self):
        """Test SessionContext with empty cookies dict."""
        context = SessionContext(
            timestamp=1702275840000,
            correlator="session-abc",
            cachebusting="rand-123",
            cookies={},
            request_id="req-1"
        )

        assert context.cookies == {}
        assert len(context.cookies) == 0

    def test_session_context_timestamp_types(self):
        """Test SessionContext with different timestamp values."""
        # Current time in milliseconds
        now_ms = int(time.time() * 1000)
        context = SessionContext(
            timestamp=now_ms,
            correlator="session-1",
            cachebusting="cache-1",
            cookies={},
            request_id="req-1"
        )

        assert isinstance(context.timestamp, int)
        assert context.timestamp > 0
        assert context.timestamp == now_ms

    def test_session_context_hashable(self):
        """Test that SessionContext is hashable (frozen dataclass)."""
        context1 = SessionContext(
            timestamp=1702275840000,
            correlator="session-abc",
            cachebusting="rand-123",
            cookies={"uid": "user1"},
            request_id="req-1"
        )

        context2 = SessionContext(
            timestamp=1702275840000,
            correlator="session-abc",
            cachebusting="rand-123",
            cookies={"uid": "user1"},
            request_id="req-1"
        )

        # Hashable
        hash1 = hash(context1)
        hash2 = hash(context2)
        assert hash1 == hash2

        # Can be used in sets
        context_set = {context1, context2}
        assert len(context_set) == 1  # Same content, should be deduplicated

    def test_session_context_repr(self):
        """Test SessionContext repr includes all fields."""
        context = SessionContext(
            timestamp=1702275840000,
            correlator="session-abc",
            cachebusting="rand-123",
            cookies={"uid": "user1"},
            request_id="req-1"
        )

        repr_str = repr(context)
        assert "SessionContext" in repr_str
        assert "1702275840000" in repr_str
        assert "session-abc" in repr_str
        assert "rand-123" in repr_str
        assert "req-1" in repr_str

    def test_session_context_equality(self):
        """Test SessionContext equality comparison."""
        context1 = SessionContext(
            timestamp=1702275840000,
            correlator="session-abc",
            cachebusting="rand-123",
            cookies={"uid": "user1"},
            request_id="req-1"
        )

        context2 = SessionContext(
            timestamp=1702275840000,
            correlator="session-abc",
            cachebusting="rand-123",
            cookies={"uid": "user1"},
            request_id="req-1"
        )

        context3 = SessionContext(
            timestamp=1702275840001,  # Different timestamp
            correlator="session-abc",
            cachebusting="rand-123",
            cookies={"uid": "user1"},
            request_id="req-1"
        )

        assert context1 == context2
        assert context1 != context3


class TestUpstreamSessionProtocol:
    """Tests for UpstreamSession protocol."""

    def test_upstream_session_protocol_has_context_property(self):
        """Test that protocol defines context property."""
        # Check protocol has context property
        assert hasattr(UpstreamSession, "context")

    def test_upstream_session_protocol_has_request_method(self):
        """Test that protocol defines request method."""
        assert hasattr(UpstreamSession, "request")

    def test_upstream_session_protocol_has_frequency_cap_method(self):
        """Test that protocol defines check_frequency_cap method."""
        assert hasattr(UpstreamSession, "check_frequency_cap")

    def test_upstream_session_protocol_has_track_budget_method(self):
        """Test that protocol defines track_budget method."""
        assert hasattr(UpstreamSession, "track_budget")

    def test_upstream_session_protocol_has_close_method(self):
        """Test that protocol defines close method."""
        assert hasattr(UpstreamSession, "close")

    def test_upstream_session_mock_implementation(self):
        """Test creating a mock UpstreamSession implementation."""
        # Create a mock implementation
        mock_session = MagicMock(spec=UpstreamSession)
        mock_session.context = SessionContext(
            timestamp=int(time.time() * 1000),
            correlator="session-1",
            cachebusting="cache-1",
            cookies={},
            request_id="req-1"
        )
        mock_session.request = AsyncMock(return_value="<VAST>...</VAST>")
        mock_session.check_frequency_cap = AsyncMock(return_value=True)
        mock_session.track_budget = AsyncMock()
        mock_session.close = AsyncMock()

        # Verify it has all required methods
        assert hasattr(mock_session, "context")
        assert hasattr(mock_session, "request")
        assert hasattr(mock_session, "check_frequency_cap")
        assert hasattr(mock_session, "track_budget")
        assert hasattr(mock_session, "close")


class TestSessionIntegration:
    """Integration tests for SessionContext with UpstreamSession."""

    @pytest.mark.asyncio
    async def test_session_lifecycle(self):
        """Test complete session lifecycle."""
        # Create context
        context = SessionContext(
            timestamp=int(time.time() * 1000),
            correlator="session-lifecycle",
            cachebusting="cache-lifecycle",
            cookies={"uid": "user-lifecycle"},
            request_id="req-lifecycle"
        )

        # Create mock session
        mock_session = MagicMock(spec=UpstreamSession)
        mock_session.context = context
        mock_session.request = AsyncMock(return_value="<VAST>...</VAST>")
        mock_session.check_frequency_cap = AsyncMock(return_value=True)
        mock_session.track_budget = AsyncMock()
        mock_session.close = AsyncMock()

        # Use session
        assert mock_session.context.correlator == "session-lifecycle"

        if await mock_session.check_frequency_cap("user-lifecycle"):
            response = await mock_session.request(params={"slot": "pre-roll"})
            assert response == "<VAST>...</VAST>"

            await mock_session.track_budget("campaign-1", 2.50)
            mock_session.track_budget.assert_called_once_with("campaign-1", 2.50)

        # Cleanup
        await mock_session.close()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_with_frequency_cap_exceeded(self):
        """Test session when frequency cap is exceeded."""
        context = SessionContext(
            timestamp=int(time.time() * 1000),
            correlator="session-cap-exceeded",
            cachebusting="cache-1",
            cookies={},
            request_id="req-1"
        )

        # Mock session with frequency cap exceeded
        mock_session = MagicMock(spec=UpstreamSession)
        mock_session.context = context
        mock_session.check_frequency_cap = AsyncMock(return_value=False)
        mock_session.request = AsyncMock()  # Should not be called
        mock_session.close = AsyncMock()

        # Frequency cap exceeded, should not request
        if await mock_session.check_frequency_cap("user-1"):
            await mock_session.request(params={"slot": "pre-roll"})
        else:
            # Cap exceeded, don't request
            pass

        # request should not have been called
        mock_session.request.assert_not_called()

        await mock_session.close()
        mock_session.close.assert_called_once()


class TestSessionContextEdgeCases:
    """Edge case tests for SessionContext."""

    def test_session_context_with_special_characters_in_strings(self):
        """Test SessionContext with special characters in string fields."""
        context = SessionContext(
            timestamp=1702275840000,
            correlator="session-abc!@#$%^&*()",
            cachebusting="rand-!@#",
            cookies={"special": "value!@#"},
            request_id="req-!@#"
        )

        assert "!@#$%^&*()" in context.correlator
        assert "!@#" in context.cachebusting
        assert context.cookies["special"] == "value!@#"

    def test_session_context_with_unicode_characters(self):
        """Test SessionContext with Unicode characters."""
        context = SessionContext(
            timestamp=1702275840000,
            correlator="session-русский",
            cachebusting="cache-中文",
            cookies={"lang": "中文"},
            request_id="req-рус"
        )

        assert "русский" in context.correlator
        assert "中文" in context.cachebusting

    def test_session_context_with_large_timestamp(self):
        """Test SessionContext with very large timestamp."""
        # Year 2100 in milliseconds
        year_2100_ms = 4102444800000
        context = SessionContext(
            timestamp=year_2100_ms,
            correlator="session-future",
            cachebusting="cache-1",
            cookies={},
            request_id="req-1"
        )

        assert context.timestamp == year_2100_ms

    def test_session_context_with_many_cookies(self):
        """Test SessionContext with many cookies."""
        cookies = {f"cookie_{i}": f"value_{i}" for i in range(100)}
        context = SessionContext(
            timestamp=1702275840000,
            correlator="session-many-cookies",
            cachebusting="cache-1",
            cookies=cookies,
            request_id="req-1"
        )

        assert len(context.cookies) == 100
        assert context.cookies["cookie_0"] == "value_0"
        assert context.cookies["cookie_99"] == "value_99"
