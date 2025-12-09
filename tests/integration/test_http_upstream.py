"""Integration tests for HTTP upstream.

These tests require network access and will be skipped if network is unavailable.
Run with: pytest -m network
Skip with: pytest -m "not network"
"""

import pytest

pytest.importorskip("httpx")

from xsp.core.base import BaseUpstream
from xsp.transports.http import HttpTransport

# Mark all tests in this module as requiring network
pytestmark = pytest.mark.network


@pytest.mark.asyncio
async def test_http_upstream_get():
    """Test HTTP upstream with GET request."""
    transport = HttpTransport(method="GET")
    upstream = BaseUpstream(
        transport=transport,
        decoder=lambda b: b.decode("utf-8"),
        endpoint="https://httpbin.org/get",
    )

    result = await upstream.fetch(params={"test": "value"})
    # Verify response contains expected content
    assert "test" in result or "httpbin" in result

    await upstream.close()


@pytest.mark.asyncio
async def test_http_upstream_with_headers():
    """Test HTTP upstream with custom headers."""
    transport = HttpTransport(method="GET")
    upstream = BaseUpstream(
        transport=transport,
        decoder=lambda b: b.decode("utf-8"),
        endpoint="https://httpbin.org/headers",
        default_headers={"X-Custom-Header": "test-value"},
    )

    result = await upstream.fetch()
    assert "X-Custom-Header" in result

    await upstream.close()
