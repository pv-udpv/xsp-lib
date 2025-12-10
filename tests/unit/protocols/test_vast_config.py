"""Tests for VAST configuration generation."""

import pytest

from xsp.core.config_generator import ConfigGenerator


@pytest.fixture(autouse=True)
def setup_vast_registry():
    """Setup: Import VAST classes to ensure they're registered."""
    # Import to register classes
    from xsp.protocols.vast import MacroSubstitutor, VastUpstream, VmapUpstream
    
    # Clear any test pollution from other tests
    from xsp.core.configurable import _CONFIGURABLE_REGISTRY
    
    # Only keep VAST-related namespaces
    keys_to_keep = [k for k in _CONFIGURABLE_REGISTRY if k.startswith("vast") or k == "vmap"]
    keys_to_remove = [k for k in _CONFIGURABLE_REGISTRY if k not in keys_to_keep]
    for key in keys_to_remove:
        del _CONFIGURABLE_REGISTRY[key]
    
    # Re-import to ensure VAST classes are registered
    import importlib
    import xsp.protocols.vast.upstream
    import xsp.protocols.vast.macros
    importlib.reload(xsp.protocols.vast.macros)
    importlib.reload(xsp.protocols.vast.upstream)
    
    yield


def test_vast_config_generation():
    """Test VAST configuration template generation."""
    toml = ConfigGenerator.generate_toml()

    # Check VAST section
    assert "[vast]" in toml
    assert "VAST protocol upstream for video ad serving" in toml
    assert "version = " in toml
    assert "enable_macros = " in toml
    assert "validate_xml = " in toml


def test_vmap_config_generation():
    """Test VMAP configuration template generation."""
    toml = ConfigGenerator.generate_toml()

    # Check VMAP section
    assert "[vmap]" in toml
    assert "VMAP upstream for video ad pod scheduling" in toml


def test_vast_macros_config_generation():
    """Test VAST macros configuration template generation."""
    toml = ConfigGenerator.generate_toml()

    # Check VAST macros section
    assert "[vast.macros]" in toml
    assert "IAB macro substitution configuration" in toml
    assert "enable_cachebusting = " in toml
    assert "enable_timestamp = " in toml


def test_vast_upstream_with_defaults():
    """Test VastUpstream uses configuration defaults."""
    from xsp.transports.memory import MemoryTransport
    from xsp.protocols.vast import VastUpstream

    # Create upstream with default config
    upstream = VastUpstream(
        transport=MemoryTransport(b"<VAST/>"),
        endpoint="https://example.com/vast",
    )

    # Check defaults are applied
    assert upstream.version.value == "4.2"
    assert upstream.validate_xml is False
    assert upstream.macro_substitutor is not None


def test_vast_upstream_with_custom_config():
    """Test VastUpstream with custom configuration."""
    from xsp.protocols.vast.types import VastVersion
    from xsp.transports.memory import MemoryTransport
    from xsp.protocols.vast import VastUpstream

    # Create upstream with custom config
    upstream = VastUpstream(
        transport=MemoryTransport(b"<VAST/>"),
        endpoint="https://example.com/vast",
        version=VastVersion.V3_0,
        enable_macros=False,
        validate_xml=True,
    )

    # Check custom config is applied
    assert upstream.version == VastVersion.V3_0
    assert upstream.validate_xml is True
    assert upstream.macro_substitutor is None


def test_macro_substitutor_with_defaults():
    """Test MacroSubstitutor uses configuration defaults."""
    from xsp.protocols.vast import MacroSubstitutor
    
    substitutor = MacroSubstitutor()

    # Check defaults are applied
    assert "TIMESTAMP" in substitutor.providers
    assert "CACHEBUSTING" in substitutor.providers


def test_macro_substitutor_with_custom_config():
    """Test MacroSubstitutor with custom configuration."""
    from xsp.protocols.vast import MacroSubstitutor
    
    substitutor = MacroSubstitutor(
        enable_timestamp=False,
        enable_cachebusting=True,
    )

    # Check custom config is applied
    assert "TIMESTAMP" not in substitutor.providers
    assert "CACHEBUSTING" in substitutor.providers


def test_generated_toml_format():
    """Test that generated TOML has proper format."""
    toml = ConfigGenerator.generate_toml()

    # Should have section headers
    assert toml.count("[vast]") == 1
    assert toml.count("[vmap]") == 1
    assert toml.count("[vast.macros]") == 1

    # Should have comments with descriptions
    assert "# VAST protocol upstream for video ad serving" in toml
    assert "# Source: VastUpstream" in toml

    # Should have valid TOML values
    assert 'version = "4.2"' in toml
    assert "enable_macros = true" in toml
    assert "validate_xml = false" in toml
    assert "enable_cachebusting = true" in toml
    assert "enable_timestamp = true" in toml
