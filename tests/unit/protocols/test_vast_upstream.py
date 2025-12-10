"""Tests for VAST upstream implementations."""

import pytest

from xsp.protocols.vast import VastUpstream, VastVersion
from xsp.transports.memory import MemoryTransport
from xsp.core.exceptions import (
    TransportError,
    TransportTimeoutError,
    TransportConnectionError,
    VastTimeoutError,
    VastNetworkError,
    VastHttpError,
)


class MockErrorTransport:
    """Mock transport that raises specific errors."""

    def __init__(self, error: Exception):
        """Initialize with error to raise."""
        self.error = error
        self.transport_type = "mock"

    async def send(self, *args, **kwargs):
        """Raise the configured error."""
        raise self.error

    async def close(self):
        """Mock close."""
        pass


@pytest.fixture
def sample_vast_xml() -> str:
    """Sample VAST 4.2 XML."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="12345">
        <InLine>
            <AdSystem>TestSystem</AdSystem>
            <AdTitle>Test Ad</AdTitle>
            <Impression><![CDATA[https://impression.example.com/imp?id=123]]></Impression>
            <Creatives>
                <Creative>
                    <Linear>
                        <MediaFiles>
                            <MediaFile delivery="progressive" type="video/mp4"
                                       width="1920" height="1080">
                                <![CDATA[https://cdn.example.com/video.mp4]]>
                            </MediaFile>
                        </MediaFiles>
                    </Linear>
                </Creative>
            </Creatives>
        </InLine>
    </Ad>
</VAST>"""


@pytest.mark.asyncio
async def test_vast_upstream_fetch(sample_vast_xml: str) -> None:
    """Test basic VAST fetch."""
    transport = MemoryTransport(sample_vast_xml.encode("utf-8"))
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
        version=VastVersion.V4_2,
    )

    xml = await upstream.fetch()
    assert '<VAST version="' in xml
    assert "Test Ad" in xml
    await upstream.close()


@pytest.mark.asyncio
async def test_vast_upstream_with_params(sample_vast_xml: str) -> None:
    """Test VAST fetch with query parameters."""
    transport = MemoryTransport(sample_vast_xml.encode("utf-8"))
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
    )

    xml = await upstream.fetch(params={"user_id": "123", "format": "video"})
    assert "<VAST" in xml
    await upstream.close()


@pytest.mark.asyncio
async def test_vast_upstream_cyrillic_params(sample_vast_xml: str) -> None:
    """Test VAST with Cyrillic in URL param."""
    transport = MemoryTransport(sample_vast_xml.encode("utf-8"))
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
    )

    xml = await upstream.fetch(
        params={
            "url": "https://example.ru/видео",
            "_encoding_config": {"url": False},  # Don't encode 'url' param
        }
    )
    assert "<VAST" in xml
    await upstream.close()


@pytest.mark.asyncio
async def test_vast_upstream_with_validation(sample_vast_xml: str) -> None:
    """Test VAST fetch with XML validation."""
    transport = MemoryTransport(sample_vast_xml.encode("utf-8"))
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
        validate_xml=True,
    )

    xml = await upstream.fetch()
    assert "<VAST" in xml
    await upstream.close()


@pytest.mark.asyncio
async def test_vast_upstream_fetch_vast_method(sample_vast_xml: str) -> None:
    """Test VAST fetch using fetch_vast convenience method."""
    transport = MemoryTransport(sample_vast_xml.encode("utf-8"))
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
    )

    xml = await upstream.fetch_vast(
        user_id="user123", ip_address="192.168.1.1", url="https://example.com/video"
    )
    assert "<VAST" in xml
    await upstream.close()


@pytest.mark.asyncio
async def test_vast_upstream_ssai_mode() -> None:
    """Test VAST upstream with SSAI mode enabled filters request URL macros."""
    # Create a transport that captures the request endpoint
    class CapturingTransport:
        def __init__(self):
            self.last_endpoint = None
            self.transport_type = "capturing"

        async def send(self, endpoint, **kwargs):
            self.last_endpoint = endpoint
            return b'<?xml version="1.0"><VAST version="4.2"><Ad/></VAST>'

        async def close(self):
            pass

    transport = CapturingTransport()
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast?ts=[TIMESTAMP]&asset=[ASSETURI]",
        version=VastVersion.V4_2,
        ssai_mode=True,
    )

    await upstream.fetch(context={"asseturi": "video.mp4"})

    # TIMESTAMP should be substituted (SSAI-recommended)
    assert "[TIMESTAMP]" not in transport.last_endpoint
    # ASSETURI should NOT be substituted (not SSAI-recommended)
    assert "[ASSETURI]" in transport.last_endpoint
    await upstream.close()


@pytest.mark.asyncio
async def test_vast_upstream_error_mapping_timeout() -> None:
    """Test TransportTimeoutError is mapped to VastTimeoutError."""
    transport = MockErrorTransport(TransportTimeoutError("Timeout"))
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
    )

    with pytest.raises(VastTimeoutError):
        await upstream.fetch()


@pytest.mark.asyncio
async def test_vast_upstream_error_mapping_connection() -> None:
    """Test TransportConnectionError is mapped to VastNetworkError."""
    transport = MockErrorTransport(TransportConnectionError("Connection failed"))
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
    )

    with pytest.raises(VastNetworkError):
        await upstream.fetch()


@pytest.mark.asyncio
async def test_vast_upstream_error_mapping_http_error() -> None:
    """Test TransportError with status code is mapped to VastHttpError."""
    transport = MockErrorTransport(
        TransportError("HTTP 404", status_code=404)
    )
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
    )

    with pytest.raises(VastHttpError) as exc_info:
        await upstream.fetch()

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_vast_upstream_error_mapping_generic_transport() -> None:
    """Test TransportError without status code is mapped to VastNetworkError."""
    transport = MockErrorTransport(TransportError("Generic error"))
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
    )

    with pytest.raises(VastNetworkError):
        await upstream.fetch()
