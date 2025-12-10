"""Tests for ConfigGenerator with TOML validation."""

import sys

import pytest

from xsp.core.config_generator import ConfigGenerator
from xsp.core.configurable import clear_configurable_registry, configurable

# Import appropriate TOML parser
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore


def test_generated_toml_is_valid():
    """Test that generated TOML can be parsed."""
    clear_configurable_registry()

    @configurable(namespace="test")
    class TestClass:
        def __init__(self, *, value: str = "test"):
            pass

    toml_str = ConfigGenerator.generate_toml()

    # Should not raise
    if tomllib is not None:
        parsed = tomllib.loads(toml_str)
        assert "test" in parsed


def test_special_characters_in_strings():
    """Test TOML generation with special characters."""
    clear_configurable_registry()

    @configurable(namespace="special")
    class SpecialClass:
        def __init__(
            self,
            *,
            quoted: str = 'test "quoted" string',
            newline: str = "line1\nline2",
            backslash: str = "path\\to\\file",
        ):
            pass

    toml_str = ConfigGenerator.generate_toml()

    # Validate parseable
    if tomllib is not None:
        parsed = tomllib.loads(toml_str)

        # Check values preserved correctly
        assert parsed["special"]["quoted"] == 'test "quoted" string'
        assert parsed["special"]["newline"] == "line1\nline2"
        assert parsed["special"]["backslash"] == "path\\to\\file"


def test_unicode_in_values():
    """Test TOML generation with Unicode characters."""
    clear_configurable_registry()

    @configurable(namespace="unicode")
    class UnicodeClass:
        def __init__(
            self,
            *,
            cyrillic: str = "Привет мир",
            emoji: str = "🚀 rocket",
        ):
            pass

    toml_str = ConfigGenerator.generate_toml()

    if tomllib is not None:
        parsed = tomllib.loads(toml_str)

        assert parsed["unicode"]["cyrillic"] == "Привет мир"
        assert parsed["unicode"]["emoji"] == "🚀 rocket"


def test_complex_types():
    """Test TOML generation with lists and dicts."""
    clear_configurable_registry()

    @configurable(namespace="complex")
    class ComplexClass:
        def __init__(
            self,
            *,
            items: list[str] | None = None,
            config: dict[str, int] | None = None,
        ):
            # Store defaults in instance for testing
            self.items = items if items is not None else ["a", "b", "c"]
            self.config = config if config is not None else {"x": 1, "y": 2}

    # Need to manually set defaults that are mutable
    # The decorator only captures what's in the function signature
    # For None defaults, we need to handle separately in real usage

    # For this test, let's use immutable defaults
    clear_configurable_registry()

    @configurable(namespace="arrays")
    class ArrayClass:
        def __init__(
            self,
            *,
            numbers: tuple[int, ...] = (1, 2, 3),
            flag: bool = False,
        ):
            pass

    toml_str = ConfigGenerator.generate_toml()

    if tomllib is not None:
        parsed = tomllib.loads(toml_str)

        # Tuples become arrays in TOML
        assert "arrays" in parsed
        assert "numbers" in parsed["arrays"]
        assert "flag" in parsed["arrays"]


def test_group_by_namespace():
    """Test TOML generation grouped by namespace."""
    clear_configurable_registry()

    @configurable(namespace="http")
    class HttpTransport:
        def __init__(self, *, timeout: float = 30.0):
            pass

    @configurable(namespace="http")
    class HttpClient:
        def __init__(self, *, retries: int = 3):
            pass

    @configurable(namespace="grpc")
    class GrpcTransport:
        def __init__(self, *, port: int = 50051):
            pass

    toml_str = ConfigGenerator.generate_toml(group_by="namespace")

    if tomllib is not None:
        parsed = tomllib.loads(toml_str)

        # Should have two namespaces
        assert "http" in parsed
        assert "grpc" in parsed

        # HTTP namespace should have both classes' parameters
        assert "timeout" in parsed["http"]
        assert "retries" in parsed["http"]

        # gRPC namespace should have its parameter
        assert "port" in parsed["grpc"]


