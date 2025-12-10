"""Tests for @configurable decorator."""

import pytest

from xsp.core.configurable import (
    configurable,
    get_configurable_registry,
    get_configurable_by_namespace,
)
from xsp.core.config_generator import ConfigGenerator


def test_configurable_decorator():
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


def test_configurable_without_namespace():
    """Test @configurable with auto-detected namespace."""
    
    @configurable(description="Auto namespace")
    class AutoClass:
        def __init__(self, *, value: str = "test"):
            pass
    
    registry = get_configurable_registry()
    
    # Namespace should be auto-detected from module
    matching = [k for k in registry.keys() if "AutoClass" in k]
    assert len(matching) > 0


def test_kwonly_params_only():
    """Test that only keyword-only params are extracted."""
    
    @configurable(namespace="test2")
    class TestClass2:
        def __init__(self, required: str, *, optional: int = 10):
            pass
    
    registry = get_configurable_registry()
    params = registry["test2.TestClass2"].parameters
    
    # Only optional should be in params (required is positional)
    assert "required" not in params
    assert "optional" in params


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
    
    assert len(ns1_items) >= 1
    assert len(ns2_items) >= 1
    assert any(m.cls.__name__ == "Class1" for m in ns1_items)
    assert any(m.cls.__name__ == "Class2" for m in ns2_items)


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
    
    @configurable(namespace="test3")
    class TestA:
        def __init__(self, *, param: int = 1):
            pass
    
    @configurable(namespace="test3")
    class TestB:
        def __init__(self, *, param: int = 2):
            pass
    
    # Group by namespace - both should be in same section
    toml_ns = ConfigGenerator.generate_toml(group_by="namespace")
    assert "[test3]" in toml_ns
    
    # Group by class - separate sections
    toml_class = ConfigGenerator.generate_toml(group_by="class")
    assert "[testa]" in toml_class or "TestA" in toml_class


def test_empty_registry():
    """Test behavior with empty registry."""
    # Clear registry for this test
    from xsp.core.configurable import _CONFIGURABLE_REGISTRY
    original = _CONFIGURABLE_REGISTRY.copy()
    _CONFIGURABLE_REGISTRY.clear()
    
    toml = ConfigGenerator.generate_toml()
    assert "No configurable classes found" in toml
    
    # Restore
    _CONFIGURABLE_REGISTRY.update(original)
