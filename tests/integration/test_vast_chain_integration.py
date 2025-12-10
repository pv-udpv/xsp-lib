"""Integration tests for VAST chain resolver with YAML config and tracking.

Tests end-to-end scenarios including:
- Loading configuration from YAML
- Resolving wrapper chains
- Sending tracking pixels (impression and error)
- Environment variable substitution
"""

import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from xsp.protocols.vast import VastChainConfigLoader, VastChainResolver
from xsp.protocols.vast.types import VastResolutionResult


@pytest.fixture
def config_path() -> Path:
    """Path to test YAML configuration."""
    return Path(__file__).parent.parent / "fixtures" / "vast_chains.yaml"


@pytest.fixture
def mock_transport() -> MagicMock:
    """Mock transport for testing."""
    transport = MagicMock()
    transport.transport_type = MagicMock(return_value="http")
    transport.send = AsyncMock()
    transport.close = AsyncMock()
    return transport


@pytest.fixture
def sample_vast_inline() -> str:
    """Sample VAST InLine response for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="12345">
        <InLine>
            <AdSystem>Test Ad System</AdSystem>
            <AdTitle>Test Ad</AdTitle>
            <Impression><![CDATA[https://track.example.com/impression?id=123]]></Impression>
            <Error><![CDATA[https://track.example.com/error?code=[ERRORCODE]]]></Error>
            <Creatives>
                <Creative>
                    <Linear>
                        <MediaFiles>
                            <MediaFile delivery="progressive" type="video/mp4"
                                       width="640" height="480" bitrate="1200">
                                <![CDATA[https://cdn.example.com/video.mp4]]>
                            </MediaFile>
                            <MediaFile delivery="progressive" type="video/mp4"
                                       width="1280" height="720" bitrate="2400">
                                <![CDATA[https://cdn.example.com/video-hd.mp4]]>
                            </MediaFile>
                        </MediaFiles>
                    </Linear>
                </Creative>
            </Creatives>
        </InLine>
    </Ad>
</VAST>"""


@pytest.fixture
def sample_vast_wrapper() -> str:
    """Sample VAST Wrapper response for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="wrapper-1">
        <Wrapper>
            <AdSystem>Wrapper System</AdSystem>
            <VASTAdTagURI><![CDATA[https://inline.example.com/vast]]></VASTAdTagURI>
            <Impression><![CDATA[https://track.example.com/wrapper-impression]]></Impression>
            <Error><![CDATA[https://track.example.com/wrapper-error?code=[ERRORCODE]]]></Error>
        </Wrapper>
    </Ad>
</VAST>"""


class TestVastChainConfigLoader:
    """Test YAML configuration loading."""

    def test_load_config_success(self, config_path: Path, mock_transport: MagicMock) -> None:
        """Test successful loading of YAML configuration."""
        resolvers = VastChainConfigLoader.load(config_path, mock_transport)

        # Should have all configured chains
        assert "default" in resolvers
        assert "high_quality" in resolvers
        assert "low_bandwidth" in resolvers
        assert "test_chain" in resolvers

        # Verify resolver types
        assert isinstance(resolvers["default"], VastChainResolver)
        assert isinstance(resolvers["high_quality"], VastChainResolver)

    def test_load_config_file_not_found(self, mock_transport: MagicMock) -> None:
        """Test error when config file doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            VastChainConfigLoader.load("nonexistent.yaml", mock_transport)

    def test_env_var_expansion_with_default(
        self, config_path: Path, mock_transport: MagicMock
    ) -> None:
        """Test environment variable expansion with default value."""
        # Don't set TEST_VAST_ENDPOINT, should use default
        if "TEST_VAST_ENDPOINT" in os.environ:
            del os.environ["TEST_VAST_ENDPOINT"]

        resolvers = VastChainConfigLoader.load(config_path, mock_transport)

        # Test chain should use default endpoint
        test_resolver = resolvers["test_chain"]
        primary_key = next(iter(test_resolver.upstreams.keys()))
        upstream = test_resolver.upstreams[primary_key]

        # Should have default endpoint
        assert upstream.endpoint == "https://test.example.com/vast"

    def test_env_var_expansion_with_value(
        self, config_path: Path, mock_transport: MagicMock
    ) -> None:
        """Test environment variable expansion with actual value."""
        # Set environment variable
        os.environ["TEST_VAST_ENDPOINT"] = "https://custom-test.example.com/vast"

        try:
            resolvers = VastChainConfigLoader.load(config_path, mock_transport)

            # Test chain should use env var value
            test_resolver = resolvers["test_chain"]
            primary_key = next(iter(test_resolver.upstreams.keys()))
            upstream = test_resolver.upstreams[primary_key]

            # Should have custom endpoint from env var
            assert upstream.endpoint == "https://custom-test.example.com/vast"

        finally:
            # Clean up
            del os.environ["TEST_VAST_ENDPOINT"]

    def test_env_var_required_missing(self, tmp_path: Path, mock_transport: MagicMock) -> None:
        """Test error when required env var is missing."""
        # Create config with required env var (no default)
        config_content = """
