"""Tests for upstream abstractions."""

import pytest

from xsp.core.base import BaseUpstream
from xsp.core.exceptions import DecodeError
from xsp.transports.memory import MemoryTransport


@pytest.mark.asyncio
async def test_basic_upstream_fetch():
    """Test basic upstream fetch with memory transport."""
    transport = MemoryTransport(b"test response")
    upstream = BaseUpstream(
        transport=transport, decoder=lambda b: b.decode("utf-8"), endpoint="test"
    )

    result = await upstream.fetch()
    assert result == "test response"


@pytest.mark.asyncio
async def test_upstream_with_decoder():
    """Test upstream with custom decoder."""
    import json

    transport = MemoryTransport(b'{"key": "value"}')
    upstream = BaseUpstream(transport=transport, decoder=json.loads, endpoint="test")

    result = await upstream.fetch()
    assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_upstream_close():
    """Test upstream close."""
    transport = MemoryTransport(b"test")
    upstream = BaseUpstream(
        transport=transport, decoder=lambda b: b.decode("utf-8"), endpoint="test"
    )

    await upstream.close()
    # Should not raise


@pytest.mark.asyncio
async def test_upstream_decode_error():
    """Test upstream decode error handling."""
    transport = MemoryTransport(b"invalid json")

    def bad_decoder(b: bytes) -> dict:
        import json

        return json.loads(b)

    upstream = BaseUpstream(transport=transport, decoder=bad_decoder, endpoint="test")

    with pytest.raises(DecodeError):
        await upstream.fetch()


@pytest.mark.asyncio
async def test_upstream_with_default_params():
    """Test upstream with default parameters."""
    transport = MemoryTransport(b"test")
    upstream = BaseUpstream(
        transport=transport,
        decoder=lambda b: b.decode("utf-8"),
        endpoint="test",
        default_params={"key": "value"},
    )

    result = await upstream.fetch()
    assert result == "test"


@pytest.mark.asyncio
async def test_upstream_with_default_headers():
    """Test upstream with default headers."""
    transport = MemoryTransport(b"test")
    upstream = BaseUpstream(
        transport=transport,
        decoder=lambda b: b.decode("utf-8"),
        endpoint="test",
        default_headers={"Authorization": "Bearer token"},
    )

    result = await upstream.fetch()
    assert result == "test"
