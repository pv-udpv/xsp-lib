"""Tests for configurable decorator."""

import pytest

from xsp.core.config_generator import ConfigGenerator
from xsp.core.configurable import configurable, get_configurable_registry


def test_configurable_decorator() -> None:
    """Test @configurable decorator registration."""

    @configurable(namespace="test", description="Test class")
    class TestClass:
        def __init__(self, required: str, *, optional: int = 42) -> None:
            pass

    registry = get_configurable_registry()

    # Check registration
    assert "test.TestClass" in registry

    metadata = registry["test.TestClass"]
    assert metadata.namespace == "test"
    assert metadata.description == "Test class"
    assert "optional" in metadata.parameters
    assert metadata.parameters["optional"].default == 42


def test_config_generator_toml() -> None:
    """Test TOML configuration generation."""

    @configurable(namespace="demo")
    class DemoUpstream:
        def __init__(self, *, timeout: float = 30.0, retries: int = 3) -> None:
            pass

    toml = ConfigGenerator.generate_toml()

    assert "[demo]" in toml
    assert "timeout = 30.0" in toml
    assert "retries = 3" in toml


def test_kwonly_params_only() -> None:
    """Test that only keyword-only params are extracted."""

    @configurable(namespace="test")
    class TestClass:
        def __init__(self, required: str, *, optional: int = 10) -> None:
            pass

    registry = get_configurable_registry()
    params = registry["test.TestClass"].parameters

    # Only optional should be in params (required is positional)
    assert "required" not in params
    assert "optional" in params


def test_configurable_default_namespace() -> None:
    """Test that namespace defaults to module name."""

    @configurable()
    class MyClass:
        def __init__(self, *, value: str = "default") -> None:
            pass

    registry = get_configurable_registry()
    # Namespace should be derived from module name
    found = False
    for key, metadata in registry.items():
        if metadata.cls.__name__ == "MyClass":
            found = True
            assert metadata.namespace == "test_configurable"
    assert found


def test_configurable_with_enum_default() -> None:
    """Test configurable with enum default value."""
    from enum import Enum

    class MyEnum(Enum):
        VALUE_A = "a"
        VALUE_B = "b"

    @configurable(namespace="enum_test")
    class EnumClass:
        def __init__(self, *, mode: MyEnum = MyEnum.VALUE_A) -> None:
            pass

    toml = ConfigGenerator.generate_toml()
    assert '"a"' in toml or "a" in toml


def test_configurable_with_docstring_descriptions() -> None:
    """Test that parameter descriptions are extracted from docstrings."""

    @configurable(namespace="doc_test")
    class DocClass:
        def __init__(self, *, timeout: float = 30.0) -> None:
            """
            Initialize class.

            Args:
                timeout: Request timeout in seconds
            """
            pass

    registry = get_configurable_registry()
    params = registry["doc_test.DocClass"].parameters

    assert "timeout" in params
    assert params["timeout"].description == "Request timeout in seconds"


def test_config_generator_grouping() -> None:
    """Test different grouping strategies."""

    @configurable(namespace="group_a")
    class ClassA:
        def __init__(self, *, value: int = 1) -> None:
            pass

    @configurable(namespace="group_b")
    class ClassB:
        def __init__(self, *, value: int = 2) -> None:
            pass

    # Test namespace grouping
    toml_ns = ConfigGenerator.generate_toml(group_by="namespace")
    assert "[group_a]" in toml_ns
    assert "[group_b]" in toml_ns

    # Test class grouping
    toml_class = ConfigGenerator.generate_toml(group_by="class")
    assert "[classa]" in toml_class.lower()
    assert "[classb]" in toml_class.lower()


def test_config_generator_invalid_group_by() -> None:
    """Test that invalid group_by raises ValueError."""
    with pytest.raises(ValueError, match="Unknown group_by"):
        ConfigGenerator.generate_toml(group_by="invalid")


def test_config_generator_yaml_not_implemented() -> None:
    """Test that YAML generation raises NotImplementedError."""
    with pytest.raises(NotImplementedError, match="YAML generation"):
        ConfigGenerator.generate_yaml()


def test_config_generator_none_default() -> None:
    """Test that None defaults are handled correctly."""

    @configurable(namespace="none_test")
    class NoneClass:
        def __init__(self, *, optional_param: str | None = None) -> None:
            pass

    toml = ConfigGenerator.generate_toml()
    assert 'optional_param = ""' in toml
