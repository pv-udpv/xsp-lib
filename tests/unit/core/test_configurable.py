"""Tests for @configurable decorator and registry."""

import pytest

from xsp.core.configurable import (
    configurable,
    get_configurable_registry,
    get_configurable_by_namespace,
    clear_registry,
)
from xsp.core.config_generator import ConfigGenerator


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear registry before each test."""
    clear_registry()
    yield
    clear_registry()


def test_configurable_decorator_basic():
    """Test @configurable decorator registration."""

    @configurable(namespace="test", description="Test class")
    class TestClass:
        def __init__(self, required: str, *, optional: int = 42):
            pass

    registry = get_configurable_registry()

    # Check registration
    assert "test.TestClass" in registry

    metadata = registry["test.TestClass"]
    assert metadata.namespace == "test"
    assert metadata.description == "Test class"
    assert "optional" in metadata.parameters
    assert metadata.parameters["optional"].default == 42


def test_configurable_auto_namespace():
    """Test @configurable with auto-detected namespace."""

    @configurable(description="Auto namespace")
    class AutoClass:
        def __init__(self, *, value: str = "test"):
            pass

    registry = get_configurable_registry()

    # Namespace should be auto-detected from module
    matching = [k for k in registry.keys() if "AutoClass" in k]
    assert len(matching) == 1


def test_kwonly_params_extraction():
    """Test that only keyword-only params are extracted."""

    @configurable(namespace="test")
    class TestClass:
        def __init__(self, required: str, *, optional: int = 10):
            pass

    registry = get_configurable_registry()
    params = registry["test.TestClass"].parameters

    # Only optional should be in params (required is positional)
    assert "required" not in params
    assert "optional" in params
    assert params["optional"].default == 10


def test_multiple_kwonly_params():
    """Test extraction of multiple keyword-only parameters."""

    @configurable(namespace="multi")
    class MultiParam:
        def __init__(
            self,
            *,
            timeout: float = 30.0,
            retries: int = 3,
            enabled: bool = True,
        ):
            pass

    registry = get_configurable_registry()
    params = registry["multi.MultiParam"].parameters

    assert len(params) == 3
    assert params["timeout"].default == 30.0
    assert params["retries"].default == 3
    assert params["enabled"].default is True


def test_get_by_namespace():
    """Test filtering configurables by namespace."""

    @configurable(namespace="ns1")
    class Class1:
        def __init__(self, *, param1: int = 1):
            pass

    @configurable(namespace="ns2")
    class Class2:
        def __init__(self, *, param2: int = 2):
            pass

    ns1_items = get_configurable_by_namespace("ns1")
    ns2_items = get_configurable_by_namespace("ns2")

    assert len(ns1_items) == 1
    assert len(ns2_items) == 1
    assert ns1_items[0].cls.__name__ == "Class1"
    assert ns2_items[0].cls.__name__ == "Class2"


def test_config_generator_toml():
    """Test TOML configuration generation."""

    @configurable(namespace="demo", description="Demo upstream")
    class DemoUpstream:
        def __init__(self, *, timeout: float = 30.0, retries: int = 3):
            pass

    toml = ConfigGenerator.generate_toml()

    assert "[demo]" in toml
    assert "timeout = 30.0" in toml
    assert "retries = 3" in toml
    assert "Demo upstream" in toml


def test_config_generator_type_formatting():
    """Test type formatting in generated config."""

    @configurable(namespace="types")
    class TypeTest:
        def __init__(
            self,
            *,
            string_val: str = "test",
            int_val: int = 42,
            float_val: float = 3.14,
            bool_val: bool = True,
        ):
            pass

    toml = ConfigGenerator.generate_toml()

    assert 'string_val = "test"' in toml
    assert "int_val = 42" in toml
    assert "float_val = 3.14" in toml
    assert "bool_val = true" in toml


def test_config_generator_grouping():
    """Test different grouping strategies."""

    @configurable(namespace="test")
    class TestA:
        def __init__(self, *, param: int = 1):
            pass

    @configurable(namespace="test")
    class TestB:
        def __init__(self, *, param: int = 2):
            pass

    # Group by namespace - both should be in same section
    toml_ns = ConfigGenerator.generate_toml(group_by="namespace")
    assert "[test]" in toml_ns

    # Group by class - separate sections
    toml_class = ConfigGenerator.generate_toml(group_by="class")
    assert "[testa]" in toml_class.lower()
    assert "[testb]" in toml_class.lower()


def test_param_without_default_ignored():
    """Test that keyword-only params without defaults are ignored."""

    @configurable(namespace="test")
    class NoDefault:
        def __init__(self, *, required: int, optional: str = "default"):
            pass

    registry = get_configurable_registry()
    params = registry["test.NoDefault"].parameters

    # Only optional should be extracted
    assert "required" not in params
    assert "optional" in params


def test_class_metadata_attributes():
    """Test that decorator adds metadata to class."""

    @configurable(namespace="test", description="Test desc")
    class MetaTest:
        def __init__(self, *, value: int = 10):
            pass

    assert hasattr(MetaTest, "_config_namespace")
    assert hasattr(MetaTest, "_config_description")
    assert hasattr(MetaTest, "_config_parameters")

    assert MetaTest._config_namespace == "test"
    assert MetaTest._config_description == "Test desc"
    assert "value" in MetaTest._config_parameters


def test_empty_registry_generation():
    """Test config generation with empty registry."""
    clear_registry()

    toml = ConfigGenerator.generate_toml()

    assert "No @configurable classes found" in toml


def test_special_characters_in_string_values():
    """Test TOML generation with special characters in strings."""

    @configurable(namespace="test")
    class SpecialChars:
        def __init__(self, *, path: str = 'path/with"quotes'):
            pass

    toml = ConfigGenerator.generate_toml()

    # Should escape quotes
    assert 'path = "path/with\\"quotes"' in toml or "path =" in toml
