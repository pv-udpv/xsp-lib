"""Tests for VAST protocol handler."""

import pytest

from xsp.core.protocol import AdRequest
from xsp.protocols.vast import ChainResolver, VastProtocolHandler, VastUpstream
from xsp.transports.memory import MemoryTransport


@pytest.fixture
def sample_vast_xml() -> str:
    """Sample VAST XML."""
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
async def test_vast_handler_protocol_name(sample_vast_xml: str) -> None:
    """Test protocol name property."""
    transport = MemoryTransport(sample_vast_xml.encode("utf-8"))
    upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")
    resolver = ChainResolver(upstream=upstream)
    handler = VastProtocolHandler(chain_resolver=resolver)

    assert handler.protocol_name == "vast"

    await handler.close()


@pytest.mark.asyncio
async def test_vast_handler_basic_request(sample_vast_xml: str) -> None:
    """Test handling basic ad request."""
    transport = MemoryTransport(sample_vast_xml.encode("utf-8"))
    upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")
    resolver = ChainResolver(upstream=upstream)
    handler = VastProtocolHandler(chain_resolver=resolver)

    request = AdRequest(
        user_id="user123",
        ip_address="192.168.1.1",
        url="https://example.com/video",
        placement_id="placement1",
    )

    response = await handler.handle(request)

    assert response.protocol == "vast"
    assert response.status == "success"
    assert "<VAST" in response.data
    assert "Test Ad" in response.data
    assert response.metadata["user_id"] == "user123"
    assert response.metadata["ip_address"] == "192.168.1.1"

    await handler.close()


@pytest.mark.asyncio
async def test_vast_handler_with_params(sample_vast_xml: str) -> None:
    """Test handling request with additional parameters."""
    transport = MemoryTransport(sample_vast_xml.encode("utf-8"))
    upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")
    resolver = ChainResolver(upstream=upstream)
    handler = VastProtocolHandler(chain_resolver=resolver)

    request = AdRequest(
        user_id="user123",
        params={"format": "video", "duration": "30"},
    )

    response = await handler.handle(request)

    assert response.status == "success"
    assert "<VAST" in response.data
    assert "format" in response.metadata["params"]
    assert "duration" in response.metadata["params"]

    await handler.close()


@pytest.mark.asyncio
async def test_vast_handler_error_handling() -> None:
    """Test error handling in handler."""
    # Create transport that will fail
    transport = MemoryTransport(b"")
    upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")
    resolver = ChainResolver(upstream=upstream, max_depth=1)
    handler = VastProtocolHandler(chain_resolver=resolver)

    # Create wrapper that will exceed depth
    wrapper_vast = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="wrapper1">
        <Wrapper>
            <AdSystem>WrapperSystem</AdSystem>
            <VASTAdTagURI><![CDATA[https://ads.example.com/inline]]></VASTAdTagURI>
        </Wrapper>
    </Ad>
</VAST>"""

    transport = MemoryTransport(wrapper_vast.encode("utf-8"))
    upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")
    resolver = ChainResolver(upstream=upstream, max_depth=1)
    handler = VastProtocolHandler(chain_resolver=resolver)

    request = AdRequest(user_id="user123")
    response = await handler.handle(request)

    assert response.status == "error"
    assert response.error is not None
    assert "error_type" in response.metadata

    await handler.close()


@pytest.mark.asyncio
async def test_vast_handler_minimal_request(sample_vast_xml: str) -> None:
    """Test handling minimal request."""
    transport = MemoryTransport(sample_vast_xml.encode("utf-8"))
    upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")
    resolver = ChainResolver(upstream=upstream)
    handler = VastProtocolHandler(chain_resolver=resolver)

    request = AdRequest()  # No parameters

    response = await handler.handle(request)

    assert response.status == "success"
    assert "<VAST" in response.data

    await handler.close()