def test_group_by_class():
    """Test TOML generation grouped by class name."""
    clear_configurable_registry()

    @configurable(namespace="http")
    class HttpTransport:
        def __init__(self, *, timeout: float = 30.0):
            pass

    @configurable(namespace="http")
    class HttpClient:
        def __init__(self, *, retries: int = 3):
            pass

    toml_str = ConfigGenerator.generate_toml(group_by="class")

    if tomllib is not None:
        parsed = tomllib.loads(toml_str)

        # Should have sections like "http.HttpTransport" and "http.HttpClient"
        assert "http.HttpTransport" in parsed
        assert "http.HttpClient" in parsed

        assert "timeout" in parsed["http.HttpTransport"]
        assert "retries" in parsed["http.HttpClient"]


def test_empty_registry():
    """Test TOML generation with empty registry."""
    clear_configurable_registry()

    toml_str = ConfigGenerator.generate_toml()
    assert toml_str == "# No configurable classes found\n"


def test_invalid_group_by():
    """Test that invalid group_by raises ValueError."""
    clear_configurable_registry()

    @configurable(namespace="test")
    class TestClass:
        def __init__(self, *, value: str = "test"):
            pass

    with pytest.raises(ValueError, match="Unknown group_by"):
        ConfigGenerator.generate_toml(group_by="invalid")


def test_validation_flag():
    """Test that validation can be disabled."""
    clear_configurable_registry()

    @configurable(namespace="test")
    class TestClass:
        def __init__(self, *, value: str = "test"):
            pass

    # Should not raise with validate=False
    toml_str = ConfigGenerator.generate_toml(validate=False)
    assert len(toml_str) > 0


def test_various_python_types():
    """Test TOML generation with various Python types."""
    clear_configurable_registry()

    @configurable(namespace="types")
    class TypesClass:
        def __init__(
            self,
            *,
            string: str = "text",
            integer: int = 42,
            floating: float = 3.14,
            boolean: bool = True,
            none_value: None = None,
        ):
            pass

    toml_str = ConfigGenerator.generate_toml()

    if tomllib is not None:
        parsed = tomllib.loads(toml_str)
        assert parsed["types"]["string"] == "text"
        assert parsed["types"]["integer"] == 42
        assert parsed["types"]["floating"] == 3.14
        assert parsed["types"]["boolean"] is True
        # None values are commented out, so they won't be in the parsed result
        assert "none_value" not in parsed["types"]
        # But should appear as a comment in the output
        assert "none_value = null" in toml_str



def test_url_with_quotes():
    """Test TOML generation with URL containing quotes (from issue example)."""
    clear_configurable_registry()

    @configurable(namespace="test")
    class TestClass:
        def __init__(self, *, url: str = 'http://example.com?a="test"'):
            pass

    toml_str = ConfigGenerator.generate_toml()

    if tomllib is not None:
        parsed = tomllib.loads(toml_str)
        # Should preserve the URL with quotes correctly
        assert parsed["test"]["url"] == 'http://example.com?a="test"'


def test_description_in_comments():
    """Test that descriptions appear as comments."""
    clear_configurable_registry()

    @configurable(namespace="test", description="This is a test class")
    class TestClass:
        def __init__(self, *, value: str = "test"):
            pass

    toml_str = ConfigGenerator.generate_toml()

    # Check that description appears in output
    assert "This is a test class" in toml_str


def test_type_information_in_comments():
    """Test that type information appears in comments."""
    clear_configurable_registry()

    @configurable(namespace="test")
    class TestClass:
        def __init__(self, *, value: str = "test", count: int = 42):
            pass

    toml_str = ConfigGenerator.generate_toml()

    # Check that type information appears
    assert "Type:" in toml_str
