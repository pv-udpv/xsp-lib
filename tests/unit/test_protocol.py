"""Tests for ProtocolHandler abstraction."""

import pytest

from xsp.core.protocol import ProtocolHandler


class SampleRequest:
    """Sample request type."""

    def __init__(self, data: str):
        self.data = data


class SampleResponse:
    """Sample response type."""

    def __init__(self, result: str):
        self.result = result


class SampleProtocolHandler(ProtocolHandler[SampleRequest, SampleResponse]):
    """Concrete protocol handler for testing."""

    async def handle(
        self, request: SampleRequest, **kwargs: object
    ) -> SampleResponse:
        """Handle test request."""
        return SampleResponse(f"processed: {request.data}")


@pytest.mark.asyncio
async def test_protocol_handler_handle():
    """Test protocol handler handle method."""
    handler = SampleProtocolHandler()
    request = SampleRequest("test data")

    response = await handler.handle(request)

    assert response.result == "processed: test data"


@pytest.mark.asyncio
async def test_protocol_handler_close():
    """Test protocol handler close method."""
    handler = SampleProtocolHandler()

    # Should not raise
    await handler.close()


@pytest.mark.asyncio
async def test_protocol_handler_health_check():
    """Test protocol handler health check."""
    handler = SampleProtocolHandler()

    health = await handler.health_check()

    assert health is True


class CustomProtocolHandler(ProtocolHandler[SampleRequest, SampleResponse]):
    """Protocol handler with custom health check."""

    def __init__(self, healthy: bool = True):
        self.healthy = healthy
        self.closed = False

    async def handle(
        self, request: SampleRequest, **kwargs: object
    ) -> SampleResponse:
        """Handle test request."""
        return SampleResponse("custom")

    async def close(self) -> None:
        """Mark as closed."""
        self.closed = True

    async def health_check(self) -> bool:
        """Custom health check."""
        return self.healthy


@pytest.mark.asyncio
async def test_protocol_handler_custom_health_check():
    """Test protocol handler with custom health check."""
    healthy_handler = CustomProtocolHandler(healthy=True)
    assert await healthy_handler.health_check() is True

    unhealthy_handler = CustomProtocolHandler(healthy=False)
    assert await unhealthy_handler.health_check() is False


@pytest.mark.asyncio
async def test_protocol_handler_custom_close():
    """Test protocol handler with custom close."""
    handler = CustomProtocolHandler()
    assert handler.closed is False

    await handler.close()
    assert handler.closed is True
