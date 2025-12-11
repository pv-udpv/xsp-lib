"""Tests for OpenRTB protocol handler.

Tests cover request mapping, response parsing, and end-to-end handler behavior
for OpenRTB 2.6 protocol integration with the orchestrator framework.

References:
    - OpenRTB 2.6 Specification: https://www.iab.com/wp-content/uploads/2016/03/OpenRTB-API-Specification-Version-2-6-FINAL.pdf
"""

from unittest.mock import AsyncMock

import pytest

from xsp.core.exceptions import OpenRTBNoBidError
from xsp.orchestrator.schemas import AdRequest, AdResponse
from xsp.protocols.openrtb import OpenRTBProtocolHandler
from xsp.protocols.openrtb.types import BidResponse


@pytest.fixture
def mock_upstream() -> AsyncMock:
    """Create mock OpenRTBUpstream for testing."""
    upstream = AsyncMock()
    upstream.close = AsyncMock()
    upstream.health_check = AsyncMock(return_value=True)
    return upstream


@pytest.fixture
def minimal_ad_request() -> AdRequest:
    """Minimal valid AdRequest."""
    return {
        "slot_id": "test-slot-123",
        "user_id": "user-456",
    }


@pytest.fixture
def full_ad_request() -> AdRequest:
    """Full AdRequest with all optional fields."""
    return {
        "slot_id": "banner-top",
        "user_id": "user-789",
        "ip_address": "203.0.113.1",
        "device_type": "mobile",
        "content_url": "https://example.com/page",
        "player_size": (728, 90),
        "geo": {
            "lat": 37.7749,
            "lon": -122.4194,
            "country": "USA",
            "region": "CA",
            "city": "San Francisco",
            "zip": "94102",
        },
        "extensions": {
            "bid_floor": 1.50,
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)",
            "buyer_uid": "buyer-123",
            "user_keywords": "sports,technology",
            "site_name": "Example Site",
            "site_categories": ["IAB1", "IAB12"],
        },
    }


@pytest.fixture
def sample_bid_response() -> BidResponse:
    """Sample successful BidResponse."""
    return {
        "id": "req-123",
        "seatbid": [
            {
                "bid": [
                    {
                        "id": "bid-1",
                        "impid": "imp-0",
                        "price": 2.5,
                        "adm": "<html><body><h1>Ad Content</h1></body></html>",
                        "adomain": ["advertiser.com"],
                        "cid": "campaign-456",
                        "crid": "creative-789",
                        "w": 728,
                        "h": 90,
                        "nurl": "https://win.example.com/win?price=${AUCTION_PRICE}",
                    }
                ]
            }
        ],
        "cur": "USD",
        "bidid": "bid-response-123",
    }


@pytest.fixture
def multi_bid_response() -> BidResponse:
    """BidResponse with multiple bids and seats."""
    return {
        "id": "req-456",
        "seatbid": [
            {
                "seat": "seat1",
                "bid": [
                    {
                        "id": "bid-1",
                        "impid": "imp-0",
                        "price": 1.5,
                        "adm": "<html>Ad 1</html>",
                        "adomain": ["advertiser1.com"],
                    },
                    {
                        "id": "bid-2",
                        "impid": "imp-0",
                        "price": 2.0,
                        "adm": "<html>Ad 2</html>",
                        "adomain": ["advertiser2.com"],
                    },
                ],
            },
            {
                "seat": "seat2",
                "bid": [
                    {
                        "id": "bid-3",
                        "impid": "imp-0",
                        "price": 3.5,
                        "adm": "<html>Ad 3</html>",
                        "adomain": ["advertiser3.com"],
                    }
                ],
            },
        ],
        "cur": "USD",
    }


# ============================================================================
# Request Mapping Tests (_build_bid_request)
# ============================================================================


@pytest.mark.asyncio
async def test_build_bid_request_minimal(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest
) -> None:
    """Test _build_bid_request with minimal required fields."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    bid_request = handler._build_bid_request(minimal_ad_request)

    # Verify required fields
    assert "id" in bid_request
    assert "imp" in bid_request
    assert len(bid_request["imp"]) == 1

    # Verify impression
    imp = bid_request["imp"][0]
    assert "id" in imp
    assert imp["tagid"] == "test-slot-123"

    # Verify user
    assert "user" in bid_request
    assert bid_request["user"]["id"] == "user-456"


@pytest.mark.asyncio
async def test_build_bid_request_with_site(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest
) -> None:
    """Test _build_bid_request with site information."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    ad_request = minimal_ad_request.copy()
    ad_request["content_url"] = "https://example.com/page"

    bid_request = handler._build_bid_request(ad_request)

    # Verify site object
    assert "site" in bid_request
    assert bid_request["site"]["page"] == "https://example.com/page"
    assert bid_request["site"]["domain"] == "example.com"