upstreams:
  vast:
    test:
      endpoint: ${REQUIRED_VAR}
      version: "4.2"

chains:
  test:
    primary: vast.test
    fallbacks: []
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(config_content)

        # Should raise error for missing required env var
        with pytest.raises(ValueError, match="Required environment variable"):
            VastChainConfigLoader.load(config_file, mock_transport)


class TestVastChainIntegration:
    """Test end-to-end VAST chain resolution with tracking."""

    @pytest.mark.asyncio
    async def test_resolve_inline_with_impression_tracking(
        self, mock_transport: MagicMock, sample_vast_inline: str
    ) -> None:
        """Test resolving InLine VAST and tracking impressions."""
        # Setup mock transport to return InLine VAST
        mock_transport.send = AsyncMock(return_value=sample_vast_inline.encode("utf-8"))

        from xsp.protocols.vast import VastChainConfig, VastUpstream

        # Create upstream and resolver
        upstream = VastUpstream(
            transport=mock_transport,
            endpoint="https://primary.example.com/vast",
            version="4.2",
        )

        config = VastChainConfig(
            max_depth=5,
            collect_tracking_urls=True,
        )

        resolver = VastChainResolver(
            config=config,
            upstreams={"primary": upstream},
        )

        # Resolve
        result = await resolver.resolve(params={"w": "640", "h": "480"})

        # Verify resolution success
        assert result.success is True
        assert result.vast_data is not None
        assert len(result.chain) == 1

        # Verify impression URLs were collected
        assert "impressions" in result.vast_data
        impressions = result.vast_data["impressions"]
        assert len(impressions) > 0
        assert "https://track.example.com/impression?id=123" in impressions

    @pytest.mark.asyncio
    async def test_resolve_wrapper_chain_with_tracking(
        self,
        mock_transport: MagicMock,
        sample_vast_wrapper: str,
        sample_vast_inline: str,
    ) -> None:
        """Test resolving wrapper chain and collecting tracking URLs."""
        # Setup mock to return wrapper first, then inline
        responses = [
            sample_vast_wrapper.encode("utf-8"),
            sample_vast_inline.encode("utf-8"),
        ]
        mock_transport.send = AsyncMock(side_effect=responses)

        from xsp.protocols.vast import VastChainConfig, VastUpstream

        upstream = VastUpstream(
            transport=mock_transport,
            endpoint="https://primary.example.com/vast",
            version="4.2",
        )

        config = VastChainConfig(
            max_depth=5,
            collect_tracking_urls=True,
            collect_error_urls=True,
        )

        resolver = VastChainResolver(
            config=config,
            upstreams={"primary": upstream},
        )

        result = await resolver.resolve(params={})

        # Verify resolution success
        assert result.success is True
        assert len(result.chain) == 2  # Wrapper + InLine

        # Verify impressions from both wrapper and inline
        impressions = result.vast_data["impressions"]  # type: ignore[index]
        assert len(impressions) >= 2
        assert any("wrapper-impression" in url for url in impressions)
        assert any("impression?id=123" in url for url in impressions)

        # Verify error URLs collected
        error_urls = result.vast_data["error_urls"]  # type: ignore[index]
        assert len(error_urls) >= 2

    @pytest.mark.asyncio
    async def test_tracking_pixel_fire_and_forget(
        self, mock_transport: MagicMock, sample_vast_inline: str
    ) -> None:
        """Test that tracking pixels are sent in fire-and-forget mode."""
        # Setup mock
        mock_transport.send = AsyncMock(return_value=sample_vast_inline.encode("utf-8"))

        from xsp.protocols.vast import VastChainConfig, VastUpstream

        upstream = VastUpstream(
            transport=mock_transport,
            endpoint="https://primary.example.com/vast",
            version="4.2",
        )

        config = VastChainConfig(max_depth=5)
        resolver = VastChainResolver(config=config, upstreams={"primary": upstream})

        # Track impression
        await resolver._track_impression(["https://track.example.com/imp"])

        # Give async tasks time to execute
        await asyncio.sleep(0.1)

        # Verify tracking request was sent
        # Note: In fire-and-forget mode, we don't wait for completion
        # So we check if send was called with tracking URL
        calls = mock_transport.send.call_args_list
        tracking_calls = [call for call in calls if "track.example.com/imp" in str(call)]
        assert len(tracking_calls) > 0

    @pytest.mark.asyncio
    async def test_error_tracking_with_macro_substitution(self, mock_transport: MagicMock) -> None:
        """Test error tracking with [ERRORCODE] macro substitution."""
        from xsp.protocols.vast import VastChainConfig, VastUpstream

        upstream = VastUpstream(
            transport=mock_transport,
            endpoint="https://primary.example.com/vast",
            version="4.2",
        )

        config = VastChainConfig(max_depth=5)
        resolver = VastChainResolver(config=config, upstreams={"primary": upstream})

        # Track error with code 303
        error_urls = [
            "https://track.example.com/error?code=[ERRORCODE]",
            "https://track2.example.com/err?e=[ERRORCODE]",
        ]
        await resolver._track_error(error_urls, error_code="303")

        # Give async tasks time to execute
        await asyncio.sleep(0.1)

        # Verify error tracking requests were sent with substituted error code
        calls = mock_transport.send.call_args_list
        error_calls = [call for call in calls if "error" in str(call) or "err" in str(call)]

        # Should have sent requests with error code 303 substituted
        assert len(error_calls) > 0
        # Check that [ERRORCODE] was replaced with 303
        call_strs = [str(call) for call in error_calls]
        assert any("303" in s for s in call_strs)

    @pytest.mark.asyncio
    async def test_fallback_tracking(
        self, mock_transport: MagicMock, sample_vast_inline: str
    ) -> None:
        """Test fallback tracking logs appropriately."""
        from xsp.protocols.vast import VastChainConfig, VastUpstream

        upstream = VastUpstream(
            transport=mock_transport,
            endpoint="https://primary.example.com/vast",
            version="4.2",
        )

        config = VastChainConfig(max_depth=5)
        resolver = VastChainResolver(config=config, upstreams={"primary": upstream})

        # Create a result that used fallback
        result = VastResolutionResult(
            success=True,
            chain=["primary", "secondary"],
            used_fallback=True,
            resolution_time_ms=150.5,
        )

        # Track fallback (should just log)
        with patch("xsp.protocols.vast.chain_resolver.logger") as mock_logger:
            await resolver._track_fallback(result)
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert "Fallback upstream used" in call_args
            assert "150.50ms" in call_args

    @pytest.mark.asyncio
    async def test_end_to_end_with_yaml_config(
        self, config_path: Path, mock_transport: MagicMock, sample_vast_inline: str
    ) -> None:
        """Test complete workflow: load YAML -> resolve -> track."""
        # Setup mock
        mock_transport.send = AsyncMock(return_value=sample_vast_inline.encode("utf-8"))

        # Load configuration
        resolvers = VastChainConfigLoader.load(config_path, mock_transport)

        # Get default resolver
        default_resolver = resolvers["default"]

        # Resolve VAST chain
        result = await default_resolver.resolve(params={"w": "1280", "h": "720"})

        # Verify success
        assert result.success is True
        assert result.selected_creative is not None

        # Verify selected creative (should be highest bitrate)
        selected_media = result.selected_creative["selected_media_file"]
        assert selected_media["bitrate"] == 2400  # Higher bitrate
        assert selected_media["width"] == 1280

        # Verify impressions collected
        assert len(result.vast_data["impressions"]) > 0  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_selection_strategies_from_config(
        self, config_path: Path, mock_transport: MagicMock, sample_vast_inline: str
    ) -> None:
        """Test different selection strategies from YAML config."""
        mock_transport.send = AsyncMock(return_value=sample_vast_inline.encode("utf-8"))

        resolvers = VastChainConfigLoader.load(config_path, mock_transport)

        # Test high_quality chain (best_quality strategy)
        hq_resolver = resolvers["high_quality"]
        hq_result = await hq_resolver.resolve(params={})
        assert hq_result.success is True
        # Should select highest bitrate (>= 1000kbps)
        assert hq_result.selected_creative["selected_media_file"]["bitrate"] == 2400  # type: ignore[index]

        # Reset mock
        mock_transport.send = AsyncMock(return_value=sample_vast_inline.encode("utf-8"))

        # Test low_bandwidth chain (lowest_bitrate strategy)
        lb_resolver = resolvers["low_bandwidth"]
        lb_result = await lb_resolver.resolve(params={})
        assert lb_result.success is True
        # Should select lowest bitrate
        assert lb_result.selected_creative["selected_media_file"]["bitrate"] == 1200  # type: ignore[index]
