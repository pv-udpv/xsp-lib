"""OpenRTB protocol handler tests."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from xsp.core import SessionContext
from xsp.protocols.openrtb import OpenRTBUpstream
from xsp.protocols.openrtb.handler import OpenRTBProtocolHandler
from xsp.transports import Transport
from xsp.orchestrator import AdRequest, AdResponse


@pytest.fixture
def mock_transport():
    """Create mock transport."""
    return AsyncMock(spec=Transport)


@pytest.fixture
def upstream(mock_transport):
    """Create OpenRTB upstream with mock transport."""
    return OpenRTBUpstream(
        transport=mock_transport,
        endpoint="https://ads.example.com/openrtb",
    )


@pytest.fixture
def handler(upstream):
    """Create OpenRTB protocol handler."""
    return OpenRTBProtocolHandler(upstream)


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


@pytest.fixture
def mock_session(upstream, session_context):
    """Create mock session."""
    import asyncio
    
    async def create_session():
        return await upstream.create_session(session_context)
    
    return asyncio.run(create_session())


class TestOpenRTBProtocolHandler:
    """Test OpenRTB protocol handler."""

    def test_handler_initialization(self, handler, upstream):
        """Test handler initialization."""
        assert handler.upstream == upstream

    @pytest.mark.asyncio
    async def test_health_check(self, handler):
        """Test health check."""
        result = await handler.health_check()
        assert result is True

    def test_map_ad_request_minimal(self, handler, mock_session):
        """Test mapping minimal AdRequest to BidRequest params."""
        ad_request: AdRequest = {"width": 300, "height": 250}
        params = handler._map_ad_request_to_params(ad_request, mock_session)

        assert params["id"] == "session-123"  # From session context
        assert params["width"] == 300
        assert params["height"] == 250

    def test_map_ad_request_with_site(self, handler, mock_session):
        """Test mapping AdRequest with site information."""
        ad_request: AdRequest = {
            "width": 300,
            "height": 250,
            "domain": "example.com",
            "page_url": "https://example.com/article",
        }
        params = handler._map_ad_request_to_params(ad_request, mock_session)

        assert params["domain"] == "example.com"
        assert params["page_url"] == "https://example.com/article"

    def test_map_ad_request_with_device(self, handler, mock_session):
        """Test mapping AdRequest with device information."""
        ad_request: AdRequest = {
            "user_agent": "Mozilla/5.0",
            "ip_address": "192.168.1.1",
        }
        params = handler._map_ad_request_to_params(ad_request, mock_session)

        assert params["user_agent"] == "Mozilla/5.0"
        assert params["ip_address"] == "192.168.1.1"

    def test_map_ad_request_with_user(self, handler, mock_session):
        """Test mapping AdRequest with user information."""
        ad_request: AdRequest = {"user_id": "user123"}
        params = handler._map_ad_request_to_params(ad_request, mock_session)

        assert params["user_id"] == "user123"

    def test_map_ad_request_with_floor(self, handler, mock_session):
        """Test mapping AdRequest with bidfloor."""
        ad_request: AdRequest = {
            "bidfloor": 1.5,
            "bidfloorcur": "USD",
        }
        params = handler._map_ad_request_to_params(ad_request, mock_session)

        assert params["bidfloor"] == 1.5
        assert params["bidfloorcur"] == "USD"

    def test_map_bid_response_empty(self, handler):
        """Test mapping empty BidResponse."""
        bid_response = {"id": "bid-123"}
        ad_request: AdRequest = {"width": 300, "height": 250}
        
        ad_response = handler._map_bid_response_to_ad_response(bid_response, ad_request)

        assert ad_response["protocol"] == "openrtb"
        assert ad_response["bid_id"] is None
        assert ad_response["price"] == 0
        assert ad_response["adm"] is None

    def test_map_bid_response_single_bid(self, handler):
        """Test mapping BidResponse with single bid."""
        bid_response = {
            "id": "bid-123",
            "seatbid": [
                {
                    "bid": [
                        {
                            "id": "bid-1",
                            "impid": "imp-1",
                            "price": 2.5,
                            "adm": "<html>Ad</html>",
                            "adomain": ["advertiser.com"],
                        }
                    ],
                    "seat": "exchange-1",
                }
            ],
        }
        ad_request: AdRequest = {"width": 300, "height": 250}
        
        ad_response = handler._map_bid_response_to_ad_response(bid_response, ad_request)

        assert ad_response["bid_id"] == "bid-1"
        assert ad_response["impid"] == "imp-1"
        assert ad_response["price"] == 2.5
        assert ad_response["adm"] == "<html>Ad</html>"
        assert ad_response["adomain"] == ["advertiser.com"]
        assert ad_response["seat"] == "exchange-1"

    def test_map_bid_response_multiple_bids_selects_highest(self, handler):
        """Test that highest bid is selected from multiple bids."""
        bid_response = {
            "id": "bid-123",
            "seatbid": [
                {
                    "bid": [
                        {"id": "bid-1", "impid": "imp-1", "price": 1.0},
                        {"id": "bid-2", "impid": "imp-2", "price": 3.5},
                        {"id": "bid-3", "impid": "imp-3", "price": 2.0},
                    ],
                    "seat": "exchange-1",
                }
            ],
        }
        ad_request: AdRequest = {}
        
        ad_response = handler._map_bid_response_to_ad_response(bid_response, ad_request)

        # Should select bid-2 with price 3.5
        assert ad_response["bid_id"] == "bid-2"
        assert ad_response["price"] == 3.5

    def test_map_bid_response_multiple_seatbids(self, handler):
        """Test selecting highest bid across multiple seatbids."""
        bid_response = {
            "id": "bid-123",
            "seatbid": [
                {
                    "bid": [{"id": "bid-1", "impid": "imp-1", "price": 1.5}],
                    "seat": "exchange-1",
                },
                {
                    "bid": [{"id": "bid-2", "impid": "imp-2", "price": 3.0}],
                    "seat": "exchange-2",
                },
            ],
        }
        ad_request: AdRequest = {}
        
        ad_response = handler._map_bid_response_to_ad_response(bid_response, ad_request)

        # Should select bid-2 from exchange-2 with price 3.0
        assert ad_response["bid_id"] == "bid-2"
        assert ad_response["seat"] == "exchange-2"
        assert ad_response["price"] == 3.0

    def test_map_bid_response_with_currency(self, handler):
        """Test currency mapping."""
        bid_response = {
            "id": "bid-123",
            "cur": "EUR",
        }
        ad_request: AdRequest = {}
        
        ad_response = handler._map_bid_response_to_ad_response(bid_response, ad_request)

        assert ad_response["currency"] == "EUR"

    def test_map_bid_response_default_currency(self, handler):
        """Test default currency when not specified."""
        bid_response = {"id": "bid-123"}
        ad_request: AdRequest = {}
        
        ad_response = handler._map_bid_response_to_ad_response(bid_response, ad_request)

        assert ad_response["currency"] == "USD"

    def test_map_bid_response_preserves_dimensions(self, handler):
        """Test that bid response preserves ad dimensions."""
        bid_response = {
            "id": "bid-123",
            "seatbid": [
                {
                    "bid": [
                        {
                            "id": "bid-1",
                            "impid": "imp-1",
                            "price": 2.5,
                            "w": 728,
                            "h": 90,
                        }
                    ],
                }
            ],
        }
        ad_request: AdRequest = {"width": 300, "height": 250}
        
        ad_response = handler._map_bid_response_to_ad_response(bid_response, ad_request)

        # Should use bid dimensions if present
        assert ad_response["w"] == 728
        assert ad_response["h"] == 90

    def test_map_bid_response_fallback_dimensions(self, handler):
        """Test fallback to request dimensions when bid doesn't specify."""
        bid_response = {
            "id": "bid-123",
            "seatbid": [
                {
                    "bid": [
                        {"id": "bid-1", "impid": "imp-1", "price": 2.5}
                    ],
                }
            ],
        }
        ad_request: AdRequest = {"width": 300, "height": 250}
        
        ad_response = handler._map_bid_response_to_ad_response(bid_response, ad_request)

        # Should fallback to request dimensions
        assert ad_response["w"] == 300
        assert ad_response["h"] == 250

    @pytest.mark.asyncio
    async def test_handle_full_flow(self, handler, upstream, session_context, mock_transport):
        """Test full handle() flow."""
        # Setup mock response
        bid_response = {
            "id": "session-123",
            "seatbid": [
                {
                    "bid": [
                        {
                            "id": "bid-1",
                            "impid": "imp-1",
                            "price": 2.5,
                            "adm": "<html>Ad</html>",
                            "adomain": ["advertiser.com"],
                        }
                    ],
                    "seat": "exchange-1",
                }
            ],
        }
        mock_transport.request.return_value = json.dumps(bid_response)

        # Create session
        session = await upstream.create_session(session_context)

        # Create ad request
        ad_request: AdRequest = {
            "width": 300,
            "height": 250,
            "domain": "example.com",
            "user_id": "user123",
        }

        # Handle request
        ad_response = await handler.handle(ad_request, session)

        # Verify response
        assert ad_response["protocol"] == "openrtb"
        assert ad_response["bid_id"] == "bid-1"
        assert ad_response["price"] == 2.5
        assert ad_response["adm"] == "<html>Ad</html>"

    @pytest.mark.asyncio
    async def test_handle_invalid_response(self, handler, upstream, session_context, mock_transport):
        """Test handle() with invalid JSON response."""
        mock_transport.request.return_value = "invalid json"

        session = await upstream.create_session(session_context)
        ad_request: AdRequest = {}

        with pytest.raises(ValueError, match="Invalid JSON"):
            await handler.handle(ad_request, session)

    @pytest.mark.asyncio
    async def test_close(self, handler, mock_transport):
        """Test closing handler."""
        await handler.close()

        assert mock_transport.close.called
