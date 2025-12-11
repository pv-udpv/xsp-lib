"""Tests for OpenRTB upstream implementation.

Tests cover bid request sending, response parsing, error handling, and
protocol-specific behavior for OpenRTB 2.6.

References:
    - OpenRTB 2.6 Specification: https://www.iab.com/wp-content/uploads/2016/03/OpenRTB-API-Specification-Version-2-6-FINAL.pdf
"""

import json
from unittest.mock import AsyncMock

import pytest

from xsp.core.exceptions import (
    OpenRTBNetworkError,
    OpenRTBParseError,
    OpenRTBTimeoutError,
    TransportConnectionError,
    TransportError,
)
from xsp.protocols.openrtb import OpenRTBUpstream
from xsp.protocols.openrtb.types import BidRequest, BidResponse


@pytest.fixture
def mock_transport() -> AsyncMock:
    """Create mock transport for testing."""
    transport = AsyncMock()
    transport.close = AsyncMock()
    return transport


@pytest.fixture
def sample_bid_request() -> BidRequest:
    """Sample OpenRTB bid request."""
    return {
        "id": "req-123",
        "imp": [
            {
                "id": "imp-1",
                "banner": {"w": 728, "h": 90},
                "tagid": "banner-top",
                "bidfloor": 0.50,
            }
        ],
        "site": {"page": "https://example.com", "domain": "example.com"},
        "device": {"ip": "203.0.113.1", "ua": "Mozilla/5.0", "devicetype": 2},
        "user": {"id": "user-456"},
    }


@pytest.fixture
def sample_bid_response_json() -> str:
    """Sample OpenRTB bid response as JSON string."""
    bid_response: BidResponse = {
        "id": "req-123",
        "seatbid": [
            {
                "bid": [
                    {
                        "id": "bid-1",
                        "impid": "imp-1",
                        "price": 2.5,
                        "adm": "<html><body>Ad Content</body></html>",
                        "adomain": ["advertiser.com"],
                        "cid": "campaign-123",
                        "crid": "creative-456",
                    }
                ]
            }
        ],
        "cur": "USD",
        "bidid": "bid-response-789",
    }
    return json.dumps(bid_response)


@pytest.fixture
def sample_bid_response() -> BidResponse:
    """Sample OpenRTB bid response as dict."""
    return {
        "id": "req-123",
        "seatbid": [
            {
                "bid": [
                    {
                        "id": "bid-1",
                        "impid": "imp-1",
                        "price": 2.5,
                        "adm": "<html><body>Ad Content</body></html>",
                        "adomain": ["advertiser.com"],
                    }
                ]
            }
        ],
        "cur": "USD",
    }


# ============================================================================
# Basic Request Tests
# ============================================================================


@pytest.mark.asyncio
async def test_request_success(
    mock_transport: AsyncMock, sample_bid_request: BidRequest, sample_bid_response_json: str
) -> None:
    """Test successful bid request and response."""
    mock_transport.request = AsyncMock(return_value=sample_bid_response_json.encode("utf-8"))

    upstream = OpenRTBUpstream(
        transport=mock_transport, endpoint="https://bidder.example.com/bid"
    )

    response = await upstream.request(payload=sample_bid_request)

    # Verify response is JSON string
    assert isinstance(response, str)
    assert "seatbid" in response

    # Verify can parse response
    parsed = json.loads(response)
    assert parsed["id"] == "req-123"
    assert len(parsed["seatbid"]) > 0

    # Verify transport was called correctly
    mock_transport.request.assert_called_once()
    await upstream.close()


@pytest.mark.asyncio
async def test_request_with_params(
    mock_transport: AsyncMock, sample_bid_request: BidRequest, sample_bid_response_json: str
) -> None:
    """Test bid request with query parameters."""
    mock_transport.request = AsyncMock(return_value=sample_bid_response_json.encode("utf-8"))

    upstream = OpenRTBUpstream(
        transport=mock_transport, endpoint="https://bidder.example.com/bid"
    )

    response = await upstream.request(
        payload=sample_bid_request, params={"debug": "true", "format": "json"}
    )

    assert isinstance(response, str)
    mock_transport.request.assert_called_once()

    # Verify params were passed in metadata
    call_args = mock_transport.request.call_args
    metadata = call_args.kwargs["metadata"]
    import json
    params = json.loads(metadata["_params"])
    assert params == {"debug": "true", "format": "json"}

    await upstream.close()


