"""Tests for UpstreamConfig dataclass."""

from xsp.core.config import UpstreamConfig


def test_upstream_config_creation_with_all_fields() -> None:
    """Test UpstreamConfig creation with all fields explicitly set."""
    config = UpstreamConfig(
        endpoint="https://ads.example.com/vast",
        params={"app": "myapp", "version": "1.0"},
        headers={"User-Agent": "MyApp/1.0", "Accept": "application/xml"},
        encoding_config={"preserve_cyrillic": True},
        timeout=30.0,
        max_retries=3,
    )

    assert config.endpoint == "https://ads.example.com/vast"
    assert config.params == {"app": "myapp", "version": "1.0"}
    assert config.headers == {"User-Agent": "MyApp/1.0", "Accept": "application/xml"}
    assert config.encoding_config == {"preserve_cyrillic": True}
    assert config.timeout == 30.0
    assert config.max_retries == 3


def test_upstream_config_default_values() -> None:
    """Test UpstreamConfig default values for optional fields."""
    config = UpstreamConfig(endpoint="https://example.com")

    assert config.endpoint == "https://example.com"
    assert config.params == {}
    assert config.headers == {}
    assert config.encoding_config == {}
    assert config.timeout == 30.0
    assert config.max_retries == 3


def test_upstream_config_minimal_creation() -> None:
    """Test UpstreamConfig creation with only required field."""
    config = UpstreamConfig(endpoint="https://minimal.example.com")

    assert config.endpoint == "https://minimal.example.com"
    assert isinstance(config.params, dict)
    assert isinstance(config.headers, dict)
    assert isinstance(config.encoding_config, dict)
    assert isinstance(config.timeout, float)
    assert isinstance(config.max_retries, int)


def test_upstream_config_replace_endpoint() -> None:
    """Test replace() method creates new config with updated endpoint."""
    original = UpstreamConfig(
        endpoint="https://example.com",
        timeout=30.0,
    )

    new_config = original.replace(endpoint="https://dev.example.com")

    # New config has updated endpoint
    assert new_config.endpoint == "https://dev.example.com"
    # Other fields remain unchanged
    assert new_config.timeout == 30.0

    # Original config is unchanged
    assert original.endpoint == "https://example.com"
    assert original.timeout == 30.0


def test_upstream_config_replace_timeout() -> None:
    """Test replace() method creates new config with updated timeout."""
    original = UpstreamConfig(
        endpoint="https://example.com",
        timeout=30.0,
        max_retries=3,
    )

    new_config = original.replace(timeout=10.0)

    # New config has updated timeout
    assert new_config.timeout == 10.0
    # Other fields remain unchanged
    assert new_config.endpoint == "https://example.com"
    assert new_config.max_retries == 3

    # Original config is unchanged
    assert original.timeout == 30.0


def test_upstream_config_replace_multiple_fields() -> None:
    """Test replace() method with multiple field updates."""
    original = UpstreamConfig(
        endpoint="https://example.com",
        timeout=30.0,
        max_retries=3,
    )

    new_config = original.replace(
        endpoint="https://prod.example.com",
        timeout=5.0,
        max_retries=5,
    )

    # New config has all updated fields
    assert new_config.endpoint == "https://prod.example.com"
    assert new_config.timeout == 5.0
    assert new_config.max_retries == 5

    # Original config is unchanged
    assert original.endpoint == "https://example.com"
    assert original.timeout == 30.0
    assert original.max_retries == 3


def test_upstream_config_replace_creates_new_instance() -> None:
    """Test that replace() creates a new instance, not modifying the original."""
    original = UpstreamConfig(endpoint="https://example.com")
    new_config = original.replace(endpoint="https://new.example.com")

    # Should be different instances
    assert original is not new_config
    assert original.endpoint != new_config.endpoint


def test_upstream_config_replace_with_dict_fields() -> None:
    """Test replace() method with dict field updates."""
    original = UpstreamConfig(
        endpoint="https://example.com",
        params={"app": "myapp"},
        headers={"User-Agent": "MyApp/1.0"},
    )

    new_config = original.replace(
        params={"app": "otherapp", "version": "2.0"},
        headers={"User-Agent": "MyApp/2.0", "Accept": "application/json"},
    )

    # New config has updated dicts
    assert new_config.params == {"app": "otherapp", "version": "2.0"}
    assert new_config.headers == {"User-Agent": "MyApp/2.0", "Accept": "application/json"}

    # Original config is unchanged
    assert original.params == {"app": "myapp"}
    assert original.headers == {"User-Agent": "MyApp/1.0"}


def test_upstream_config_merge_params_with_empty_defaults() -> None:
    """Test merge_params() with empty default params."""
    config = UpstreamConfig(endpoint="https://example.com")
    request_params = {"width": "640", "height": "480"}

    merged = config.merge_params(request_params)

    assert merged == {"width": "640", "height": "480"}
    # Original config params unchanged
    assert config.params == {}