@pytest.mark.asyncio
async def test_build_bid_request_with_device(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest
) -> None:
    """Test _build_bid_request with device information."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    ad_request = minimal_ad_request.copy()
    ad_request["ip_address"] = "203.0.113.1"
    ad_request["device_type"] = "mobile"
    ad_request["extensions"] = {"user_agent": "Mozilla/5.0 (iPhone)"}

    bid_request = handler._build_bid_request(ad_request)

    # Verify device object
    assert "device" in bid_request
    assert bid_request["device"]["ip"] == "203.0.113.1"
    assert bid_request["device"]["devicetype"] == 4  # PHONE
    assert bid_request["device"]["ua"] == "Mozilla/5.0 (iPhone)"


@pytest.mark.asyncio
async def test_build_bid_request_with_user(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest
) -> None:
    """Test _build_bid_request with additional user fields."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    ad_request = minimal_ad_request.copy()
    ad_request["extensions"] = {
        "buyer_uid": "buyer-123",
        "user_keywords": "sports,technology",
    }

    bid_request = handler._build_bid_request(ad_request)

    # Verify user object
    assert "user" in bid_request
    assert bid_request["user"]["id"] == "user-456"
    assert bid_request["user"]["buyeruid"] == "buyer-123"
    assert bid_request["user"]["keywords"] == "sports,technology"


@pytest.mark.asyncio
async def test_build_bid_request_with_floor(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest
) -> None:
    """Test _build_bid_request with bid floor in extensions."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    ad_request = minimal_ad_request.copy()
    ad_request["extensions"] = {"bid_floor": 1.50}

    bid_request = handler._build_bid_request(ad_request)

    # Verify impression has bid floor
    imp = bid_request["imp"][0]
    assert "bidfloor" in imp
    assert imp["bidfloor"] == 1.50


@pytest.mark.asyncio
async def test_build_bid_request_with_geo(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest
) -> None:
    """Test _build_bid_request with geographic information."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    ad_request = minimal_ad_request.copy()
    ad_request["geo"] = {
        "lat": 37.7749,
        "lon": -122.4194,
        "country": "USA",
        "region": "CA",
        "city": "San Francisco",
        "zip": "94102",
    }

    bid_request = handler._build_bid_request(ad_request)

    # Verify device geo
    assert "device" in bid_request
    assert "geo" in bid_request["device"]
    geo = bid_request["device"]["geo"]
    assert geo["lat"] == 37.7749
    assert geo["lon"] == -122.4194
    assert geo["country"] == "USA"
    assert geo["region"] == "CA"
    assert geo["city"] == "San Francisco"
    assert geo["zip"] == "94102"


