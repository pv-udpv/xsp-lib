"""Tests for OpenRTB upstream implementation."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from xsp.core.session import SessionContext
from xsp.protocols.openrtb.upstream import OpenRTBSession, OpenRTBUpstream


class TestOpenRTBUpstream:
    """Tests for OpenRTBUpstream."""

    @pytest.fixture
    def mock_transport(self) -> MagicMock:
        """Create mock transport."""
        transport = MagicMock()
        transport.request = AsyncMock()
        return transport

    @pytest.fixture
    def upstream(self, mock_transport: MagicMock) -> OpenRTBUpstream:
        """Create OpenRTB upstream instance."""
        return OpenRTBUpstream(
            transport=mock_transport,
            endpoint="https://bidder.example.com/rtb"
        )

    def test_init(self, upstream: OpenRTBUpstream) -> None:
        """Test upstream initialization."""
        assert upstream.endpoint == "https://bidder.example.com/rtb"
        assert upstream.encoder is not None
        assert upstream.decoder is not None

    def test_build_bid_request_minimal(self, upstream: OpenRTBUpstream) -> None:
        """Test building minimal BidRequest."""
        params = {
            "id": "req123",
            "imp": [{"id": "imp1", "banner": {"w": 300, "h": 250}}],
        }
        bid_request = upstream._build_bid_request(params)

        assert bid_request["id"] == "req123"
        assert len(bid_request["imp"]) == 1
        assert bid_request["imp"][0]["id"] == "imp1"

    def test_build_bid_request_with_banner(self, upstream: OpenRTBUpstream) -> None:
        """Test building BidRequest with banner impression."""
        params = {
            "id": "req123",
            "imp": [
                {
                    "id": "imp1",
                    "banner": {"w": 728, "h": 90},
                    "tagid": "banner-slot-1",
                }
            ],
        }
        bid_request = upstream._build_bid_request(params)

        assert bid_request["imp"][0]["banner"] == {"w": 728, "h": 90}
        assert bid_request["imp"][0]["tagid"] == "banner-slot-1"

    def test_build_bid_request_with_site(self, upstream: OpenRTBUpstream) -> None:
        """Test building BidRequest with site."""
        params = {
            "id": "req123",
            "imp": [{"id": "imp1"}],
            "site": {
                "domain": "example.com",
                "page": "https://example.com/article",
            },
        }
        bid_request = upstream._build_bid_request(params)

        assert "site" in bid_request
        assert bid_request["site"]["domain"] == "example.com"
        assert bid_request["site"]["page"] == "https://example.com/article"

    def test_build_bid_request_with_device(self, upstream: OpenRTBUpstream) -> None:
        """Test building BidRequest with device."""
        params = {
            "id": "req123",
            "imp": [{"id": "imp1"}],
            "device": {
                "ua": "Mozilla/5.0",
                "ip": "192.168.1.1",
            },
        }
        bid_request = upstream._build_bid_request(params)

        assert "device" in bid_request
        assert bid_request["device"]["ua"] == "Mozilla/5.0"
        assert bid_request["device"]["ip"] == "192.168.1.1"

    def test_build_bid_request_with_user(self, upstream: OpenRTBUpstream) -> None:
        """Test building BidRequest with user."""
        params = {
            "id": "req123",
            "imp": [{"id": "imp1"}],
            "user": {"id": "user123"},
        }
        bid_request = upstream._build_bid_request(params)

        assert "user" in bid_request
        assert bid_request["user"]["id"] == "user123"

    def test_build_bid_request_with_bidfloor(self, upstream: OpenRTBUpstream) -> None:
        """Test building BidRequest with bid floor."""
        params = {
            "id": "req123",
            "imp": [
                {
                    "id": "imp1",
                    "bidfloor": 1.50,
                    "bidfloorcur": "USD",
                }
            ],
        }
        bid_request = upstream._build_bid_request(params)

        assert bid_request["imp"][0]["bidfloor"] == 1.50
        assert bid_request["imp"][0]["bidfloorcur"] == "USD"

    def test_build_bid_request_missing_id(self, upstream: OpenRTBUpstream) -> None:
        """Test building BidRequest without id raises error."""
        params = {"imp": [{"id": "imp1"}]}

        with pytest.raises(ValueError, match="must have 'id' field"):
            upstream._build_bid_request(params)

    def test_build_bid_request_missing_imp(self, upstream: OpenRTBUpstream) -> None:
        """Test building BidRequest without impressions raises error."""
        params = {"id": "req123"}

        with pytest.raises(ValueError, match="must have at least one impression"):
            upstream._build_bid_request(params)

    @pytest.mark.asyncio
    async def test_request_sends_to_transport(
        self,
        upstream: OpenRTBUpstream,
        mock_transport: MagicMock
    ) -> None:
        """Test request sends BidRequest to transport."""
        # Setup mock response
        response_data = {
            "id": "req123",
            "seatbid": [
                {"bid": [{"impid": "imp1", "price": 2.50}]}
            ],
        }
        mock_transport.request.return_value = json.dumps(response_data).encode("utf-8")

        # Send request
        params = {
            "id": "req123",
            "imp": [{"id": "imp1", "banner": {"w": 300, "h": 250}}],
        }
        response = await upstream.request(params=params)

        # Verify transport was called
        assert mock_transport.request.called

        # Verify response is JSON string
        response_obj = json.loads(response)
        assert response_obj["id"] == "req123"
        assert response_obj["seatbid"][0]["bid"][0]["price"] == 2.50

    @pytest.mark.asyncio
    async def test_request_without_params_raises_error(
        self,
        upstream: OpenRTBUpstream
    ) -> None:
        """Test request without params raises ValueError."""
        with pytest.raises(ValueError, match="params dict is required"):
            await upstream.request()

    @pytest.mark.asyncio
    async def test_create_session(self, upstream: OpenRTBUpstream) -> None:
        """Test creating session."""
        context = SessionContext(
            timestamp=1702275840000,
            correlator="sess-123",
            cachebusting="rand456",
            cookies={"uid": "user789"},
            request_id="req-001"
        )

        session = await upstream.create_session(context)

        assert isinstance(session, OpenRTBSession)
        assert session.context == context


class TestOpenRTBSession:
    """Tests for OpenRTBSession."""

    @pytest.fixture
    def mock_transport(self) -> MagicMock:
        """Create mock transport."""
        transport = MagicMock()
        transport.request = AsyncMock()
        return transport

    @pytest.fixture
    def upstream(self, mock_transport: MagicMock) -> OpenRTBUpstream:
        """Create OpenRTB upstream instance."""
        return OpenRTBUpstream(
            transport=mock_transport,
            endpoint="https://bidder.example.com/rtb"
        )

    @pytest.fixture
    def context(self) -> SessionContext:
        """Create session context."""
        return SessionContext(
            timestamp=1702275840000,
            correlator="sess-123",
            cachebusting="rand456",
            cookies={"uid": "user789", "session": "abc"},
            request_id="req-001"
        )

    @pytest.fixture
    async def session(
        self,
        upstream: OpenRTBUpstream,
        context: SessionContext
    ) -> OpenRTBSession:
        """Create session instance."""
        return await upstream.create_session(context)

    def test_context_property(
        self,
        session: OpenRTBSession,
        context: SessionContext
    ) -> None:
        """Test accessing session context."""
        assert session.context == context
        assert session.context.correlator == "sess-123"

    @pytest.mark.asyncio
    async def test_request_merges_cookies(
        self,
        session: OpenRTBSession,
        mock_transport: MagicMock
    ) -> None:
        """Test request merges session cookies into headers."""
        # Setup mock response
        mock_transport.request.return_value = json.dumps({"id": "req123"}).encode("utf-8")

        # Send request
        params = {
            "id": "req123",
            "imp": [{"id": "imp1"}],
        }
        await session.request(params=params)

        # Verify transport was called
        assert mock_transport.request.called

    @pytest.mark.asyncio
    async def test_check_frequency_cap_always_true(
        self,
        session: OpenRTBSession
    ) -> None:
        """Test frequency cap check always returns True in MVP."""
        result = await session.check_frequency_cap("user123")
        assert result is True

        # Check with explicit limit
        result = await session.check_frequency_cap("user123", limit=3, window_seconds=3600)
        assert result is True

    @pytest.mark.asyncio
    async def test_track_budget_no_op(self, session: OpenRTBSession) -> None:
        """Test budget tracking is no-op in MVP."""
        # Should not raise any errors
        await session.track_budget("campaign-456", 2.50)
        await session.track_budget("campaign-789", 5.00, currency="EUR")

    @pytest.mark.asyncio
    async def test_close_session(self, session: OpenRTBSession) -> None:
        """Test closing session."""
        await session.close()

        # After close, requests should fail
        with pytest.raises(RuntimeError, match="Cannot request on closed session"):
            await session.request(params={"id": "req123", "imp": [{"id": "imp1"}]})