def test_upstream_config_merge_params_with_defaults() -> None:
    """Test merge_params() combines default and request params."""
    config = UpstreamConfig(
        endpoint="https://example.com",
        params={"app": "myapp", "version": "1.0"},
    )
    request_params = {"width": "640", "height": "480"}

    merged = config.merge_params(request_params)

    # Should contain both default and request params
    assert merged == {
        "app": "myapp",
        "version": "1.0",
        "width": "640",
        "height": "480",
    }
    # Original config params unchanged
    assert config.params == {"app": "myapp", "version": "1.0"}


def test_upstream_config_merge_params_override() -> None:
    """Test merge_params() with request params overriding defaults."""
    config = UpstreamConfig(
        endpoint="https://example.com",
        params={"app": "myapp", "version": "1.0", "debug": "false"},
    )
    request_params = {"debug": "true", "width": "640"}

    merged = config.merge_params(request_params)

    # Request params should override defaults
    assert merged == {
        "app": "myapp",
        "version": "1.0",
        "debug": "true",  # Overridden
        "width": "640",
    }
    # Original config params unchanged
    assert config.params["debug"] == "false"


def test_upstream_config_merge_params_with_none() -> None:
    """Test merge_params() with None returns copy of default params."""
    config = UpstreamConfig(
        endpoint="https://example.com",
        params={"app": "myapp", "version": "1.0"},
    )

    merged = config.merge_params(None)

    # Should return copy of default params
    assert merged == {"app": "myapp", "version": "1.0"}
    # Should be a copy, not the same object
    assert merged is not config.params


def test_upstream_config_merge_params_does_not_modify_original() -> None:
    """Test that merge_params() does not modify the original config.params."""
    config = UpstreamConfig(
        endpoint="https://example.com",
        params={"app": "myapp"},
    )

    merged = config.merge_params({"width": "640"})
    merged["new_key"] = "new_value"  # Modify merged dict

    # Original config params should be unchanged
    assert "width" not in config.params
    assert "new_key" not in config.params
    assert config.params == {"app": "myapp"}


def test_upstream_config_merge_headers_with_empty_defaults() -> None:
    """Test merge_headers() with empty default headers."""
    config = UpstreamConfig(endpoint="https://example.com")
    request_headers = {"Authorization": "Bearer token123"}

    merged = config.merge_headers(request_headers)

    assert merged == {"Authorization": "Bearer token123"}
    # Original config headers unchanged
    assert config.headers == {}


def test_upstream_config_merge_headers_with_defaults() -> None:
    """Test merge_headers() combines default and request headers."""
    config = UpstreamConfig(
        endpoint="https://example.com",
        headers={"User-Agent": "MyApp/1.0", "Accept": "application/xml"},
    )
    request_headers = {"Authorization": "Bearer token123"}

    merged = config.merge_headers(request_headers)

    # Should contain both default and request headers
    assert merged == {
        "User-Agent": "MyApp/1.0",
        "Accept": "application/xml",
        "Authorization": "Bearer token123",
    }
    # Original config headers unchanged
    assert config.headers == {"User-Agent": "MyApp/1.0", "Accept": "application/xml"}


def test_upstream_config_merge_headers_override() -> None:
    """Test merge_headers() with request headers overriding defaults."""
    config = UpstreamConfig(
        endpoint="https://example.com",
        headers={"User-Agent": "MyApp/1.0", "Accept": "application/xml"},
    )
    request_headers = {"User-Agent": "MyApp/2.0", "Content-Type": "application/json"}

    merged = config.merge_headers(request_headers)

    # Request headers should override defaults
    assert merged == {
        "User-Agent": "MyApp/2.0",  # Overridden
        "Accept": "application/xml",
        "Content-Type": "application/json",
    }
    # Original config headers unchanged
    assert config.headers["User-Agent"] == "MyApp/1.0"


def test_upstream_config_merge_headers_with_none() -> None:
    """Test merge_headers() with None returns copy of default headers."""
    config = UpstreamConfig(
        endpoint="https://example.com",
        headers={"User-Agent": "MyApp/1.0"},
    )

    merged = config.merge_headers(None)

    # Should return copy of default headers
    assert merged == {"User-Agent": "MyApp/1.0"}
    # Should be a copy, not the same object
    assert merged is not config.headers


def test_upstream_config_merge_headers_does_not_modify_original() -> None:
    """Test that merge_headers() does not modify the original config.headers."""
    config = UpstreamConfig(
        endpoint="https://example.com",
        headers={"User-Agent": "MyApp/1.0"},
    )

    merged = config.merge_headers({"Accept": "application/json"})
    merged["new_header"] = "new_value"  # Modify merged dict

    # Original config headers should be unchanged
    assert "Accept" not in config.headers
    assert "new_header" not in config.headers
    assert config.headers == {"User-Agent": "MyApp/1.0"}


