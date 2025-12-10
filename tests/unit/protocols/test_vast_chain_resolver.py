"""Tests for VAST wrapper chain resolver."""

from typing import Any

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

    # Phase 2: Returns creative with selected media file
    assert creative is not None
    assert creative["type"] == "InLine"
    assert creative["ad_system"] == "TestSystem"
    assert creative["ad_title"] == "Test InLine Ad"
    assert creative["selected_media_file"] is not None
    await upstream.close()


# Phase 2 Tests - Creative Resolution and Selection


@pytest.fixture
def multibitrate_inline_xml() -> str:
    """VAST InLine with multiple media files at different bitrates."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="multi-bitrate-ad">
        <InLine>
            <AdSystem>MultiSystem</AdSystem>
            <AdTitle>Multi-Bitrate Ad</AdTitle>
            <Impression><![CDATA[https://impression1.example.com/imp1]]></Impression>
            <Impression><![CDATA[https://impression2.example.com/imp2]]></Impression>
            <Error><![CDATA[https://error.example.com/err?code=[ERRORCODE]]]></Error>
            <Creatives>
                <Creative>
                    <Linear>
                        <TrackingEvents>
                            <Tracking event="start"><![CDATA[https://track.example.com/start]]></Tracking>
                            <Tracking event="complete"><![CDATA[https://track.example.com/complete]]></Tracking>
                        </TrackingEvents>
                        <MediaFiles>
                            <MediaFile delivery="progressive" type="video/mp4"
                                       width="640" height="360" bitrate="500">
                                <![CDATA[https://cdn.example.com/video-low.mp4]]>
                            </MediaFile>
                            <MediaFile delivery="progressive" type="video/mp4"
                                       width="1280" height="720" bitrate="1500">
                                <![CDATA[https://cdn.example.com/video-medium.mp4]]>
                            </MediaFile>
                            <MediaFile delivery="progressive" type="video/mp4"
                                       width="1920" height="1080" bitrate="3000">
                                <![CDATA[https://cdn.example.com/video-high.mp4]]>
                            </MediaFile>
                            <MediaFile delivery="streaming" type="video/mp4"
                                       width="3840" height="2160" bitrate="8000">
                                <![CDATA[https://cdn.example.com/video-4k.mp4]]>
                            </MediaFile>
                        </MediaFiles>
                    </Linear>
                </Creative>
            </Creatives>
        </InLine>
    </Ad>
</VAST>"""


@pytest.fixture
def wrapper_with_tracking_xml() -> str:
    """VAST Wrapper with impression and error tracking."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="wrapper-with-tracking">
        <Wrapper>
            <AdSystem>WrapperWithTracking</AdSystem>
            <VASTAdTagURI><![CDATA[https://inline.example.com/vast]]></VASTAdTagURI>
            <Impression><![CDATA[https://wrapper.example.com/imp1]]></Impression>
            <Impression><![CDATA[https://wrapper.example.com/imp2]]></Impression>
            <Error><![CDATA[https://wrapper.example.com/error]]></Error>
        </Wrapper>
    </Ad>
</VAST>"""


@pytest.mark.asyncio
async def test_highest_bitrate_selection(multibitrate_inline_xml: str) -> None:
    """Test creative selection with HIGHEST_BITRATE strategy."""
    from xsp.protocols.vast.chain import SelectionStrategy

    config = VastChainConfig(selection_strategy=SelectionStrategy.HIGHEST_BITRATE)
    transport = MemoryTransport(b"")
    upstream = VastUpstream(transport=transport, endpoint="https://test.com")
    resolver = VastChainResolver(config, {"primary": upstream})

    vast_data = resolver._parse_vast_xml(multibitrate_inline_xml)
    creative = resolver._select_creative(vast_data)

    assert creative is not None
    assert creative["selected_media_file"]["bitrate"] == 8000
    assert creative["selected_media_file"]["width"] == 3840
    assert creative["selected_media_file"]["uri"] == "https://cdn.example.com/video-4k.mp4"
    await upstream.close()


@pytest.mark.asyncio
async def test_lowest_bitrate_selection(multibitrate_inline_xml: str) -> None:
    """Test creative selection with LOWEST_BITRATE strategy."""
    from xsp.protocols.vast.chain import SelectionStrategy

    config = VastChainConfig(selection_strategy=SelectionStrategy.LOWEST_BITRATE)
    transport = MemoryTransport(b"")
    upstream = VastUpstream(transport=transport, endpoint="https://test.com")
    resolver = VastChainResolver(config, {"primary": upstream})

    vast_data = resolver._parse_vast_xml(multibitrate_inline_xml)
    creative = resolver._select_creative(vast_data)

    assert creative is not None
    assert creative["selected_media_file"]["bitrate"] == 500
    assert creative["selected_media_file"]["width"] == 640
    assert creative["selected_media_file"]["uri"] == "https://cdn.example.com/video-low.mp4"
    await upstream.close()


