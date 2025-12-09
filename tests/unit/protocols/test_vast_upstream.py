"""Tests for VAST upstream implementations."""

import pytest

from xsp.protocols.vast import VastUpstream, VastVersion
from xsp.transports.memory import MemoryTransport


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
