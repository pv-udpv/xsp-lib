"""Tests for transport implementations."""

import pytest

from xsp.core.transport import TransportType
from xsp.core.exceptions import (
    TransportError,
    TransportTimeoutError,
    TransportConnectionError,
)
from xsp.transports.file import FileTransport
from xsp.transports.memory import MemoryTransport


@pytest.mark.asyncio
async def test_memory_transport():
    """Test memory transport."""
    transport = MemoryTransport(b"test data")

    assert transport.transport_type == TransportType.MEMORY

    result = await transport.send(endpoint="anything")
    assert result == b"test data"

    await transport.close()


@pytest.mark.asyncio
async def test_file_transport(tmp_path):
    """Test file transport."""
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"file contents")

    transport = FileTransport()

    assert transport.transport_type == TransportType.FILE

    result = await transport.send(endpoint=str(test_file))
    assert result == b"file contents"

    await transport.close()


@pytest.mark.asyncio
async def test_file_transport_nonexistent_file():
    """Test file transport with nonexistent file."""
    transport = FileTransport()

    with pytest.raises(FileNotFoundError):
        await transport.send(endpoint="/nonexistent/file.txt")


@pytest.mark.asyncio
async def test_http_transport_timeout_error():
    """Test HTTP transport maps httpx.TimeoutException to TransportTimeoutError."""
    try:
        import httpx
        from xsp.transports.http import HttpTransport
    except ImportError:
        pytest.skip("httpx not installed")

    # Create a mock httpx client that raises TimeoutException
    class MockHttpxClient:
        async def request(self, **kwargs):
            raise httpx.TimeoutException("Request timed out")

        async def aclose(self):
            pass

    transport = HttpTransport(client=MockHttpxClient())

    with pytest.raises(TransportTimeoutError) as exc_info:
        await transport.send(endpoint="https://example.com")

    assert "timeout" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_http_transport_connection_error():
    """Test HTTP transport maps httpx.ConnectError to TransportConnectionError."""
    try:
        import httpx
        from xsp.transports.http import HttpTransport
    except ImportError:
        pytest.skip("httpx not installed")

    # Create a mock httpx client that raises ConnectError
    class MockHttpxClient:
        async def request(self, **kwargs):
            raise httpx.ConnectError("Connection failed")

        async def aclose(self):
            pass

    transport = HttpTransport(client=MockHttpxClient())

    with pytest.raises(TransportConnectionError) as exc_info:
        await transport.send(endpoint="https://example.com")

    assert "connection failed" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_http_transport_network_error():
    """Test HTTP transport maps httpx.NetworkError to TransportConnectionError."""
    try:
        import httpx
        from xsp.transports.http import HttpTransport
    except ImportError:
        pytest.skip("httpx not installed")

    # Create a mock httpx client that raises NetworkError
    class MockHttpxClient:
        async def request(self, **kwargs):
            raise httpx.NetworkError("Network error")

        async def aclose(self):
            pass

    transport = HttpTransport(client=MockHttpxClient())

    with pytest.raises(TransportConnectionError) as exc_info:
        await transport.send(endpoint="https://example.com")

    assert "connection failed" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_http_transport_http_status_error():
    """Test HTTP transport maps httpx.HTTPStatusError to TransportError with status code."""
    try:
        import httpx
        from xsp.transports.http import HttpTransport
    except ImportError:
        pytest.skip("httpx not installed")

    # Create a mock httpx client that raises HTTPStatusError
    class MockResponse:
        status_code = 404

    class MockHttpxClient:
        async def request(self, **kwargs):
            response = MockResponse()
            raise httpx.HTTPStatusError(
                "404 Not Found",
                request=None,
                response=response,
            )

        async def aclose(self):
            pass

    transport = HttpTransport(client=MockHttpxClient())

    with pytest.raises(TransportError) as exc_info:
        await transport.send(endpoint="https://example.com")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_http_transport_generic_exception():
    """Test HTTP transport maps generic exceptions to TransportError."""
    try:
        import httpx
        from xsp.transports.http import HttpTransport
    except ImportError:
        pytest.skip("httpx not installed")

    # Create a mock httpx client that raises a generic exception
    class MockHttpxClient:
        async def request(self, **kwargs):
            raise RuntimeError("Unexpected error")

        async def aclose(self):
            pass

    transport = HttpTransport(client=MockHttpxClient())

    with pytest.raises(TransportError) as exc_info:
        await transport.send(endpoint="https://example.com")

    assert "transport error" in str(exc_info.value).lower()