@pytest.mark.asyncio
async def test_build_bid_request_with_dimensions(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest
) -> None:
    """Test _build_bid_request with player_size for banner dimensions."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    ad_request = minimal_ad_request.copy()
    ad_request["player_size"] = (728, 90)

    bid_request = handler._build_bid_request(ad_request)

    # Verify impression has banner dimensions
    imp = bid_request["imp"][0]
    assert "banner" in imp
    assert imp["banner"]["w"] == 728
    assert imp["banner"]["h"] == 90


# ============================================================================
# Response Parsing Tests (_build_ad_response)
# ============================================================================


@pytest.mark.asyncio
async def test_build_ad_response_empty_seatbid(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest
) -> None:
    """Test _build_ad_response with empty seatbid array."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    bid_response: BidResponse = {
        "id": "req-123",
        "seatbid": [],
        "cur": "USD",
    }

    with pytest.raises(OpenRTBNoBidError) as exc_info:
        handler._build_ad_response(minimal_ad_request, bid_response)

    assert "no seatbid" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_build_ad_response_single_bid(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest, sample_bid_response: BidResponse
) -> None:
    """Test _build_ad_response with single bid."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    ad_response = handler._build_ad_response(minimal_ad_request, sample_bid_response)

    # Verify success
    assert ad_response["success"] is True
    assert ad_response["slot_id"] == "test-slot-123"

    # Verify bid details preserved
    assert ad_response["ad_id"] == "bid-1"
    assert ad_response["creative_type"] == "display/html"
    assert ad_response["raw_response"] == "<html><body><h1>Ad Content</h1></body></html>"
    assert ad_response["advertiser"] == "advertiser.com"
    assert ad_response["campaign_id"] == "campaign-456"
    assert ad_response["dimensions"] == (728, 90)

    # Verify extensions
    assert "extensions" in ad_response
    ext = ad_response["extensions"]
    assert ext["bid_price"] == 2.5
    assert ext["currency"] == "USD"
    assert ext["creative_id"] == "creative-789"
    assert ext["nurl"] == "https://win.example.com/win?price=${AUCTION_PRICE}"


@pytest.mark.asyncio
async def test_build_ad_response_multiple_bids_same_seat(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest
) -> None:
    """Test _build_ad_response with multiple bids in same seatbid."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    bid_response: BidResponse = {
        "id": "req-456",
        "seatbid": [
            {
                "bid": [
                    {"id": "bid-1", "impid": "imp-0", "price": 1.5, "adm": "<html>Ad 1</html>"},
                    {"id": "bid-2", "impid": "imp-0", "price": 3.0, "adm": "<html>Ad 2</html>"},
                    {"id": "bid-3", "impid": "imp-0", "price": 2.0, "adm": "<html>Ad 3</html>"},
                ]
            }
        ],
        "cur": "USD",
    }

    ad_response = handler._build_ad_response(minimal_ad_request, bid_response)

    # Verify highest price wins
    assert ad_response["success"] is True
    assert ad_response["ad_id"] == "bid-2"
    assert ad_response["extensions"]["bid_price"] == 3.0


@pytest.mark.asyncio
async def test_build_ad_response_multiple_seatbids(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest, multi_bid_response: BidResponse
) -> None:
    """Test _build_ad_response with multiple seatbids."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    ad_response = handler._build_ad_response(minimal_ad_request, multi_bid_response)

    # Verify highest price across all seats wins
    assert ad_response["success"] is True
    assert ad_response["extensions"]["bid_price"] == 3.5
    assert ad_response["advertiser"] == "advertiser3.com"


@pytest.mark.asyncio
async def test_build_ad_response_highest_price_wins(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest
) -> None:
    """Test _build_ad_response selects highest-priced bid."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    bid_response: BidResponse = {
        "id": "req-789",
        "seatbid": [
            {"bid": [{"id": "bid-1", "impid": "imp-0", "price": 1.0, "adm": "Ad 1"}]},
            {"bid": [{"id": "bid-2", "impid": "imp-0", "price": 5.0, "adm": "Ad 2"}]},
            {"bid": [{"id": "bid-3", "impid": "imp-0", "price": 3.0, "adm": "Ad 3"}]},
        ],
        "cur": "EUR",
    }

    ad_response = handler._build_ad_response(minimal_ad_request, bid_response)

    assert ad_response["ad_id"] == "bid-2"
    assert ad_response["extensions"]["bid_price"] == 5.0
    assert ad_response["extensions"]["currency"] == "EUR"


