"""Unit tests for UpstreamConfig."""

from __future__ import annotations

from xsp.core.config import UpstreamConfig


class TestUpstreamConfig:
    """Test suite for UpstreamConfig dataclass."""

    def test_default_values(self) -> None:
        """Test that UpstreamConfig has correct default values."""
        config = UpstreamConfig()

        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.encoding == "utf-8"
        assert config.encoding_config is None
        assert config.default_headers == {}
        assert config.default_params == {}

    def test_custom_timeout(self) -> None:
        """Test creating UpstreamConfig with custom timeout."""
        config = UpstreamConfig(timeout=5.0)

        assert config.timeout == 5.0
        assert config.max_retries == 3  # Still default

    def test_openrtb_low_latency_config(self) -> None:
        """Test OpenRTB configuration with low timeout (per OpenRTB 2.6 §4.1)."""
        config = UpstreamConfig(
            timeout=0.3,  # 300ms typical for OpenRTB
            max_retries=1,  # Low retries for RTB
        )

        assert config.timeout == 0.3
        assert config.max_retries == 1

    def test_vast_config_with_headers(self) -> None:
        """Test VAST configuration with custom headers."""
        config = UpstreamConfig(
            timeout=30.0,
            default_headers={"X-API-Key": "secret", "User-Agent": "xsp-lib/1.0"},
        )

        assert config.timeout == 30.0
        assert config.default_headers == {
            "X-API-Key": "secret",
            "User-Agent": "xsp-lib/1.0",
        }

    def test_encoding_config_cyrillic(self) -> None:
        """Test encoding configuration for Cyrillic preservation."""
        config = UpstreamConfig(
            encoding="utf-8",
            encoding_config={"preserve_cyrillic": True, "strict": False},
        )

        assert config.encoding == "utf-8"
        assert config.encoding_config == {"preserve_cyrillic": True, "strict": False}

    def test_default_params(self) -> None:
        """Test configuration with default query parameters."""
        config = UpstreamConfig(
            default_params={"app_id": "my_app", "version": "1.0"},
        )

        assert config.default_params == {"app_id": "my_app", "version": "1.0"}

    def test_all_custom_values(self) -> None:
        """Test UpstreamConfig with all custom values."""
        config = UpstreamConfig(
            timeout=15.0,
            max_retries=5,
            encoding="utf-16",
            encoding_config={"custom": "setting"},
            default_headers={"Authorization": "Bearer token"},
            default_params={"key": "value"},
        )

        assert config.timeout == 15.0
        assert config.max_retries == 5
        assert config.encoding == "utf-16"
        assert config.encoding_config == {"custom": "setting"}
        assert config.default_headers == {"Authorization": "Bearer token"}
        assert config.default_params == {"key": "value"}

    def test_immutable_collections_not_shared(self) -> None:
        """Test that default_headers and default_params are not shared across instances."""
        config1 = UpstreamConfig(default_headers={"Key": "Value1"})
        config2 = UpstreamConfig(default_headers={"Key": "Value2"})

        assert config1.default_headers != config2.default_headers
        assert config1.default_headers == {"Key": "Value1"}
        assert config2.default_headers == {"Key": "Value2"}

    def test_none_encoding_config(self) -> None:
        """Test that encoding_config can be None."""
        config = UpstreamConfig(encoding_config=None)

        assert config.encoding_config is None

    def test_empty_default_headers(self) -> None:
        """Test that default_headers defaults to empty dict."""
        config = UpstreamConfig()

        assert config.default_headers == {}
        assert isinstance(config.default_headers, dict)

    def test_empty_default_params(self) -> None:
        """Test that default_params defaults to empty dict."""
        config = UpstreamConfig()

        assert config.default_params == {}
        assert isinstance(config.default_params, dict)

    def test_dataclass_equality(self) -> None:
        """Test that UpstreamConfig instances are equal when values match."""
        config1 = UpstreamConfig(
            timeout=30.0,
            max_retries=3,
            encoding="utf-8",
        )
        config2 = UpstreamConfig(
            timeout=30.0,
            max_retries=3,
            encoding="utf-8",
        )

        assert config1 == config2

    def test_dataclass_inequality(self) -> None:
        """Test that UpstreamConfig instances are not equal when values differ."""
        config1 = UpstreamConfig(timeout=30.0)
        config2 = UpstreamConfig(timeout=15.0)

        assert config1 != config2
