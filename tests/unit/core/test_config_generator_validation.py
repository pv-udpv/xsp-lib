"""Tests for ConfigGenerator TOML validation."""

import tomllib

import pytest

from xsp.core.config_generator import ConfigGenerator
from xsp.core.configurable import configurable


def test_generated_toml_is_valid() -> None:
    """Test that generated TOML can be parsed."""

    @configurable(namespace="test")
    class TestClass:
        def __init__(self, *, value: str = "test") -> None:
            pass

    toml_str = ConfigGenerator.generate_toml()

    # Should not raise
    parsed = tomllib.loads(toml_str)
    assert "test" in parsed


def test_special_characters_in_strings() -> None:
    """Test TOML generation with special characters."""

    @configurable(namespace="special")
    class SpecialClass:
        def __init__(
            self,
            *,
            quoted: str = 'test "quoted" string',
            newline: str = "line1\nline2",
            backslash: str = "path\\to\\file",
            tab: str = "col1\tcol2",
        ) -> None:
            pass

    toml_str = ConfigGenerator.generate_toml()

    # Validate parseable
    parsed = tomllib.loads(toml_str)

    # Check values preserved correctly
    assert parsed["special"]["quoted"] == 'test "quoted" string'
    assert parsed["special"]["newline"] == "line1\nline2"
    assert parsed["special"]["backslash"] == "path\\to\\file"
    assert parsed["special"]["tab"] == "col1\tcol2"


def test_unicode_in_values() -> None:
    """Test TOML generation with Unicode characters."""

    @configurable(namespace="unicode")
    class UnicodeClass:
        def __init__(
            self,
            *,
            cyrillic: str = "Привет мир",
            emoji: str = "🚀 rocket",
            chinese: str = "你好世界",
        ) -> None:
            pass

    toml_str = ConfigGenerator.generate_toml()
    parsed = tomllib.loads(toml_str)

    assert parsed["unicode"]["cyrillic"] == "Привет мир"
    assert parsed["unicode"]["emoji"] == "🚀 rocket"
    assert parsed["unicode"]["chinese"] == "你好世界"


def test_complex_types() -> None:
    """Test TOML generation with lists and dicts."""

    @configurable(namespace="complex")
    class ComplexClass:
        def __init__(
            self,
            *,
            items: list[str] | None = None,
            config: dict[str, int] | None = None,
        ) -> None:
            # Default values in __init__ body
            self.items = items or ["a", "b", "c"]
            self.config = config or {"x": 1, "y": 2}

    # Note: Since defaults are set in __init__ body, not in signature,
    # the configurable decorator will see None as defaults
    toml_str = ConfigGenerator.generate_toml()
    parsed = tomllib.loads(toml_str)

    # Both should be empty strings (None converted)
    assert parsed["complex"]["items"] == ""
    assert parsed["complex"]["config"] == ""


def test_complex_types_with_signature_defaults() -> None:
    """Test TOML generation with lists and dicts in signature defaults.
    
    Note: Using mutable defaults in production code is discouraged.
    This test verifies that tomlkit can handle such cases if they exist.
    """

    @configurable(namespace="complex2")
    class ComplexClass2:
        def __init__(
            self,
            *,
            items: list[str] | None = None,
            numbers: list[int] | None = None,
            config: dict[str, int] | None = None,
        ) -> None:
            # Best practice: create mutable defaults in method body
            self.items = items if items is not None else ["a", "b", "c"]
            self.numbers = numbers if numbers is not None else [1, 2, 3]
            self.config = config if config is not None else {"x": 1, "y": 2}

    # Since defaults are None in signature, they'll be converted to empty strings
    toml_str = ConfigGenerator.generate_toml()
    parsed = tomllib.loads(toml_str)

    # All should be empty strings (None converted)
    assert parsed["complex2"]["items"] == ""
    assert parsed["complex2"]["numbers"] == ""
    assert parsed["complex2"]["config"] == ""