@pytest.mark.asyncio
async def test_build_ad_response_preserves_bid_details(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest
) -> None:
    """Test _build_ad_response preserves all bid details."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    bid_response: BidResponse = {
        "id": "req-999",
        "seatbid": [
            {
                "bid": [
                    {
                        "id": "bid-detail-test",
                        "impid": "imp-0",
                        "price": 4.75,
                        "adm": "<VAST version='4.2'><Ad></Ad></VAST>",
                        "adomain": ["example-advertiser.com", "backup-domain.com"],
                        "cid": "campaign-xyz",
                        "crid": "creative-abc",
                        "adid": "ad-12345",
                        "nurl": "https://win.example.com/notify",
                        "w": 300,
                        "h": 250,
                    }
                ]
            }
        ],
        "cur": "GBP",
        "bidid": "global-bid-id",
    }

    ad_response = handler._build_ad_response(minimal_ad_request, bid_response)

    # Verify all details preserved
    assert ad_response["ad_id"] == "ad-12345"
    assert ad_response["creative_type"] == "video/vast"
    assert ad_response["raw_response"] == "<VAST version='4.2'><Ad></Ad></VAST>"
    assert ad_response["advertiser"] == "example-advertiser.com"
    assert ad_response["campaign_id"] == "campaign-xyz"
    assert ad_response["dimensions"] == (300, 250)

    ext = ad_response["extensions"]
    assert ext["bid_price"] == 4.75
    assert ext["currency"] == "GBP"
    assert ext["creative_id"] == "creative-abc"
    assert ext["nurl"] == "https://win.example.com/notify"
    assert ext["adm"] == "<VAST version='4.2'><Ad></Ad></VAST>"
    assert ext["bid_id"] == "global-bid-id"


@pytest.mark.asyncio
async def test_build_ad_response_no_seatbid(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest
) -> None:
    """Test _build_ad_response with missing seatbid key."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    bid_response: BidResponse = {
        "id": "req-no-seatbid",
        "cur": "USD",
    }

    with pytest.raises(OpenRTBNoBidError) as exc_info:
        handler._build_ad_response(minimal_ad_request, bid_response)

    assert "no seatbid" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_build_ad_response_empty_bids(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest
) -> None:
    """Test _build_ad_response with seatbid but no bids."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    bid_response: BidResponse = {
        "id": "req-empty-bids",
        "seatbid": [{"bid": []}],
        "cur": "USD",
    }

    with pytest.raises(OpenRTBNoBidError) as exc_info:
        handler._build_ad_response(minimal_ad_request, bid_response)

    assert "no bids" in str(exc_info.value).lower()


# ============================================================================
# Handler End-to-End Tests (fetch method)
# ============================================================================


@pytest.mark.asyncio
async def test_fetch_success(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest, sample_bid_response: BidResponse
) -> None:
    """Test fetch method with successful bid response."""
    mock_upstream.send_bid_request = AsyncMock(return_value=sample_bid_response)
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    response = await handler.fetch(minimal_ad_request)

    # Verify success
    assert response["success"] is True
    assert response["slot_id"] == "test-slot-123"
    assert response["ad_id"] == "bid-1"
    assert response["extensions"]["bid_price"] == 2.5

    # Verify upstream was called correctly
    mock_upstream.send_bid_request.assert_called_once()
    call_args = mock_upstream.send_bid_request.call_args
    bid_request = call_args[0][0]
    assert bid_request["imp"][0]["tagid"] == "test-slot-123"


@pytest.mark.asyncio
async def test_fetch_with_context(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest, sample_bid_response: BidResponse
) -> None:
    """Test fetch method passes context correctly."""
    mock_upstream.send_bid_request = AsyncMock(return_value=sample_bid_response)
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    # Context shouldn't affect OpenRTB handling but should not error
    response = await handler.fetch(
        minimal_ad_request, session_id="test-session", custom_field="value"
    )

    assert response["success"] is True
    mock_upstream.send_bid_request.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_no_bid_response(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest
) -> None:
    """Test fetch method handles no bid response."""
    no_bid_response: BidResponse = {
        "id": "req-no-bid",
        "seatbid": [],
        "cur": "USD",
    }
    mock_upstream.send_bid_request = AsyncMock(return_value=no_bid_response)
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    response = await handler.fetch(minimal_ad_request)

    # Verify unsuccessful response with NO_BID error code
    assert response["success"] is False
    assert response["slot_id"] == "test-slot-123"
    assert response["error_code"] == "NO_BID"
    assert "no seatbid" in response["error"].lower()


@pytest.mark.asyncio
async def test_fetch_invalid_json(mock_upstream: AsyncMock, minimal_ad_request: AdRequest) -> None:
    """Test fetch method handles JSON parsing errors."""
    from xsp.core.exceptions import OpenRTBParseError

    mock_upstream.send_bid_request = AsyncMock(side_effect=OpenRTBParseError("Invalid JSON"))
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    response = await handler.fetch(minimal_ad_request)

    # Verify error response
    assert response["success"] is False
    assert response["slot_id"] == "test-slot-123"
    assert response["error_code"] == "OPENRTB_ERROR"
    assert "invalid json" in response["error"].lower()


@pytest.mark.asyncio
async def test_fetch_upstream_exception(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest
) -> None:
    """Test fetch method handles generic upstream exceptions."""
    mock_upstream.send_bid_request = AsyncMock(side_effect=Exception("Network error"))
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    response = await handler.fetch(minimal_ad_request)

    assert response["success"] is False
    assert response["error_code"] == "OPENRTB_ERROR"
    assert "network error" in response["error"].lower()


# ============================================================================
# Lifecycle Tests
# ============================================================================


@pytest.mark.asyncio
async def test_close(mock_upstream: AsyncMock) -> None:
    """Test close method calls upstream.close()."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    await handler.close()

    mock_upstream.close.assert_called_once()


