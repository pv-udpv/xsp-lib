"""Unit tests for session management."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

import pytest

from xsp.core.session import SessionContext, UpstreamSession


class TestSessionContext:
    """Test suite for SessionContext."""

    def test_create_default(self) -> None:
        """Test creating SessionContext with default values."""
        context = SessionContext.create()

        assert context.timestamp > 0
        assert context.correlator
        assert context.cachebusting
        assert context.request_id.startswith("req-")
        assert context.cookies == {}

    def test_create_with_cookies(self) -> None:
        """Test creating SessionContext with custom cookies."""
        cookies = {"user_id": "123", "session_id": "abc"}
        context = SessionContext.create(cookies=cookies)

        assert context.cookies == cookies
        assert context.timestamp > 0
        assert context.correlator

    def test_timestamp_in_milliseconds(self) -> None:
        """Test that timestamp is in milliseconds (VAST macro format)."""
        before = int(datetime.now(timezone.utc).timestamp() * 1000)
        context = SessionContext.create()
        after = int(datetime.now(timezone.utc).timestamp() * 1000)

        assert before <= context.timestamp <= after

    def test_correlator_is_uuid(self) -> None:
        """Test that correlator is a valid UUID."""
        context = SessionContext.create()

        # Should not raise ValueError
        uuid.UUID(context.correlator)

    def test_cachebusting_is_uuid(self) -> None:
        """Test that cachebusting is a valid UUID."""
        context = SessionContext.create()

        # Should not raise ValueError
        uuid.UUID(context.cachebusting)

    def test_request_id_format(self) -> None:
        """Test that request_id has correct format."""
        context = SessionContext.create()

        assert context.request_id.startswith("req-")
        # Extract UUID part and validate
        uuid_part = context.request_id[4:]  # Remove "req-" prefix
        uuid.UUID(uuid_part)  # Should not raise ValueError

    def test_unique_values_per_instance(self) -> None:
        """Test that each SessionContext has unique values."""
        context1 = SessionContext.create()
        context2 = SessionContext.create()

        assert context1.correlator != context2.correlator
        assert context1.cachebusting != context2.cachebusting
        assert context1.request_id != context2.request_id

    def test_immutable(self) -> None:
        """Test that SessionContext is immutable (frozen dataclass)."""
        context = SessionContext.create()

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            context.timestamp = 999  # type: ignore

        with pytest.raises(Exception):
            context.correlator = "new-correlator"  # type: ignore

    def test_cookies_not_shared_across_instances(self) -> None:
        """Test that cookies dict is not shared between instances."""
        cookies1 = {"user_id": "123"}
        context1 = SessionContext.create(cookies=cookies1)

        cookies2 = {"user_id": "456"}
        context2 = SessionContext.create(cookies=cookies2)

        assert context1.cookies != context2.cookies
        assert context1.cookies == {"user_id": "123"}
        assert context2.cookies == {"user_id": "456"}

    def test_empty_cookies_by_default(self) -> None:
        """Test that cookies are empty dict when not provided."""
        context = SessionContext.create()

        assert context.cookies == {}
        assert isinstance(context.cookies, dict)


class TestUpstreamSession:
    """Test suite for UpstreamSession protocol."""

    @pytest.mark.asyncio
    async def test_protocol_compliance_request(self) -> None:
        """Test that UpstreamSession protocol includes request() method."""

        class MockUpstreamSession:
            """Mock implementation of UpstreamSession."""

            async def request(
                self,
                context: SessionContext,
                **kwargs: Any,
            ) -> Any:
                return {"result": "success"}

            async def check_frequency_cap(
                self,
                user_id: str,
                campaign_id: str,
            ) -> bool:
                return True

            async def track_budget(
                self,
                campaign_id: str,
                cost: Decimal,
            ) -> bool:
                return True

        # Create mock session
        session: UpstreamSession = MockUpstreamSession()
        context = SessionContext.create()

        # Test request method
        result = await session.request(context, params={"test": "value"})
        assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_protocol_compliance_check_frequency_cap(self) -> None:
        """Test that UpstreamSession protocol includes check_frequency_cap() method."""

        class MockUpstreamSession:
            """Mock implementation of UpstreamSession."""

            async def request(
                self,
                context: SessionContext,
                **kwargs: Any,
            ) -> Any:
                return {}

            async def check_frequency_cap(
                self,
                user_id: str,
                campaign_id: str,
            ) -> bool:
                return user_id != "blocked_user"

            async def track_budget(
                self,
                campaign_id: str,
                cost: Decimal,
            ) -> bool:
                return True

        session: UpstreamSession = MockUpstreamSession()

        # Test check_frequency_cap
        can_serve = await session.check_frequency_cap("user123", "campaign456")
        assert can_serve is True

        blocked = await session.check_frequency_cap("blocked_user", "campaign456")
        assert blocked is False

    @pytest.mark.asyncio
    async def test_protocol_compliance_track_budget(self) -> None:
        """Test that UpstreamSession protocol includes track_budget() method."""

        class MockUpstreamSession:
            """Mock implementation of UpstreamSession."""

            def __init__(self) -> None:
                self.budget = Decimal("100.00")
                self.spent = Decimal("0.00")

            async def request(
                self,
                context: SessionContext,
                **kwargs: Any,
            ) -> Any:
                return {}

            async def check_frequency_cap(
                self,
                user_id: str,
                campaign_id: str,
            ) -> bool:
                return True

            async def track_budget(
                self,
                campaign_id: str,
                cost: Decimal,
            ) -> bool:
                if self.spent + cost > self.budget:
                    return False
                self.spent += cost
                return True

        session: UpstreamSession = MockUpstreamSession()

        # Track budget
        result1 = await session.track_budget("campaign123", Decimal("50.00"))
        assert result1 is True

        result2 = await session.track_budget("campaign123", Decimal("40.00"))
        assert result2 is True

        # Should fail (exceeds budget)
        result3 = await session.track_budget("campaign123", Decimal("20.00"))
        assert result3 is False

    @pytest.mark.asyncio
    async def test_upstream_session_with_mocks(self) -> None:
        """Test UpstreamSession with AsyncMock."""

        # Create mock session using AsyncMock
        mock_session = AsyncMock(spec=UpstreamSession)
        mock_session.request.return_value = {"ad": "creative"}
        mock_session.check_frequency_cap.return_value = True
        mock_session.track_budget.return_value = True

        context = SessionContext.create()

        # Test request
        response = await mock_session.request(context, params={"test": "value"})
        assert response == {"ad": "creative"}
        mock_session.request.assert_called_once()

        # Test frequency cap
        can_serve = await mock_session.check_frequency_cap("user123", "campaign456")
        assert can_serve is True
        mock_session.check_frequency_cap.assert_called_once_with("user123", "campaign456")

        # Test budget tracking
        budget_ok = await mock_session.track_budget("campaign456", Decimal("1.50"))
        assert budget_ok is True
        mock_session.track_budget.assert_called_once_with("campaign456", Decimal("1.50"))