@pytest.mark.asyncio
async def test_request_timeout(mock_transport: AsyncMock, sample_bid_request: BidRequest) -> None:
    """Test bid request timeout handling."""
    import asyncio

    async def timeout_coroutine(*args, **kwargs):
        await asyncio.sleep(2.0)  # Sleep longer than timeout
        return b"{}"

    mock_transport.request = AsyncMock(side_effect=timeout_coroutine)

    upstream = OpenRTBUpstream(
        transport=mock_transport, endpoint="https://bidder.example.com/bid"
    )

    with pytest.raises(OpenRTBTimeoutError) as exc_info:
        await upstream.request(payload=sample_bid_request, timeout=0.1)

    assert "timed out" in str(exc_info.value).lower()
    await upstream.close()


@pytest.mark.asyncio
async def test_request_network_error(
    mock_transport: AsyncMock, sample_bid_request: BidRequest
) -> None:
    """Test bid request network error handling."""
    mock_transport.request = AsyncMock(
        side_effect=TransportConnectionError("Connection refused")
    )

    upstream = OpenRTBUpstream(
        transport=mock_transport, endpoint="https://bidder.example.com/bid"
    )

    with pytest.raises(OpenRTBNetworkError) as exc_info:
        await upstream.request(payload=sample_bid_request)

    assert "connection" in str(exc_info.value).lower()
    await upstream.close()


@pytest.mark.asyncio
async def test_request_http_error(
    mock_transport: AsyncMock, sample_bid_request: BidRequest
) -> None:
    """Test bid request HTTP error handling."""
    # BaseUpstream wraps errors, so we need to test the actual error that gets through
    mock_transport.request = AsyncMock(side_effect=Exception("HTTP 500 Internal Server Error"))

    upstream = OpenRTBUpstream(
        transport=mock_transport, endpoint="https://bidder.example.com/bid"
    )

    with pytest.raises(OpenRTBNetworkError) as exc_info:
        await upstream.request(payload=sample_bid_request)

    assert "500" in str(exc_info.value)
    await upstream.close()


@pytest.mark.asyncio
async def test_request_invalid_json(
    mock_transport: AsyncMock, sample_bid_request: BidRequest
) -> None:
    """Test bid request with invalid JSON response."""
    mock_transport.request = AsyncMock(return_value=b"<html>Not JSON</html>")

    upstream = OpenRTBUpstream(
        transport=mock_transport, endpoint="https://bidder.example.com/bid"
    )

    with pytest.raises(OpenRTBParseError) as exc_info:
        await upstream.request(payload=sample_bid_request)

    assert "json" in str(exc_info.value).lower()
    await upstream.close()


@pytest.mark.asyncio
async def test_request_missing_id(
    mock_transport: AsyncMock, sample_bid_request: BidRequest
) -> None:
    """Test bid request with response missing required 'id' field."""
    invalid_response = json.dumps({"seatbid": []})
    mock_transport.request = AsyncMock(return_value=invalid_response.encode("utf-8"))

    upstream = OpenRTBUpstream(
        transport=mock_transport, endpoint="https://bidder.example.com/bid"
    )

    with pytest.raises(OpenRTBParseError) as exc_info:
        await upstream.request(payload=sample_bid_request)

    assert "missing required field" in str(exc_info.value).lower()
    assert "'id'" in str(exc_info.value)
    await upstream.close()


# ============================================================================
# Header Tests
# ============================================================================


