"""Integration test for complete xsp-lib workflow."""

import asyncio
import json

import pytest

from xsp.core.base import BaseUpstream
from xsp.middleware.base import MiddlewareStack
from xsp.middleware.retry import RetryMiddleware
from xsp.transports.memory import MemoryTransport


@pytest.mark.asyncio
async def test_complete_workflow():
    """Test complete workflow with upstream, middleware, and transport."""
    # Create transport with sample JSON data
    sample_data = {"ad_id": "123", "impression_url": "https://example.com/imp"}
    transport = MemoryTransport(json.dumps(sample_data).encode("utf-8"))

    # Create base upstream
    upstream = BaseUpstream(
        transport=transport,
        decoder=json.loads,
        endpoint="memory://ads",
        default_headers={"X-API-Key": "test-key"},
        default_timeout=10.0,
    )

    # Wrap with retry middleware
    middleware = MiddlewareStack(RetryMiddleware(max_attempts=3))
    wrapped_upstream = middleware.wrap(upstream)

    # Fetch data
    result = await wrapped_upstream.fetch()

    # Verify
    assert result["ad_id"] == "123"
    assert result["impression_url"] == "https://example.com/imp"

    # Cleanup
    await wrapped_upstream.close()


@pytest.mark.asyncio
async def test_file_transport_workflow(tmp_path):
    """Test workflow with file transport."""
    from xsp.transports.file import FileTransport

    # Create test file
    test_file = tmp_path / "ad_response.json"
    test_data = {"campaign_id": "456", "creative_url": "https://cdn.example.com/ad.jpg"}
    test_file.write_text(json.dumps(test_data))

    # Create upstream with file transport
    transport = FileTransport()
    upstream = BaseUpstream(
        transport=transport,
        decoder=json.loads,
        endpoint=str(test_file),
    )

    # Fetch data
    result = await upstream.fetch()

    # Verify
    assert result["campaign_id"] == "456"
    assert "creative_url" in result

    await upstream.close()