def test_mutable_defaults_in_signature() -> None:
    """Test TOML generation when mutable defaults are (incorrectly) used in signature.
    
    This test documents behavior when encountering anti-pattern code.
    """

    @configurable(namespace="mutable")
    class MutableDefaultsClass:
        def __init__(
            self,
            *,
            items: list[str] = ["a", "b", "c"],  # noqa: B006
            numbers: list[int] = [1, 2, 3],  # noqa: B006
            config: dict[str, int] = {"x": 1, "y": 2},  # noqa: B006
        ) -> None:
            pass

    toml_str = ConfigGenerator.generate_toml()
    parsed = tomllib.loads(toml_str)

    # Verify structure preserved
    assert isinstance(parsed["mutable"]["items"], list)
    assert parsed["mutable"]["items"] == ["a", "b", "c"]
    assert isinstance(parsed["mutable"]["numbers"], list)
    assert parsed["mutable"]["numbers"] == [1, 2, 3]
    assert isinstance(parsed["mutable"]["config"], dict)
    assert parsed["mutable"]["config"] == {"x": 1, "y": 2}


def test_edge_case_url_with_quotes() -> None:
    """Test URL with quotes as mentioned in issue."""

    @configurable(namespace="url_test")
    class UrlClass:
        def __init__(self, *, url: str = 'http://example.com?a="test"') -> None:
            pass

    toml_str = ConfigGenerator.generate_toml()
    parsed = tomllib.loads(toml_str)

    # Check that value is preserved correctly
    assert parsed["url_test"]["url"] == 'http://example.com?a="test"'


def test_validation_can_be_disabled() -> None:
    """Test that validation can be disabled."""

    @configurable(namespace="no_validate")
    class NoValidateClass:
        def __init__(self, *, value: str = "test") -> None:
            pass

    # Should not raise even if we don't validate
    toml_str = ConfigGenerator.generate_toml(validate=False)

    # But it should still be valid TOML
    parsed = tomllib.loads(toml_str)
    assert "no_validate" in parsed


def test_validation_raises_on_invalid_toml() -> None:
    """Test that validation raises ValueError on invalid TOML."""
    # This is hard to test directly since tomlkit should always generate valid TOML
    # But we can test the validation method directly
    invalid_toml = 'invalid = "unclosed string'

    with pytest.raises(ValueError, match="Generated TOML is invalid"):
        ConfigGenerator._validate_toml(invalid_toml)


def test_empty_string_default() -> None:
    """Test TOML generation with empty string default."""

    @configurable(namespace="empty")
    class EmptyClass:
        def __init__(self, *, value: str = "") -> None:
            pass

    toml_str = ConfigGenerator.generate_toml()
    parsed = tomllib.loads(toml_str)

    assert parsed["empty"]["value"] == ""


def test_multiline_string() -> None:
    """Test TOML generation with multiline strings."""

    @configurable(namespace="multiline")
    class MultilineClass:
        def __init__(self, *, description: str = "Line 1\nLine 2\nLine 3") -> None:
            pass

    toml_str = ConfigGenerator.generate_toml()
    parsed = tomllib.loads(toml_str)

    assert parsed["multiline"]["description"] == "Line 1\nLine 2\nLine 3"


def test_boolean_values() -> None:
    """Test TOML generation with boolean values."""

    @configurable(namespace="bool_test")
    class BoolClass:
        def __init__(self, *, enabled: bool = True, disabled: bool = False) -> None:
            pass

    toml_str = ConfigGenerator.generate_toml()
    parsed = tomllib.loads(toml_str)

    assert parsed["bool_test"]["enabled"] is True
    assert parsed["bool_test"]["disabled"] is False


def test_numeric_values() -> None:
    """Test TOML generation with numeric values."""

    @configurable(namespace="numeric")
    class NumericClass:
        def __init__(
            self,
            *,
            int_val: int = 42,
            float_val: float = 3.14,
            negative: int = -100,
        ) -> None:
            pass

    toml_str = ConfigGenerator.generate_toml()
    parsed = tomllib.loads(toml_str)

    assert parsed["numeric"]["int_val"] == 42
    assert parsed["numeric"]["float_val"] == 3.14
    assert parsed["numeric"]["negative"] == -100


def test_special_toml_reserved_characters() -> None:
    """Test TOML generation with TOML reserved characters."""

    @configurable(namespace="reserved")
    class ReservedClass:
        def __init__(
            self,
            *,
            brackets: str = "[test]",
            hash: str = "# comment",
            equals: str = "key=value",
        ) -> None:
            pass

    toml_str = ConfigGenerator.generate_toml()
    parsed = tomllib.loads(toml_str)

    assert parsed["reserved"]["brackets"] == "[test]"
    assert parsed["reserved"]["hash"] == "# comment"
    assert parsed["reserved"]["equals"] == "key=value"