@pytest.mark.asyncio
async def test_request_headers(
    mock_transport: AsyncMock, sample_bid_request: BidRequest, sample_bid_response_json: str
) -> None:
    """Test bid request sets correct OpenRTB headers."""
    mock_transport.request = AsyncMock(return_value=sample_bid_response_json.encode("utf-8"))

    upstream = OpenRTBUpstream(
        transport=mock_transport, endpoint="https://bidder.example.com/bid"
    )

    await upstream.request(payload=sample_bid_request)

    # Verify headers were set in metadata
    call_args = mock_transport.request.call_args
    metadata = call_args.kwargs["metadata"]
    assert metadata["Content-Type"] == "application/json"
    assert metadata["x-openrtb-version"] == "2.6"

    await upstream.close()


@pytest.mark.asyncio
async def test_request_custom_headers(
    mock_transport: AsyncMock, sample_bid_request: BidRequest, sample_bid_response_json: str
) -> None:
    """Test bid request with custom headers."""
    mock_transport.request = AsyncMock(return_value=sample_bid_response_json.encode("utf-8"))

    upstream = OpenRTBUpstream(
        transport=mock_transport, endpoint="https://bidder.example.com/bid"
    )

    custom_headers = {
        "Authorization": "Bearer token123",
        "X-Custom-Header": "value",
    }

    await upstream.request(payload=sample_bid_request, headers=custom_headers)

    # Verify custom headers were merged with defaults in metadata
    call_args = mock_transport.request.call_args
    metadata = call_args.kwargs["metadata"]
    assert metadata["Content-Type"] == "application/json"
    assert metadata["x-openrtb-version"] == "2.6"
    assert metadata["Authorization"] == "Bearer token123"
    assert metadata["X-Custom-Header"] == "value"

    await upstream.close()


# ============================================================================
# Bid Request Defaults Tests
# ============================================================================


@pytest.mark.asyncio
async def test_request_applies_defaults(
    mock_transport: AsyncMock, sample_bid_response_json: str
) -> None:
    """Test request applies default fields to bid request."""
    mock_transport.request = AsyncMock(return_value=sample_bid_response_json.encode("utf-8"))

    upstream = OpenRTBUpstream(
        transport=mock_transport,
        endpoint="https://bidder.example.com/bid",
        test_mode=True,
        auction_type=1,
        timeout_ms=500,
    )

    minimal_request: BidRequest = {
        "id": "req-minimal",
        "imp": [{"id": "imp-1", "banner": {"w": 300, "h": 250}}],
    }

    await upstream.request(payload=minimal_request)

    # Verify defaults were applied by decoding the encoded payload
    call_args = mock_transport.request.call_args
    payload_bytes = call_args.kwargs["payload"]
    import json
    payload = json.loads(payload_bytes.decode("utf-8"))
    assert payload["test"] == 1
    assert payload["at"] == 1
    assert payload["tmax"] == 500

    await upstream.close()


@pytest.mark.asyncio
async def test_request_respects_existing_fields(
    mock_transport: AsyncMock, sample_bid_response_json: str
) -> None:
    """Test request does not override existing fields."""
    mock_transport.request = AsyncMock(return_value=sample_bid_response_json.encode("utf-8"))

    upstream = OpenRTBUpstream(
        transport=mock_transport,
        endpoint="https://bidder.example.com/bid",
        test_mode=True,
        auction_type=1,
    )

    request_with_fields: BidRequest = {
        "id": "req-with-fields",
        "imp": [{"id": "imp-1", "banner": {"w": 300, "h": 250}}],
        "test": 0,
        "at": 2,
    }

    await upstream.request(payload=request_with_fields)

    # Verify existing fields were not overridden by decoding the payload
    call_args = mock_transport.request.call_args
    payload_bytes = call_args.kwargs["payload"]
    import json
    payload = json.loads(payload_bytes.decode("utf-8"))
    assert payload["test"] == 0  # Not overridden
    assert payload["at"] == 2  # Not overridden

    await upstream.close()


# ============================================================================
# send_bid_request Tests
# ============================================================================


