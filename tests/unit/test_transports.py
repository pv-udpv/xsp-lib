"""Tests for transport implementations."""

import pytest

from xsp.core.transport import TransportType
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
