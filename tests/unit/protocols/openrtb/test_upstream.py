"""OpenRTB upstream unit tests."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from xsp.core import SessionContext
from xsp.protocols.openrtb import OpenRTBUpstream
from xsp.transports import Transport


@pytest.fixture
def mock_transport():
    """Create mock transport."""
    transport = AsyncMock(spec=Transport)
    return transport


@pytest.fixture
def upstream(mock_transport):
    """Create OpenRTB upstream with mock transport."""
    return OpenRTBUpstream(
        transport=mock_transport,
        endpoint="https://ads.example.com/openrtb",
    )


@pytest.fixture
def session_context():
    """Create session context."""
    return SessionContext(
        timestamp=1234567890000,
        correlator="session-123",
        cachebusting="rand-xyz",
        cookies={"uid": "user123"},
        request_id="req-001",
    )


class TestOpenRTBUpstream:
    """Test OpenRTB upstream."""

    def test_upstream_initialization(self, mock_transport):
        """Test upstream initialization."""
        upstream = OpenRTBUpstream(
            transport=mock_transport,
            endpoint="https://ads.example.com/openrtb",
        )
        assert upstream.endpoint == "https://ads.example.com/openrtb"
        assert upstream.transport == mock_transport

    @pytest.mark.asyncio
    async def test_build_bid_request_minimal(self, upstream):
        """Test building minimal BidRequest."""
        params = {"id": "bid-123"}
        bid_request = upstream._build_bid_request(params)

        assert bid_request["id"] == "bid-123"
        assert "imp" in bid_request
        assert len(bid_request["imp"]) > 0

    @pytest.mark.asyncio
    async def test_build_bid_request_with_banner(self, upstream):
        """Test building BidRequest with banner."""
        params = {
            "id": "bid-123",
            "width": 300,
            "height": 250,
        }
        bid_request = upstream._build_bid_request(params)

        assert bid_request["id"] == "bid-123"
        assert "imp" in bid_request
        assert bid_request["imp"][0]["banner"]["w"] == 300
        assert bid_request["imp"][0]["banner"]["h"] == 250

    @pytest.mark.asyncio
    async def test_build_bid_request_with_site(self, upstream):
        """Test building BidRequest with site."""
        params = {
            "id": "bid-123",
            "domain": "example.com",
            "page_url": "https://example.com/article",
        }
        bid_request = upstream._build_bid_request(params)

        assert bid_request["site"]["domain"] == "example.com"
        assert bid_request["site"]["page"] == "https://example.com/article"

    @pytest.mark.asyncio
    async def test_build_bid_request_with_device(self, upstream):
        """Test building BidRequest with device."""
        params = {
            "id": "bid-123",
            "user_agent": "Mozilla/5.0",
            "ip_address": "192.168.1.1",
        }
        bid_request = upstream._build_bid_request(params)

        assert bid_request["device"]["ua"] == "Mozilla/5.0"
        assert bid_request["device"]["ip"] == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_build_bid_request_with_user(self, upstream):
        """Test building BidRequest with user."""
        params = {
            "id": "bid-123",
            "user_id": "user123",
        }
        bid_request = upstream._build_bid_request(params)

        assert bid_request["user"]["id"] == "user123"

    @pytest.mark.asyncio
    async def test_build_bid_request_with_bidfloor(self, upstream):
        """Test building BidRequest with bidfloor."""
        params = {
            "id": "bid-123",
            "bidfloor": 1.5,
            "bidfloorcur": "USD",
        }
        bid_request = upstream._build_bid_request(params)

        assert bid_request["imp"][0]["bidfloor"] == 1.5
        assert bid_request["imp"][0]["bidfloorcur"] == "USD"

    @pytest.mark.asyncio
    async def test_request_sends_to_transport(self, upstream, mock_transport):
        """Test request sends BidRequest to transport."""
        response_json = json.dumps({"id": "bid-123", "seatbid": []})
        mock_transport.request.return_value = response_json

        result = await upstream.request(
            params={"id": "bid-123"},
            headers={"User-Agent": "test"},
        )

        assert result == response_json
        assert mock_transport.request.called

    @pytest.mark.asyncio
    async def test_request_invalid_json_response(self, upstream, mock_transport):
        """Test request raises on invalid JSON response."""
        mock_transport.request.return_value = "invalid json"

        with pytest.raises(ValueError, match="Invalid JSON"):
            await upstream.request(params={"id": "bid-123"})

    @pytest.mark.asyncio
    async def test_create_session(self, upstream, session_context):
        """Test creating session."""
        session = await upstream.create_session(session_context)

        assert session.context == session_context
        assert session.context.correlator == "session-123"

    @pytest.mark.asyncio
    async def test_session_request(self, upstream, session_context, mock_transport):
        """Test sending request through session."""
        response_json = json.dumps({"id": "session-123", "seatbid": []})
        mock_transport.request.return_value = response_json

        session = await upstream.create_session(session_context)
        result = await session.request(params={"width": 300})

        assert result == response_json

    @pytest.mark.asyncio
    async def test_session_close(self, upstream, session_context):
        """Test closing session."""
        session = await upstream.create_session(session_context)
        await session.close()

        # Verify session is marked closed
        with pytest.raises(RuntimeError, match="closed"):
            await session.request()

    @pytest.mark.asyncio
    async def test_frequency_cap_always_true(self, upstream, session_context):
        """Test frequency cap (MVP: always returns True)."""
        session = await upstream.create_session(session_context)
        result = await session.check_frequency_cap("user123")

        assert result is True

    @pytest.mark.asyncio
    async def test_track_budget_noop(self, upstream, session_context):
        """Test budget tracking (MVP: no-op)."""
        session = await upstream.create_session(session_context)
        await session.track_budget("campaign-123", 2.5)

        # Should not raise
        assert True

    @pytest.mark.asyncio
    async def test_upstream_close(self, upstream, mock_transport):
        """Test closing upstream."""
        await upstream.close()

        assert mock_transport.close.called
