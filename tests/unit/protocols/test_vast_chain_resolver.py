"""Tests for VAST wrapper chain resolver."""

import pytest

from xsp.core.exceptions import UpstreamError
from xsp.protocols.vast.chain import (
    VastChainConfig,
)
from xsp.protocols.vast.chain_resolver import VastChainResolver
from xsp.protocols.vast.upstream import VastUpstream
from xsp.transports.memory import MemoryTransport


@pytest.fixture
def inline_vast_xml() -> str:
    """Sample VAST InLine response."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="inline-ad-123">
        <InLine>
            <AdSystem>TestSystem</AdSystem>
            <AdTitle>Test InLine Ad</AdTitle>
            <Impression><![CDATA[https://impression.example.com/imp?id=123]]></Impression>
            <Creatives>
                <Creative>
                    <Linear>
                        <MediaFiles>
                            <MediaFile delivery="progressive" type="video/mp4"
                                       width="1920" height="1080" bitrate="2000">
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
def wrapper_vast_xml() -> str:
    """Sample VAST Wrapper response."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="wrapper-ad-456">
        <Wrapper>
            <AdSystem>WrapperSystem</AdSystem>
            <VASTAdTagURI><![CDATA[https://next.example.com/vast?id=789]]></VASTAdTagURI>
            <Impression><![CDATA[https://wrapper-impression.example.com/imp]]></Impression>
        </Wrapper>
    </Ad>
</VAST>"""


@pytest.fixture
def two_level_wrapper_xml() -> str:
    """Second level wrapper that points to inline."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="wrapper-level-2">
        <Wrapper>
            <AdSystem>SecondLevelWrapper</AdSystem>
            <VASTAdTagURI><![CDATA[https://final.example.com/vast?id=final]]></VASTAdTagURI>
        </Wrapper>
    </Ad>
</VAST>"""


class MockTransport:
    """Mock transport that returns different responses based on endpoint."""

    def __init__(self, responses: dict[str, bytes]) -> None:
        """Initialize with response mapping.

        Args:
            responses: Map of endpoint URLs to response bytes
        """
        self.responses = responses
        self.call_count = 0

    async def send(
        self,
        endpoint: str,
        payload: bytes | None = None,
        metadata: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> bytes:
        """Return response based on endpoint."""
        self.call_count += 1

        # Find matching response
        for url_pattern, response in self.responses.items():
            if url_pattern in endpoint or endpoint == url_pattern:
                return response

        # Default to first response if no match
        return next(iter(self.responses.values()))

    async def close(self) -> None:
        """No-op for mock transport."""
        pass


@pytest.mark.asyncio
async def test_resolve_inline_response(inline_vast_xml: str) -> None:
    """Test resolving a direct InLine response (no wrapper chain)."""
    transport = MemoryTransport(inline_vast_xml.encode("utf-8"))
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
    )

    config = VastChainConfig(max_depth=5)
    resolver = VastChainResolver(config, {"primary": upstream})

    result = await resolver.resolve()

    assert result.success is True
    assert result.xml == inline_vast_xml
    assert result.used_fallback is False
    assert len(result.chain) == 1
    assert result.vast_data is not None
    assert result.vast_data["version"] == "4.2"
    assert len(result.vast_data["ads"]) == 1
    assert result.vast_data["ads"][0]["type"] == "InLine"
    assert result.resolution_time_ms is not None
    await upstream.close()


@pytest.mark.asyncio
async def test_resolve_wrapper_chain(wrapper_vast_xml: str, inline_vast_xml: str) -> None:
    """Test resolving a 2-level wrapper chain."""
    # Set up mock transport that returns wrapper first, then inline
    responses = {
        "https://ads.example.com/vast": wrapper_vast_xml.encode("utf-8"),
        "https://next.example.com/vast?id=789": inline_vast_xml.encode("utf-8"),
    }
    transport = MockTransport(responses)
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
    )

    config = VastChainConfig(max_depth=5)
    resolver = VastChainResolver(config, {"primary": upstream})

    result = await resolver.resolve()

    assert result.success is True
    assert result.used_fallback is False
    assert len(result.chain) == 2
    assert "https://ads.example.com/vast" in result.chain[0]
    assert "https://next.example.com/vast?id=789" in result.chain[1]
    assert result.vast_data is not None
    assert result.vast_data["ads"][0]["type"] == "InLine"
    await upstream.close()


@pytest.mark.asyncio
async def test_resolve_three_level_wrapper_chain(
    wrapper_vast_xml: str,
    two_level_wrapper_xml: str,
    inline_vast_xml: str,
) -> None:
    """Test resolving a 3-level wrapper chain."""
    responses = {
        "https://ads.example.com/vast": wrapper_vast_xml.encode("utf-8"),
        "https://next.example.com/vast?id=789": two_level_wrapper_xml.encode("utf-8"),
        "https://final.example.com/vast?id=final": inline_vast_xml.encode("utf-8"),
    }
    transport = MockTransport(responses)
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
    )

    config = VastChainConfig(max_depth=5)
    resolver = VastChainResolver(config, {"primary": upstream})

    result = await resolver.resolve()

    assert result.success is True
    assert len(result.chain) == 3
    assert result.vast_data["ads"][0]["type"] == "InLine"
    await upstream.close()


@pytest.mark.asyncio
async def test_depth_limit_protection(wrapper_vast_xml: str) -> None:
    """Test that depth limit prevents infinite loops."""
    # Mock transport that always returns wrapper (infinite loop scenario)
    transport = MemoryTransport(wrapper_vast_xml.encode("utf-8"))
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
    )

    config = VastChainConfig(max_depth=3)
    resolver = VastChainResolver(config, {"primary": upstream})

    result = await resolver.resolve()

    # Should fail due to depth limit
    assert result.success is False
    assert result.error is not None
    assert isinstance(result.error, UpstreamError)
    assert "depth" in str(result.error).lower()
    await upstream.close()


@pytest.mark.asyncio
async def test_fallback_on_primary_failure(inline_vast_xml: str) -> None:
    """Test fallback to secondary upstream when primary fails."""

    # Primary upstream that fails
    class FailingTransport:
        async def send(
            self,
            endpoint: str,
            payload: bytes | None = None,
            metadata: dict[str, str] | None = None,
            timeout: float | None = None,
        ) -> bytes:
            raise RuntimeError("Primary upstream failed")

        async def close(self) -> None:
            pass

    primary_transport = FailingTransport()
    primary_upstream = VastUpstream(
        transport=primary_transport,
        endpoint="https://primary.example.com/vast",
    )

    # Secondary upstream that succeeds
    secondary_transport = MemoryTransport(inline_vast_xml.encode("utf-8"))
    secondary_upstream = VastUpstream(
        transport=secondary_transport,
        endpoint="https://secondary.example.com/vast",
    )

    config = VastChainConfig(enable_fallbacks=True)
    resolver = VastChainResolver(
        config,
        {
            "primary": primary_upstream,
            "secondary": secondary_upstream,
        },
    )

    result = await resolver.resolve()

    assert result.success is True
    assert result.used_fallback is True
    assert result.vast_data is not None
    await primary_upstream.close()
    await secondary_upstream.close()


@pytest.mark.asyncio
async def test_all_upstreams_fail() -> None:
    """Test error handling when all upstreams fail."""

    class FailingTransport:
        async def send(
            self,
            endpoint: str,
            payload: bytes | None = None,
            metadata: dict[str, str] | None = None,
            timeout: float | None = None,
        ) -> bytes:
            raise RuntimeError("Upstream failed")

        async def close(self) -> None:
            pass

    primary_upstream = VastUpstream(
        transport=FailingTransport(),
        endpoint="https://primary.example.com/vast",
    )
    secondary_upstream = VastUpstream(
        transport=FailingTransport(),
        endpoint="https://secondary.example.com/vast",
    )

    config = VastChainConfig(enable_fallbacks=True)
    resolver = VastChainResolver(
        config,
        {
            "primary": primary_upstream,
            "secondary": secondary_upstream,
        },
    )

    result = await resolver.resolve()

    assert result.success is False
    assert result.error is not None
    assert result.used_fallback is False
    await primary_upstream.close()
    await secondary_upstream.close()


@pytest.mark.asyncio
async def test_fallbacks_disabled(inline_vast_xml: str) -> None:
    """Test that fallbacks are not used when disabled."""

    class FailingTransport:
        async def send(
            self,
            endpoint: str,
            payload: bytes | None = None,
            metadata: dict[str, str] | None = None,
            timeout: float | None = None,
        ) -> bytes:
            raise RuntimeError("Primary failed")

        async def close(self) -> None:
            pass

    primary_upstream = VastUpstream(
        transport=FailingTransport(),
        endpoint="https://primary.example.com/vast",
    )
    secondary_upstream = VastUpstream(
        transport=MemoryTransport(inline_vast_xml.encode("utf-8")),
        endpoint="https://secondary.example.com/vast",
    )

    config = VastChainConfig(enable_fallbacks=False)
    resolver = VastChainResolver(
        config,
        {
            "primary": primary_upstream,
            "secondary": secondary_upstream,
        },
    )

    result = await resolver.resolve()

    # Should fail without using fallback
    assert result.success is False
    assert result.used_fallback is False
    await primary_upstream.close()
    await secondary_upstream.close()


@pytest.mark.asyncio
async def test_is_wrapper_detection(wrapper_vast_xml: str, inline_vast_xml: str) -> None:
    """Test wrapper vs inline detection."""
    config = VastChainConfig()
    transport = MemoryTransport(b"")
    upstream = VastUpstream(transport=transport, endpoint="https://test.com")
    resolver = VastChainResolver(config, {"primary": upstream})

    assert resolver._is_wrapper(wrapper_vast_xml) is True
    assert resolver._is_wrapper(inline_vast_xml) is False
    await upstream.close()


@pytest.mark.asyncio
async def test_is_inline_detection(wrapper_vast_xml: str, inline_vast_xml: str) -> None:
    """Test inline detection."""
    config = VastChainConfig()
    transport = MemoryTransport(b"")
    upstream = VastUpstream(transport=transport, endpoint="https://test.com")
    resolver = VastChainResolver(config, {"primary": upstream})

    assert resolver._is_inline(inline_vast_xml) is True
    assert resolver._is_inline(wrapper_vast_xml) is False
    await upstream.close()


@pytest.mark.asyncio
async def test_extract_wrapper_url(wrapper_vast_xml: str) -> None:
    """Test extraction of VASTAdTagURI from wrapper."""
    config = VastChainConfig()
    transport = MemoryTransport(b"")
    upstream = VastUpstream(transport=transport, endpoint="https://test.com")
    resolver = VastChainResolver(config, {"primary": upstream})

    url = resolver._extract_wrapper_url(wrapper_vast_xml)
    assert url == "https://next.example.com/vast?id=789"
    await upstream.close()


@pytest.mark.asyncio
async def test_config_additional_params(inline_vast_xml: str) -> None:
    """Test that additional params from config are used."""
    transport = MemoryTransport(inline_vast_xml.encode("utf-8"))
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
    )

    config = VastChainConfig(additional_params={"custom_param": "value123"})
    resolver = VastChainResolver(config, {"primary": upstream})

    result = await resolver.resolve()

    assert result.success is True
    await upstream.close()


@pytest.mark.asyncio
async def test_empty_upstreams_raises_error() -> None:
    """Test that empty upstreams dict raises ValueError."""
    config = VastChainConfig()

    with pytest.raises(ValueError, match="At least one upstream"):
        VastChainResolver(config, {})


@pytest.mark.asyncio
async def test_resolution_time_tracking(inline_vast_xml: str) -> None:
    """Test that resolution time is tracked."""
    transport = MemoryTransport(inline_vast_xml.encode("utf-8"))
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
    )

    config = VastChainConfig()
    resolver = VastChainResolver(config, {"primary": upstream})

    result = await resolver.resolve()

    assert result.resolution_time_ms is not None
    assert result.resolution_time_ms >= 0
    await upstream.close()


@pytest.mark.asyncio
async def test_parse_vast_xml(inline_vast_xml: str) -> None:
    """Test VAST XML parsing."""
    config = VastChainConfig()
    transport = MemoryTransport(b"")
    upstream = VastUpstream(transport=transport, endpoint="https://test.com")
    resolver = VastChainResolver(config, {"primary": upstream})

    vast_data = resolver._parse_vast_xml(inline_vast_xml)

    assert vast_data["version"] == "4.2"
    assert len(vast_data["ads"]) == 1
    assert vast_data["ads"][0]["id"] == "inline-ad-123"
    assert vast_data["ads"][0]["type"] == "InLine"
    assert vast_data["ads"][0]["ad_system"] == "TestSystem"
    assert vast_data["ads"][0]["ad_title"] == "Test InLine Ad"
    await upstream.close()


@pytest.mark.asyncio
async def test_creative_selection(inline_vast_xml: str) -> None:
    """Test creative selection (Phase 1 stub)."""
    config = VastChainConfig()
    transport = MemoryTransport(b"")
    upstream = VastUpstream(transport=transport, endpoint="https://test.com")
    resolver = VastChainResolver(config, {"primary": upstream})

    vast_data = resolver._parse_vast_xml(inline_vast_xml)
    creative = resolver._select_creative(vast_data)

    # Phase 1: Just returns first ad
    assert creative is not None
    assert creative["type"] == "InLine"
    await upstream.close()
