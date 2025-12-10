"""Tests for configurable decorator and config generator."""

import pytest

from xsp.core.config_generator import ConfigGenerator
from xsp.core.configurable import configurable, get_configurable_registry


def test_configurable_decorator():
    """Test that @configurable registers a class."""
    # Clear registry first (to avoid pollution from other tests)
    from xsp.core.configurable import _CONFIGURABLE_REGISTRY
    _CONFIGURABLE_REGISTRY.clear()

    @configurable(namespace="test", description="Test class")
    class TestClass:
        def __init__(self, *, param1: str = "default", param2: int = 42):
            self.param1 = param1
            self.param2 = param2

    registry = get_configurable_registry()
    assert "test" in registry
    assert registry["test"]["description"] == "Test class"
    assert registry["test"]["class"] == TestClass
    assert "param1" in registry["test"]["params"]
    assert "param2" in registry["test"]["params"]
    assert registry["test"]["params"]["param1"]["default"] == "default"
    assert registry["test"]["params"]["param2"]["default"] == 42


def test_configurable_ignores_positional():
    """Test that @configurable ignores positional parameters."""
    from xsp.core.configurable import _CONFIGURABLE_REGISTRY
    _CONFIGURABLE_REGISTRY.clear()

    @configurable(namespace="test2", description="Test class 2")
    class TestClass2:
        def __init__(self, required: str, *, optional: str = "default"):
            self.required = required
            self.optional = optional

    registry = get_configurable_registry()
    assert "test2" in registry
    # Should only have optional (keyword-only with default)
    assert "optional" in registry["test2"]["params"]
    assert "required" not in registry["test2"]["params"]


def test_config_generator_empty():
    """Test config generator with no registered classes."""
    from xsp.core.configurable import _CONFIGURABLE_REGISTRY
    _CONFIGURABLE_REGISTRY.clear()

    toml = ConfigGenerator.generate_toml()
    assert "No configurable classes registered" in toml


def test_config_generator_basic():
    """Test config generator with a basic class."""
    from xsp.core.configurable import _CONFIGURABLE_REGISTRY
    _CONFIGURABLE_REGISTRY.clear()

    @configurable(namespace="basic", description="Basic test class")
    class BasicClass:
        def __init__(self, *, enabled: bool = True, timeout: float = 30.0):
            self.enabled = enabled
            self.timeout = timeout

    toml = ConfigGenerator.generate_toml()
    assert "[basic]" in toml
    assert "Basic test class" in toml
    assert "Source: BasicClass" in toml
    assert "enabled = true" in toml
    assert "timeout = 30.0" in toml


def test_config_generator_multiple_namespaces():
    """Test config generator with multiple namespaces."""
    from xsp.core.configurable import _CONFIGURABLE_REGISTRY
    _CONFIGURABLE_REGISTRY.clear()

    @configurable(namespace="first", description="First class")
    class FirstClass:
        def __init__(self, *, value: str = "first"):
            self.value = value

    @configurable(namespace="second", description="Second class")
    class SecondClass:
        def __init__(self, *, value: str = "second"):
            self.value = value

    toml = ConfigGenerator.generate_toml()
    assert "[first]" in toml
    assert "[second]" in toml
    assert "First class" in toml
    assert "Second class" in toml


def test_config_generator_nested_namespace():
    """Test config generator with nested namespace."""
    from xsp.core.configurable import _CONFIGURABLE_REGISTRY
    _CONFIGURABLE_REGISTRY.clear()

    @configurable(namespace="parent.child", description="Nested class")
    class NestedClass:
        def __init__(self, *, nested: bool = False):
            self.nested = nested

    toml = ConfigGenerator.generate_toml()
    assert "[parent.child]" in toml
    assert "Nested class" in toml