@pytest.mark.asyncio
async def test_send_bid_request(
    mock_transport: AsyncMock, sample_bid_request: BidRequest, sample_bid_response_json: str
) -> None:
    """Test send_bid_request convenience method."""
    mock_transport.request = AsyncMock(return_value=sample_bid_response_json.encode("utf-8"))

    upstream = OpenRTBUpstream(
        transport=mock_transport, endpoint="https://bidder.example.com/bid"
    )

    response = await upstream.send_bid_request(sample_bid_request)

    # Verify response is parsed dict
    assert isinstance(response, dict)
    assert response["id"] == "req-123"
    assert "seatbid" in response
    assert len(response["seatbid"]) > 0

    # Verify bid details
    bid = response["seatbid"][0]["bid"][0]
    assert bid["price"] == 2.5
    assert bid["adm"] == "<html><body>Ad Content</body></html>"

    await upstream.close()


@pytest.mark.asyncio
async def test_send_bid_request_with_timeout(
    mock_transport: AsyncMock, sample_bid_request: BidRequest, sample_bid_response_json: str
) -> None:
    """Test send_bid_request with timeout parameter."""
    mock_transport.request = AsyncMock(return_value=sample_bid_response_json.encode("utf-8"))

    upstream = OpenRTBUpstream(
        transport=mock_transport, endpoint="https://bidder.example.com/bid"
    )

    response = await upstream.send_bid_request(sample_bid_request, timeout=2.0)

    assert isinstance(response, dict)

    # Verify timeout was passed to transport
    call_args = mock_transport.request.call_args
    assert call_args.kwargs["timeout"] == 2.0

    await upstream.close()


@pytest.mark.asyncio
async def test_send_bid_request_error(
    mock_transport: AsyncMock, sample_bid_request: BidRequest
) -> None:
    """Test send_bid_request error handling."""
    import asyncio

    async def timeout_coroutine(*args, **kwargs):
        await asyncio.sleep(2.0)
        return b"{}"

    mock_transport.request = AsyncMock(side_effect=timeout_coroutine)

    upstream = OpenRTBUpstream(
        transport=mock_transport, endpoint="https://bidder.example.com/bid"
    )

    with pytest.raises(OpenRTBTimeoutError):
        await upstream.send_bid_request(sample_bid_request, timeout=0.1)

    await upstream.close()


# ============================================================================
# Configuration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_upstream_configuration(mock_transport: AsyncMock) -> None:
    """Test upstream initialization with various configurations."""
    upstream = OpenRTBUpstream(
        transport=mock_transport,
        endpoint="https://bidder.example.com/bid",
        currency="EUR",
        test_mode=True,
        auction_type=1,
        timeout_ms=1000,
    )

    assert upstream.currency == "EUR"
    assert upstream.test_mode is True
    assert upstream.auction_type == 1
    assert upstream.timeout_ms == 1000

    await upstream.close()


@pytest.mark.asyncio
async def test_upstream_default_configuration(mock_transport: AsyncMock) -> None:
    """Test upstream initialization with default configurations."""
    upstream = OpenRTBUpstream(
        transport=mock_transport, endpoint="https://bidder.example.com/bid"
    )

    assert upstream.currency == "USD"
    assert upstream.test_mode is False
    assert upstream.auction_type == 2
    assert upstream.timeout_ms is None

    await upstream.close()


# ============================================================================
# Lifecycle Tests
# ============================================================================


@pytest.mark.asyncio
async def test_close(mock_transport: AsyncMock) -> None:
    """Test close method calls transport.close()."""
    upstream = OpenRTBUpstream(
        transport=mock_transport, endpoint="https://bidder.example.com/bid"
    )

    await upstream.close()

    mock_transport.close.assert_called_once()


# ============================================================================
# Error Mapping Tests
# ============================================================================


@pytest.mark.asyncio
async def test_error_mapping_timeout(
    mock_transport: AsyncMock, sample_bid_request: BidRequest
) -> None:
    """Test timeout maps to OpenRTBTimeoutError."""
    import asyncio

    async def timeout_coroutine(*args, **kwargs):
        await asyncio.sleep(2.0)
        return b"{}"

    mock_transport.request = AsyncMock(side_effect=timeout_coroutine)

    upstream = OpenRTBUpstream(
        transport=mock_transport, endpoint="https://bidder.example.com/bid"
    )

    with pytest.raises(OpenRTBTimeoutError):
        await upstream.request(payload=sample_bid_request, timeout=0.1)

    await upstream.close()