@pytest.mark.asyncio
async def test_health_check(mock_upstream: AsyncMock) -> None:
    """Test health_check returns upstream health status."""
    mock_upstream.health_check = AsyncMock(return_value=True)
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    result = await handler.health_check()

    assert result is True
    mock_upstream.health_check.assert_called_once()


@pytest.mark.asyncio
async def test_health_check_unhealthy(mock_upstream: AsyncMock) -> None:
    """Test health_check returns False when upstream unhealthy."""
    mock_upstream.health_check = AsyncMock(return_value=False)
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    result = await handler.health_check()

    assert result is False


@pytest.mark.asyncio
async def test_validate_request_valid(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest
) -> None:
    """Test validate_request with valid request."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    result = handler.validate_request(minimal_ad_request)

    assert result is True


@pytest.mark.asyncio
async def test_validate_request_missing_slot_id(mock_upstream: AsyncMock) -> None:
    """Test validate_request with missing slot_id."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    invalid_request: AdRequest = {"user_id": "user-123"}

    result = handler.validate_request(invalid_request)

    assert result is False


@pytest.mark.asyncio
async def test_validate_request_missing_user_id(mock_upstream: AsyncMock) -> None:
    """Test validate_request with missing user_id."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    invalid_request: AdRequest = {"slot_id": "slot-123"}

    result = handler.validate_request(invalid_request)

    assert result is False


# ============================================================================
# Track Method Tests
# ============================================================================


@pytest.mark.asyncio
async def test_track_impression(mock_upstream: AsyncMock) -> None:
    """Test track method for impression event."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    ad_response: AdResponse = {
        "success": True,
        "slot_id": "test-slot",
        "extensions": {"nurl": "https://win.example.com/notify"},
    }

    # Should not raise error (implementation is placeholder)
    await handler.track("impression", ad_response)


@pytest.mark.asyncio
async def test_track_other_event(mock_upstream: AsyncMock) -> None:
    """Test track method for non-impression event."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    ad_response: AdResponse = {
        "success": True,
        "slot_id": "test-slot",
    }

    # Should not raise error
    await handler.track("click", ad_response)


# ============================================================================
# Creative Type Detection Tests
# ============================================================================


@pytest.mark.asyncio
async def test_creative_type_detection_vast(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest
) -> None:
    """Test creative type detection for VAST XML."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    bid_response: BidResponse = {
        "id": "req-vast",
        "seatbid": [
            {
                "bid": [
                    {
                        "id": "bid-1",
                        "impid": "imp-0",
                        "price": 2.0,
                        "adm": "<VAST version='4.2'><Ad></Ad></VAST>",
                    }
                ]
            }
        ],
        "cur": "USD",
    }

    ad_response = handler._build_ad_response(minimal_ad_request, bid_response)

    assert ad_response["creative_type"] == "video/vast"


@pytest.mark.asyncio
async def test_creative_type_detection_html(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest
) -> None:
    """Test creative type detection for HTML."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    bid_response: BidResponse = {
        "id": "req-html",
        "seatbid": [
            {
                "bid": [
                    {
                        "id": "bid-1",
                        "impid": "imp-0",
                        "price": 2.0,
                        "adm": "<!DOCTYPE html><html><body>Ad</body></html>",
                    }
                ]
            }
        ],
        "cur": "USD",
    }

    ad_response = handler._build_ad_response(minimal_ad_request, bid_response)

    assert ad_response["creative_type"] == "display/html"


@pytest.mark.asyncio
async def test_creative_type_detection_banner(
    mock_upstream: AsyncMock, minimal_ad_request: AdRequest
) -> None:
    """Test creative type detection for generic banner."""
    handler = OpenRTBProtocolHandler(upstream=mock_upstream)

    bid_response: BidResponse = {
        "id": "req-banner",
        "seatbid": [
            {
                "bid": [
                    {
                        "id": "bid-1",
                        "impid": "imp-0",
                        "price": 2.0,
                        "adm": "<div>Simple banner ad</div>",
                    }
                ]
            }
        ],
        "cur": "USD",
    }

    ad_response = handler._build_ad_response(minimal_ad_request, bid_response)

    assert ad_response["creative_type"] == "display/banner"
