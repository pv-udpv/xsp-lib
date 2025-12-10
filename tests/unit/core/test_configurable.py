"""Tests for configurable decorator and registry."""

import pytest

from xsp.core.configurable import (
    ConfigurableMetadata,
    ParameterInfo,
    clear_configurable_registry,
    configurable,
    get_configurable_registry,
)


def test_configurable_decorator():
    """Test basic @configurable decorator functionality."""
    clear_configurable_registry()

    @configurable(namespace="test", description="Test class")
    class TestClass:
        def __init__(self, *, value: str = "default"):
            self.value = value

    registry = get_configurable_registry()
    assert len(registry) == 1

    key = f"{TestClass.__module__}.{TestClass.__qualname__}"
    assert key in registry

    metadata = registry[key]
    assert isinstance(metadata, ConfigurableMetadata)
    assert metadata.cls == TestClass
    assert metadata.namespace == "test"
    assert metadata.description == "Test class"
    assert "value" in metadata.parameters


def test_configurable_parameters():
    """Test parameter extraction from __init__."""
    clear_configurable_registry()

    @configurable(namespace="test")
    class TestClass:
        def __init__(
            self,
            *,
            str_param: str = "test",
            int_param: int = 42,
            float_param: float = 3.14,
            bool_param: bool = True,
        ):
            pass

    registry = get_configurable_registry()
    key = f"{TestClass.__module__}.{TestClass.__qualname__}"
    metadata = registry[key]

    assert len(metadata.parameters) == 4
    assert metadata.parameters["str_param"].default == "test"
    assert metadata.parameters["int_param"].default == 42
    assert metadata.parameters["float_param"].default == 3.14
    assert metadata.parameters["bool_param"].default is True


def test_configurable_ignores_non_keyword_only():
    """Test that non-keyword-only parameters are ignored."""
    clear_configurable_registry()

    @configurable(namespace="test")
    class TestClass:
        def __init__(self, positional, *args, keyword_only: str = "test", **kwargs):
            pass

    registry = get_configurable_registry()
    key = f"{TestClass.__module__}.{TestClass.__qualname__}"
    metadata = registry[key]

    # Should only have keyword_only parameter
    assert len(metadata.parameters) == 1
    assert "keyword_only" in metadata.parameters
    assert "positional" not in metadata.parameters


def test_configurable_ignores_no_default():
    """Test that parameters without defaults are ignored."""
    clear_configurable_registry()

    @configurable(namespace="test")
    class TestClass:
        def __init__(self, *, with_default: str = "test", without_default: int):
            pass

    registry = get_configurable_registry()
    key = f"{TestClass.__module__}.{TestClass.__qualname__}"
    metadata = registry[key]

    # Should only have parameter with default
    assert len(metadata.parameters) == 1
    assert "with_default" in metadata.parameters
    assert "without_default" not in metadata.parameters


def test_multiple_configurable_classes():
    """Test multiple @configurable classes in registry."""
    clear_configurable_registry()

    @configurable(namespace="ns1")
    class Class1:
        def __init__(self, *, param1: str = "value1"):
            pass

    @configurable(namespace="ns2")
    class Class2:
        def __init__(self, *, param2: int = 42):
            pass

    registry = get_configurable_registry()
    assert len(registry) == 2


def test_clear_registry():
    """Test clearing the configurable registry."""
    clear_configurable_registry()

    @configurable(namespace="test")
    class TestClass:
        def __init__(self, *, value: str = "test"):
            pass

    assert len(get_configurable_registry()) == 1

    clear_configurable_registry()
    assert len(get_configurable_registry()) == 0


def test_registry_copy():
    """Test that get_configurable_registry returns a copy."""
    clear_configurable_registry()

    @configurable(namespace="test")
    class TestClass:
        def __init__(self, *, value: str = "test"):
            pass

    registry1 = get_configurable_registry()
    registry2 = get_configurable_registry()

    # Should be equal but not the same object
    assert registry1 == registry2
    assert registry1 is not registry2