@pytest.mark.asyncio
async def test_error_mapping_connection(
    mock_transport: AsyncMock, sample_bid_request: BidRequest
) -> None:
    """Test TransportConnectionError maps to OpenRTBNetworkError."""
    mock_transport.request = AsyncMock(side_effect=TransportConnectionError("Connection failed"))

    upstream = OpenRTBUpstream(
        transport=mock_transport, endpoint="https://bidder.example.com/bid"
    )

    with pytest.raises(OpenRTBNetworkError):
        await upstream.request(payload=sample_bid_request)

    await upstream.close()


@pytest.mark.asyncio
async def test_error_mapping_http_with_status(
    mock_transport: AsyncMock, sample_bid_request: BidRequest
) -> None:
    """Test error handling for HTTP errors."""
    mock_transport.request = AsyncMock(
        side_effect=Exception("HTTP 404 Not Found")
    )

    upstream = OpenRTBUpstream(
        transport=mock_transport, endpoint="https://bidder.example.com/bid"
    )

    with pytest.raises(OpenRTBNetworkError) as exc_info:
        await upstream.request(payload=sample_bid_request)

    assert "404" in str(exc_info.value)

    await upstream.close()


@pytest.mark.asyncio
async def test_error_mapping_generic_transport(
    mock_transport: AsyncMock, sample_bid_request: BidRequest
) -> None:
    """Test generic TransportError maps to OpenRTBNetworkError."""
    mock_transport.request = AsyncMock(
        side_effect=TransportError("Generic transport error")
    )

    upstream = OpenRTBUpstream(
        transport=mock_transport, endpoint="https://bidder.example.com/bid"
    )

    with pytest.raises(OpenRTBNetworkError):
        await upstream.request(payload=sample_bid_request)

    await upstream.close()


# ============================================================================
# Payload Validation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_request_requires_payload(mock_transport: AsyncMock) -> None:
    """Test request raises error when payload is None."""
    upstream = OpenRTBUpstream(
        transport=mock_transport, endpoint="https://bidder.example.com/bid"
    )

    with pytest.raises(ValueError) as exc_info:
        await upstream.request()

    assert "payload" in str(exc_info.value).lower()
    assert "required" in str(exc_info.value).lower()

    await upstream.close()


# ============================================================================
# No-Bid Response Tests
# ============================================================================


@pytest.mark.asyncio
async def test_no_bid_response(mock_transport: AsyncMock, sample_bid_request: BidRequest) -> None:
    """Test handling of no-bid response."""
    no_bid_response = json.dumps({"id": "req-123", "seatbid": [], "nbr": 0})
    mock_transport.request = AsyncMock(return_value=no_bid_response.encode("utf-8"))

    upstream = OpenRTBUpstream(
        transport=mock_transport, endpoint="https://bidder.example.com/bid"
    )

    response = await upstream.send_bid_request(sample_bid_request)

    # Verify response structure is valid
    assert response["id"] == "req-123"
    assert response["seatbid"] == []
    assert response["nbr"] == 0

    await upstream.close()


@pytest.mark.asyncio
async def test_empty_response(mock_transport: AsyncMock, sample_bid_request: BidRequest) -> None:
    """Test handling of minimal valid response."""
    minimal_response = json.dumps({"id": "req-123"})
    mock_transport.request = AsyncMock(return_value=minimal_response.encode("utf-8"))

    upstream = OpenRTBUpstream(
        transport=mock_transport, endpoint="https://bidder.example.com/bid"
    )

    response = await upstream.send_bid_request(sample_bid_request)

    # Should parse successfully
    assert response["id"] == "req-123"
    assert "seatbid" not in response or response.get("seatbid") is None

    await upstream.close()
