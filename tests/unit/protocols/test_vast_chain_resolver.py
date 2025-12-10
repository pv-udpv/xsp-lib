"""Tests for VAST chain resolver."""

import pytest

from xsp.protocols.vast import ChainResolver, MaxDepthExceededError, VastUpstream
from xsp.transports.memory import MemoryTransport


@pytest.fixture
def sample_inline_vast() -> str:
    """Sample inline VAST ad."""
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


@pytest.fixture
def sample_wrapper_vast() -> str:
    """Sample VAST wrapper."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="wrapper1">
        <Wrapper>
            <AdSystem>WrapperSystem</AdSystem>
            <VASTAdTagURI><![CDATA[https://ads.example.com/inline]]></VASTAdTagURI>
            <Impression><![CDATA[https://wrapper.example.com/imp]]></Impression>
        </Wrapper>
    </Ad>
</VAST>"""


@pytest.mark.asyncio
async def test_chain_resolver_inline_ad(sample_inline_vast: str) -> None:
    """Test resolving inline ad (no wrappers)."""
    transport = MemoryTransport(sample_inline_vast.encode("utf-8"))
    upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")
    resolver = ChainResolver(upstream=upstream)

    result = await resolver.resolve()

    assert "<InLine>" in result
    assert "Test Ad" in result

    await resolver.close()


@pytest.mark.asyncio
async def test_chain_resolver_empty_vast() -> None:
    """Test resolving empty VAST."""
    empty_vast = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
</VAST>"""

    transport = MemoryTransport(empty_vast.encode("utf-8"))
    upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")
    resolver = ChainResolver(upstream=upstream)

    result = await resolver.resolve()

    assert "<VAST" in result

    await resolver.close()


@pytest.mark.asyncio
async def test_chain_resolver_max_depth_exceeded(sample_wrapper_vast: str) -> None:
    """Test max depth protection."""
    transport = MemoryTransport(sample_wrapper_vast.encode("utf-8"))
    upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")
    resolver = ChainResolver(upstream=upstream, max_depth=2)

    # Wrapper points to itself in a loop, should hit max depth
    with pytest.raises(MaxDepthExceededError) as exc_info:
        await resolver.resolve()

    assert "Maximum wrapper depth" in str(exc_info.value)

    await resolver.close()


@pytest.mark.asyncio
async def test_chain_resolver_with_params(sample_inline_vast: str) -> None:
    """Test resolver with query parameters."""
    transport = MemoryTransport(sample_inline_vast.encode("utf-8"))
    upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")
    resolver = ChainResolver(upstream=upstream)

    result = await resolver.resolve(params={"user_id": "123", "placement": "banner"})

    assert "<InLine>" in result

    await resolver.close()


@pytest.mark.asyncio
async def test_chain_resolver_with_headers(sample_inline_vast: str) -> None:
    """Test resolver with session headers."""
    transport = MemoryTransport(sample_inline_vast.encode("utf-8"))
    upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")
    resolver = ChainResolver(upstream=upstream, propagate_headers=True)

    result = await resolver.resolve(headers={"Cookie": "session=abc123"})

    assert "<InLine>" in result

    await resolver.close()