@pytest.mark.asyncio
async def test_best_quality_selection_high(multibitrate_inline_xml: str) -> None:
    """Test creative selection with BEST_QUALITY strategy (high bitrate available)."""
    from xsp.protocols.vast.chain import SelectionStrategy

    config = VastChainConfig(selection_strategy=SelectionStrategy.BEST_QUALITY)
    transport = MemoryTransport(b"")
    upstream = VastUpstream(transport=transport, endpoint="https://test.com")
    resolver = VastChainResolver(config, {"primary": upstream})

    vast_data = resolver._parse_vast_xml(multibitrate_inline_xml)
    creative = resolver._select_creative(vast_data)

    assert creative is not None
    # Should select highest since highest bitrate >= 1000kbps
    assert creative["selected_media_file"]["bitrate"] == 8000
    await upstream.close()


@pytest.mark.asyncio
async def test_best_quality_selection_mobile() -> None:
    """Test creative selection with BEST_QUALITY strategy (mobile-friendly fallback)."""
    from xsp.protocols.vast.chain import SelectionStrategy

    # VAST with only low bitrate options (mobile scenario)
    mobile_xml = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="mobile-ad">
        <InLine>
            <AdSystem>MobileSystem</AdSystem>
            <AdTitle>Mobile Ad</AdTitle>
            <Creatives>
                <Creative>
                    <Linear>
                        <MediaFiles>
                            <MediaFile delivery="progressive" type="video/mp4"
                                       width="480" height="270" bitrate="300">
                                <![CDATA[https://cdn.example.com/mobile-low.mp4]]>
                            </MediaFile>
                            <MediaFile delivery="progressive" type="video/mp4"
                                       width="640" height="360" bitrate="600">
                                <![CDATA[https://cdn.example.com/mobile-high.mp4]]>
                            </MediaFile>
                        </MediaFiles>
                    </Linear>
                </Creative>
            </Creatives>
        </InLine>
    </Ad>
</VAST>"""

    config = VastChainConfig(selection_strategy=SelectionStrategy.BEST_QUALITY)
    transport = MemoryTransport(b"")
    upstream = VastUpstream(transport=transport, endpoint="https://test.com")
    resolver = VastChainResolver(config, {"primary": upstream})

    vast_data = resolver._parse_vast_xml(mobile_xml)
    creative = resolver._select_creative(vast_data)

    assert creative is not None
    # Should select lowest since all bitrates < 1000kbps
    assert creative["selected_media_file"]["bitrate"] == 300
    await upstream.close()


@pytest.mark.asyncio
async def test_custom_selection_strategy() -> None:
    """Test creative selection with CUSTOM strategy."""
    from xsp.protocols.vast.chain import SelectionStrategy

    multibitrate_xml = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="custom-select-ad">
        <InLine>
            <AdSystem>CustomSystem</AdSystem>
            <AdTitle>Custom Selection Ad</AdTitle>
            <Creatives>
                <Creative>
                    <Linear>
                        <MediaFiles>
                            <MediaFile delivery="progressive" type="video/mp4"
                                       width="640" height="360" bitrate="500">
                                <![CDATA[https://cdn.example.com/sd.mp4]]>
                            </MediaFile>
                            <MediaFile delivery="progressive" type="video/mp4"
                                       width="1280" height="720" bitrate="1500">
                                <![CDATA[https://cdn.example.com/hd.mp4]]>
                            </MediaFile>
                            <MediaFile delivery="progressive" type="video/mp4"
                                       width="1920" height="1080" bitrate="3000">
                                <![CDATA[https://cdn.example.com/fullhd.mp4]]>
                            </MediaFile>
                        </MediaFiles>
                    </Linear>
                </Creative>
            </Creatives>
        </InLine>
    </Ad>
</VAST>"""

    # Define custom selector: select first HD file (720p or higher)
    def select_hd(media_files: list[dict[str, Any]]) -> dict[str, Any] | None:
        for mf in media_files:
            if mf.get("height", 0) >= 720:
                return mf
        return media_files[0] if media_files else None

    config = VastChainConfig(selection_strategy=SelectionStrategy.CUSTOM)
    transport = MemoryTransport(b"")
    upstream = VastUpstream(transport=transport, endpoint="https://test.com")
    resolver = VastChainResolver(config, {"primary": upstream})
    resolver.set_custom_selector(select_hd)

    vast_data = resolver._parse_vast_xml(multibitrate_xml)
    creative = resolver._select_creative(vast_data)

    assert creative is not None
    # Should select first 720p file
    assert creative["selected_media_file"]["height"] == 720
    assert creative["selected_media_file"]["uri"] == "https://cdn.example.com/hd.mp4"
    await upstream.close()


@pytest.mark.asyncio
async def test_custom_selection_without_selector() -> None:
    """Test that CUSTOM strategy without custom selector raises error."""
    from xsp.protocols.vast.chain import SelectionStrategy
    from xsp.core.exceptions import UpstreamError

    inline_xml = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="test-ad">
        <InLine>
            <AdSystem>TestSystem</AdSystem>
            <AdTitle>Test Ad</AdTitle>
            <Creatives>
                <Creative>
                    <Linear>
                        <MediaFiles>
                            <MediaFile delivery="progressive" type="video/mp4"
                                       width="640" height="360" bitrate="500">
                                <![CDATA[https://cdn.example.com/video.mp4]]>
                            </MediaFile>
                        </MediaFiles>
                    </Linear>
                </Creative>
            </Creatives>
        </InLine>
    </Ad>
</VAST>"""

    config = VastChainConfig(selection_strategy=SelectionStrategy.CUSTOM)
    transport = MemoryTransport(b"")
    upstream = VastUpstream(transport=transport, endpoint="https://test.com")
    resolver = VastChainResolver(config, {"primary": upstream})
    # Don't set custom selector

    vast_data = resolver._parse_vast_xml(inline_xml)

    with pytest.raises(UpstreamError, match="CUSTOM selection strategy requires"):
        resolver._select_creative(vast_data)

    await upstream.close()


@pytest.mark.asyncio
async def test_impression_collection(
    wrapper_with_tracking_xml: str, multibitrate_inline_xml: str
) -> None:
    """Test impression URL collection through wrapper chain."""
    responses = {
        "https://ads.example.com/vast": wrapper_with_tracking_xml.encode("utf-8"),
        "https://inline.example.com/vast": multibitrate_inline_xml.encode("utf-8"),
    }
    transport = MockTransport(responses)
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
    )

    config = VastChainConfig(collect_tracking_urls=True)
    resolver = VastChainResolver(config, {"primary": upstream})

    result = await resolver.resolve()

    assert result.success is True
    assert result.vast_data is not None
    # Should have impressions from both wrapper and inline
    impressions = result.vast_data.get("impressions", [])
    assert len(impressions) == 4  # 2 from wrapper + 2 from inline
    assert "https://wrapper.example.com/imp1" in impressions
    assert "https://wrapper.example.com/imp2" in impressions
    assert "https://impression1.example.com/imp1" in impressions
    assert "https://impression2.example.com/imp2" in impressions
    await upstream.close()


@pytest.mark.asyncio
async def test_error_url_collection(
    wrapper_with_tracking_xml: str, multibitrate_inline_xml: str
) -> None:
    """Test error URL collection through wrapper chain."""
    responses = {
        "https://ads.example.com/vast": wrapper_with_tracking_xml.encode("utf-8"),
        "https://inline.example.com/vast": multibitrate_inline_xml.encode("utf-8"),
    }
    transport = MockTransport(responses)
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
    )

    config = VastChainConfig(collect_error_urls=True)
    resolver = VastChainResolver(config, {"primary": upstream})

    result = await resolver.resolve()

    assert result.success is True
    assert result.vast_data is not None
    # Should have error URLs from both wrapper and inline
    error_urls = result.vast_data.get("error_urls", [])
    assert len(error_urls) == 2  # 1 from wrapper + 1 from inline
    assert "https://wrapper.example.com/error" in error_urls
    assert "https://error.example.com/err?code=[ERRORCODE]" in error_urls
    await upstream.close()


@pytest.mark.asyncio
async def test_media_file_parsing(multibitrate_inline_xml: str) -> None:
    """Test MediaFile parsing with various attributes."""
    config = VastChainConfig()
    transport = MemoryTransport(b"")
    upstream = VastUpstream(transport=transport, endpoint="https://test.com")
    resolver = VastChainResolver(config, {"primary": upstream})

    vast_data = resolver._parse_vast_xml(multibitrate_inline_xml)

    assert vast_data["ad_system"] == "MultiSystem"
    assert vast_data["ad_title"] == "Multi-Bitrate Ad"

    media_files = vast_data["media_files"]
    assert len(media_files) == 4

    # Check first media file (low bitrate)
    mf1 = media_files[0]
    assert mf1["delivery"] == "progressive"
    assert mf1["type"] == "video/mp4"
    assert mf1["width"] == 640
    assert mf1["height"] == 360
    assert mf1["bitrate"] == 500
    assert mf1["uri"] == "https://cdn.example.com/video-low.mp4"

    # Check last media file (4K)
    mf4 = media_files[3]
    assert mf4["delivery"] == "streaming"
    assert mf4["bitrate"] == 8000
    assert mf4["width"] == 3840

    # Check tracking events
    tracking = vast_data["tracking_events"]
    assert "start" in tracking
    assert "complete" in tracking
    assert len(tracking["start"]) == 1
    assert tracking["start"][0] == "https://track.example.com/start"

    await upstream.close()


@pytest.mark.asyncio
async def test_no_media_files_available() -> None:
    """Test edge case: no media files available."""
    from xsp.protocols.vast.chain import SelectionStrategy

    # VAST with no media files
    no_media_xml = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="no-media-ad">
        <InLine>
            <AdSystem>NoMediaSystem</AdSystem>
            <AdTitle>No Media Ad</AdTitle>
            <Creatives>
                <Creative>
                    <Linear>
                        <MediaFiles>
                        </MediaFiles>
                    </Linear>
                </Creative>
            </Creatives>
        </InLine>
    </Ad>
</VAST>"""

    config = VastChainConfig(selection_strategy=SelectionStrategy.HIGHEST_BITRATE)
    transport = MemoryTransport(b"")
    upstream = VastUpstream(transport=transport, endpoint="https://test.com")
    resolver = VastChainResolver(config, {"primary": upstream})

    vast_data = resolver._parse_vast_xml(no_media_xml)
    creative = resolver._select_creative(vast_data)

    assert creative is None  # No creative available
    await upstream.close()


@pytest.mark.asyncio
async def test_collect_impressions_method(multibitrate_inline_xml: str) -> None:
    """Test _collect_impressions method directly."""
    config = VastChainConfig()
    transport = MemoryTransport(b"")
    upstream = VastUpstream(transport=transport, endpoint="https://test.com")
    resolver = VastChainResolver(config, {"primary": upstream})

    impressions = resolver._collect_impressions(multibitrate_inline_xml)

    assert len(impressions) == 2
    assert "https://impression1.example.com/imp1" in impressions
    assert "https://impression2.example.com/imp2" in impressions
    await upstream.close()


@pytest.mark.asyncio
async def test_collect_error_urls_method(multibitrate_inline_xml: str) -> None:
    """Test _collect_error_urls method directly."""
    config = VastChainConfig()
    transport = MemoryTransport(b"")
    upstream = VastUpstream(transport=transport, endpoint="https://test.com")
    resolver = VastChainResolver(config, {"primary": upstream})

    error_urls = resolver._collect_error_urls(multibitrate_inline_xml)

    assert len(error_urls) == 1
    assert "https://error.example.com/err?code=[ERRORCODE]" in error_urls
    await upstream.close()


@pytest.mark.asyncio
async def test_tracking_disabled() -> None:
    """Test that tracking collection can be disabled."""
    wrapper_xml = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="wrapper-ad">
        <Wrapper>
            <AdSystem>WrapperSystem</AdSystem>
            <VASTAdTagURI><![CDATA[https://inline.example.com/vast]]></VASTAdTagURI>
            <Impression><![CDATA[https://wrapper.example.com/imp]]></Impression>
            <Error><![CDATA[https://wrapper.example.com/error]]></Error>
        </Wrapper>
    </Ad>
</VAST>"""

    inline_xml = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="inline-ad">
        <InLine>
            <AdSystem>InlineSystem</AdSystem>
            <AdTitle>Inline Ad</AdTitle>
            <Impression><![CDATA[https://inline.example.com/imp]]></Impression>
            <Creatives>
                <Creative>
                    <Linear>
                        <MediaFiles>
                            <MediaFile delivery="progressive" type="video/mp4"
                                       width="640" height="360" bitrate="500">
                                <![CDATA[https://cdn.example.com/video.mp4]]>
                            </MediaFile>
                        </MediaFiles>
                    </Linear>
                </Creative>
            </Creatives>
        </InLine>
    </Ad>
</VAST>"""

    responses = {
        "https://ads.example.com/vast": wrapper_xml.encode("utf-8"),
        "https://inline.example.com/vast": inline_xml.encode("utf-8"),
    }
    transport = MockTransport(responses)
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
    )

    config = VastChainConfig(collect_tracking_urls=False, collect_error_urls=False)
    resolver = VastChainResolver(config, {"primary": upstream})

    result = await resolver.resolve()

    assert result.success is True
    assert result.vast_data is not None
    # Should have empty tracking arrays when disabled
    impressions = result.vast_data.get("impressions", [])
    error_urls = result.vast_data.get("error_urls", [])
    assert len(impressions) == 0
    assert len(error_urls) == 0
    await upstream.close()
