"""Tests for orchestrator."""

import pytest

from xsp.core.protocol import AdRequest
from xsp.core.state import InMemoryStateBackend
from xsp.orchestrator import Orchestrator
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
async def test_orchestrator_register_handler(sample_vast_xml: str) -> None:
    """Test registering a protocol handler."""
    transport = MemoryTransport(sample_vast_xml.encode("utf-8"))
    upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")
    resolver = ChainResolver(upstream=upstream)
    handler = VastProtocolHandler(chain_resolver=resolver)

    orchestrator = Orchestrator()
    orchestrator.register_handler("vast", handler)

    assert "vast" in orchestrator.handlers
    assert orchestrator.handlers["vast"] is handler

    await orchestrator.close()


@pytest.mark.asyncio
async def test_orchestrator_serve_vast(sample_vast_xml: str) -> None:
    """Test serving VAST ad request."""
    transport = MemoryTransport(sample_vast_xml.encode("utf-8"))
    upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")
    resolver = ChainResolver(upstream=upstream)
    handler = VastProtocolHandler(chain_resolver=resolver)

    orchestrator = Orchestrator(handlers={"vast": handler})

    request = AdRequest(
        protocol="vast",
        user_id="user123",
        ip_address="192.168.1.1",
    )

    response = await orchestrator.serve(request)

    assert response.protocol == "vast"
    assert response.status == "success"
    assert "<VAST" in response.data

    await orchestrator.close()


@pytest.mark.asyncio
async def test_orchestrator_serve_unsupported_protocol() -> None:
    """Test serving request with unsupported protocol."""
    orchestrator = Orchestrator()

    request = AdRequest(protocol="openrtb")

    response = await orchestrator.serve(request)

    assert response.status == "error"
    assert "not supported" in response.error
    assert "supported_protocols" in response.metadata

    await orchestrator.close()


@pytest.mark.asyncio
async def test_orchestrator_auto_detect_protocol(sample_vast_xml: str) -> None:
    """Test auto-detecting protocol."""
    transport = MemoryTransport(sample_vast_xml.encode("utf-8"))
    upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")
    resolver = ChainResolver(upstream=upstream)
    handler = VastProtocolHandler(chain_resolver=resolver)

    orchestrator = Orchestrator(handlers={"vast": handler})

    # Request without explicit protocol
    request = AdRequest(user_id="user123")

    response = await orchestrator.serve(request)

    assert response.protocol == "vast"
    assert response.status == "success"

    await orchestrator.close()


@pytest.mark.asyncio
async def test_orchestrator_with_caching(sample_vast_xml: str) -> None:
    """Test orchestrator with caching enabled."""
    transport = MemoryTransport(sample_vast_xml.encode("utf-8"))
    upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")
    resolver = ChainResolver(upstream=upstream)
    handler = VastProtocolHandler(chain_resolver=resolver)

    cache_backend = InMemoryStateBackend()
    orchestrator = Orchestrator(
        handlers={"vast": handler},
        cache_backend=cache_backend,
        enable_caching=True,
        cache_ttl=60.0,
    )

    request = AdRequest(
        protocol="vast",
        user_id="user123",
        ip_address="192.168.1.1",
    )

    # First request - should fetch
    response1 = await orchestrator.serve(request)
    assert response1.status == "success"

    # Second request - should hit cache
    response2 = await orchestrator.serve(request)
    assert response2.status == "success"
    assert response2.data == response1.data

    await orchestrator.close()


@pytest.mark.asyncio
async def test_orchestrator_caching_disabled(sample_vast_xml: str) -> None:
    """Test orchestrator with caching disabled."""
    transport = MemoryTransport(sample_vast_xml.encode("utf-8"))
    upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")
    resolver = ChainResolver(upstream=upstream)
    handler = VastProtocolHandler(chain_resolver=resolver)

    cache_backend = InMemoryStateBackend()
    orchestrator = Orchestrator(
        handlers={"vast": handler},
        cache_backend=cache_backend,
        enable_caching=False,  # Disabled
    )

    request = AdRequest(protocol="vast", user_id="user123")

    # Both requests should fetch (not cached)
    response1 = await orchestrator.serve(request)
    response2 = await orchestrator.serve(request)

    assert response1.status == "success"
    assert response2.status == "success"

    # Cache should be empty
    cache_key = orchestrator._build_cache_key(request, "vast")
    cached_value = await cache_backend.get(cache_key)
    assert cached_value is None

    await orchestrator.close()


@pytest.mark.asyncio
async def test_orchestrator_caching_only_successful_responses(sample_vast_xml: str) -> None:
    """Test that only successful responses are cached."""
    # Create handler that will fail
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

    cache_backend = InMemoryStateBackend()
    orchestrator = Orchestrator(
        handlers={"vast": handler},
        cache_backend=cache_backend,
        enable_caching=True,
    )

    request = AdRequest(protocol="vast", user_id="user123")

    # Request will fail (max depth exceeded)
    response = await orchestrator.serve(request)
    assert response.status == "error"

    # Error response should not be cached
    cache_key = orchestrator._build_cache_key(request, "vast")
    cached_value = await cache_backend.get(cache_key)
    assert cached_value is None

    await orchestrator.close()