def test_upstream_config_vast_use_case() -> None:
    """Test UpstreamConfig for VAST protocol use case."""
    config = UpstreamConfig(
        endpoint="https://ads.example.com/vast",
        params={"app": "myapp", "version": "1.0"},
        headers={"User-Agent": "MyApp/1.0", "Accept": "application/xml"},
        encoding_config={"preserve_cyrillic": True},
        timeout=30.0,
        max_retries=3,
    )

    # Merge request-specific params
    request_params = config.merge_params({"w": "640", "h": "480"})
    assert request_params == {
        "app": "myapp",
        "version": "1.0",
        "w": "640",
        "h": "480",
    }

    # Merge request-specific headers
    request_headers = config.merge_headers({"X-Request-ID": "req-123"})
    assert request_headers == {
        "User-Agent": "MyApp/1.0",
        "Accept": "application/xml",
        "X-Request-ID": "req-123",
    }


def test_upstream_config_openrtb_use_case() -> None:
    """Test UpstreamConfig for OpenRTB protocol use case with short timeout."""
    config = UpstreamConfig(
        endpoint="https://bidder.example.com/openrtb",
        params={"publisher": "pub123"},
        headers={"Content-Type": "application/json"},
        timeout=0.3,  # 300ms per OpenRTB 2.6 §4.1
        max_retries=1,
    )

    assert config.endpoint == "https://bidder.example.com/openrtb"
    assert config.timeout == 0.3
    assert config.max_retries == 1
    assert config.headers["Content-Type"] == "application/json"


def test_upstream_config_environment_specific_configs() -> None:
    """Test creating environment-specific configs using replace()."""
    base_config = UpstreamConfig(
        endpoint="https://prod.example.com",
        timeout=30.0,
        max_retries=3,
    )

    # Development config with longer timeout
    dev_config = base_config.replace(
        endpoint="https://dev.example.com",
        timeout=60.0,
    )

    # Staging config
    staging_config = base_config.replace(
        endpoint="https://staging.example.com",
    )

    assert base_config.endpoint == "https://prod.example.com"
    assert dev_config.endpoint == "https://dev.example.com"
    assert staging_config.endpoint == "https://staging.example.com"

    assert dev_config.timeout == 60.0
    assert staging_config.timeout == 30.0  # Inherited from base


def test_upstream_config_cyrillic_encoding_preservation() -> None:
    """Test encoding_config for Cyrillic character preservation."""
    config = UpstreamConfig(
        endpoint="https://example.com",
        encoding_config={"preserve_cyrillic": True, "preserve_chinese": False},
    )

    assert config.encoding_config["preserve_cyrillic"] is True
    assert config.encoding_config["preserve_chinese"] is False


def test_upstream_config_equality() -> None:
    """Test UpstreamConfig equality comparison."""
    config1 = UpstreamConfig(
        endpoint="https://example.com",
        timeout=30.0,
    )

    config2 = UpstreamConfig(
        endpoint="https://example.com",
        timeout=30.0,
    )

    # Same values should be equal
    assert config1 == config2

    # Different values should not be equal
    config3 = UpstreamConfig(
        endpoint="https://different.example.com",
        timeout=30.0,
    )
    assert config1 != config3


def test_upstream_config_repr() -> None:
    """Test UpstreamConfig string representation."""
    config = UpstreamConfig(
        endpoint="https://example.com",
        timeout=30.0,
        max_retries=3,
    )

    repr_str = repr(config)
    assert "UpstreamConfig" in repr_str
    assert "https://example.com" in repr_str
    assert "30.0" in repr_str
    assert "3" in repr_str


def test_upstream_config_default_factory_independence() -> None:
    """Test that default dict factories create independent instances."""
    config1 = UpstreamConfig(endpoint="https://example1.com")
    config2 = UpstreamConfig(endpoint="https://example2.com")

    # Modify config1's params
    config1.params["key1"] = "value1"

    # config2's params should not be affected
    assert "key1" not in config2.params
    assert config1.params != config2.params


def test_upstream_config_with_complex_params() -> None:
    """Test UpstreamConfig with complex nested parameter values."""
    config = UpstreamConfig(
        endpoint="https://example.com",
        params={
            "simple": "value",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "list": [1, 2, 3],
            "nested": {"key": "value"},
        },
    )

    assert config.params["simple"] == "value"
    assert config.params["number"] == 42
    assert config.params["float"] == 3.14
    assert config.params["boolean"] is True
    assert config.params["list"] == [1, 2, 3]
    assert config.params["nested"] == {"key": "value"}


def test_upstream_config_replace_preserves_unspecified_dicts() -> None:
    """Test that replace() preserves dict fields when not specified."""
    original = UpstreamConfig(
        endpoint="https://example.com",
        params={"app": "myapp"},
        headers={"User-Agent": "MyApp/1.0"},
        encoding_config={"preserve_cyrillic": True},
    )

    new_config = original.replace(timeout=10.0)

    # Dict fields should be preserved
    assert new_config.params == {"app": "myapp"}
    assert new_config.headers == {"User-Agent": "MyApp/1.0"}
    assert new_config.encoding_config == {"preserve_cyrillic": True}

    # But they should be copies, not the same objects
    assert new_config.params is not original.params
    assert new_config.headers is not original.headers
    assert new_config.encoding_config is not original.encoding_config
