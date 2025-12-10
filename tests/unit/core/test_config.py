"""Tests for UpstreamConfig dataclass."""


from xsp.core.base import BaseUpstream
from xsp.core.config import UpstreamConfig
from xsp.core.transport import Transport, TransportType


# Simple mock transport for testing
class MockTransport(Transport):
    """Mock transport for testing."""

    @property
    def transport_type(self) -> TransportType:
        """Return the transport type."""
        return TransportType.MEMORY

    async def send(
        self,
        endpoint: str,
        payload: bytes | None = None,
        metadata: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> bytes:
        """Mock send method."""
        return b"test response"

    async def close(self) -> None:
        """Mock close method."""
        pass


def test_upstream_config_creation() -> None:
    """UpstreamConfig should store configuration."""
    config = UpstreamConfig(
        endpoint="https://example.com/api",
        params={"key": "value"},
        headers={"Authorization": "Bearer token"},
        encoding_config={"url": False},
        timeout=60.0,
        max_retries=5,
    )

    assert config.endpoint == "https://example.com/api"
    assert config.params == {"key": "value"}
    assert config.headers == {"Authorization": "Bearer token"}
    assert config.encoding_config == {"url": False}
    assert config.timeout == 60.0
    assert config.max_retries == 5


def test_upstream_config_defaults() -> None:
    """UpstreamConfig should have sensible defaults."""
    config = UpstreamConfig(endpoint="https://example.com")

    assert config.params == {}
    assert config.headers == {}
    assert config.encoding_config == {}
    assert config.timeout == 30.0
    assert config.max_retries == 3


def test_upstream_config_replace() -> None:
    """UpstreamConfig.replace() should create new config."""
    config = UpstreamConfig(endpoint="https://dev.example.com", timeout=10.0)

    prod_config = config.replace(
        endpoint="https://prod.example.com", timeout=60.0
    )

    # Original unchanged
    assert config.endpoint == "https://dev.example.com"
    assert config.timeout == 10.0

    # New config updated
    assert prod_config.endpoint == "https://prod.example.com"
    assert prod_config.timeout == 60.0


def test_merge_params() -> None:
    """Config params should be overridden by request params."""
    config = UpstreamConfig(
        endpoint="https://example.com",
        params={"default": "value", "override": "old"},
    )

    merged = config.merge_params({"override": "new", "extra": "param"})

    assert merged == {"default": "value", "override": "new", "extra": "param"}


def test_merge_headers() -> None:
    """Config headers should be overridden by request headers."""
    config = UpstreamConfig(
        endpoint="https://example.com",
        headers={"User-Agent": "default", "Authorization": "old"},
    )

    merged = config.merge_headers({"Authorization": "new", "X-Custom": "header"})

    assert merged == {
        "User-Agent": "default",
        "Authorization": "new",
        "X-Custom": "header",
    }


def test_merge_params_empty_request() -> None:
    """Merge with empty request params should return config params."""
    config = UpstreamConfig(
        endpoint="https://example.com", params={"default": "value"}
    )

    merged = config.merge_params({})

    assert merged == {"default": "value"}


def test_merge_headers_empty_request() -> None:
    """Merge with empty request headers should return config headers."""
    config = UpstreamConfig(
        endpoint="https://example.com", headers={"User-Agent": "default"}
    )

    merged = config.merge_headers({})

    assert merged == {"User-Agent": "default"}


def test_upstream_config_immutability_pattern() -> None:
    """Replace should create new instance without modifying original."""
    original = UpstreamConfig(
        endpoint="https://example.com",
        params={"key": "value"},
        headers={"User-Agent": "test"},
        timeout=30.0,
    )

    # Create modified config
    modified = original.replace(timeout=60.0)

    # Original should be unchanged
    assert original.timeout == 30.0
    assert original.endpoint == "https://example.com"

    # Modified should have new values
    assert modified.timeout == 60.0
    assert modified.endpoint == "https://example.com"

    # They should be different objects
    assert original is not modified


def test_base_upstream_with_config() -> None:
    """BaseUpstream should accept UpstreamConfig object."""
    config = UpstreamConfig(
        endpoint="https://example.com/api",
        params={"key": "value"},
        headers={"Authorization": "Bearer token"},
        timeout=60.0,
    )

    upstream = BaseUpstream(
        transport=MockTransport(),
        decoder=lambda b: b.decode("utf-8"),
        config=config,
    )

    assert upstream.endpoint == "https://example.com/api"
    assert upstream.default_params == {"key": "value"}
    assert upstream.default_headers == {"Authorization": "Bearer token"}
    assert upstream.default_timeout == 60.0
    assert upstream.config.endpoint == "https://example.com/api"


def test_base_upstream_backward_compatibility() -> None:
    """BaseUpstream should still work with individual parameters."""
    upstream = BaseUpstream(
        transport=MockTransport(),
        decoder=lambda b: b.decode("utf-8"),
        endpoint="https://example.com/api",
        default_params={"key": "value"},
        default_headers={"Authorization": "Bearer token"},
        default_timeout=60.0,
    )

    assert upstream.endpoint == "https://example.com/api"
    assert upstream.default_params == {"key": "value"}
    assert upstream.default_headers == {"Authorization": "Bearer token"}
    assert upstream.default_timeout == 60.0
    # Should create config internally
    assert upstream.config.endpoint == "https://example.com/api"


def test_base_upstream_config_priority() -> None:
    """When both config and individual params provided, config should take precedence."""
    config = UpstreamConfig(
        endpoint="https://config.example.com",
        params={"from": "config"},
        timeout=120.0,
    )

    upstream = BaseUpstream(
        transport=MockTransport(),
        decoder=lambda b: b.decode("utf-8"),
        config=config,
        endpoint="https://ignored.example.com",  # Should be ignored
        default_params={"from": "params"},  # Should be ignored
    )

    # Config values should win
    assert upstream.endpoint == "https://config.example.com"
    assert upstream.default_params == {"from": "config"}
    assert upstream.default_timeout == 120.0

