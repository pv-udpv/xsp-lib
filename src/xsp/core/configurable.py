"""Configurable decorator for explicit configuration control."""

from typing import Any, TypeVar, get_type_hints
import inspect
from dataclasses import dataclass

T = TypeVar("T")


@dataclass
class ConfigMetadata:
    """Metadata for configurable class."""
    cls: type
    namespace: str
    description: str | None
    parameters: dict[str, "ParameterInfo"]


@dataclass
class ParameterInfo:
    """Information about configurable parameter."""
    name: str
    type: type | str
    default: Any
    description: str | None = None


# Global registry of configurable classes
_CONFIGURABLE_REGISTRY: dict[str, ConfigMetadata] = {}


def configurable(
    *,
    namespace: str | None = None,
    description: str | None = None,
):
    """
    Mark class as configurable.
    
    Extracts __init__ parameters and registers them in the global
    configuration registry. Enables automatic config generation.
    
    Args:
        namespace: Configuration namespace (e.g., "vast", "openrtb")
                  Defaults to module name if not provided
        description: Human-readable description for documentation
    
    Example:
        @configurable(
            namespace="vast",
            description="VAST protocol upstream settings"
        )
        class VastUpstream:
            def __init__(
                self,
                transport: Transport,
                endpoint: str,
                *,
                version: VastVersion = VastVersion.V4_2,
                enable_macros: bool = True,
                validate_xml: bool = False,
                timeout: float = 30.0,
            ):
                ...
        
        Generates config section:
        [vast]
        # VAST protocol upstream settings
        version = "4.2"
        enable_macros = true
        validate_xml = false
        timeout = 30.0
    """
    def decorator(cls: type[T]) -> type[T]:
        # Determine namespace
        ns = namespace or cls.__module__.split(".")[-1]
        
        # Extract parameters from __init__
        params = _extract_parameters(cls)
        
        # Create metadata
        metadata = ConfigMetadata(
            cls=cls,
            namespace=ns,
            description=description,
            parameters=params,
        )
        
        # Register
        registry_key = f"{ns}.{cls.__name__}"
        _CONFIGURABLE_REGISTRY[registry_key] = metadata
        
        # Store metadata on class for introspection
        cls._config_namespace = ns  # type: ignore
        cls._config_description = description  # type: ignore
        cls._config_parameters = params  # type: ignore
        
        return cls
    
    return decorator


def _extract_parameters(cls: type) -> dict[str, ParameterInfo]:
    """
    Extract configurable parameters from class __init__.
    
    Only extracts keyword-only parameters (after *) to avoid
    including required positional args like `transport`.
    """
    sig = inspect.signature(cls.__init__)
    try:
        type_hints = get_type_hints(cls.__init__)
    except Exception:
        type_hints = {}
    
    params: dict[str, ParameterInfo] = {}
    
    # Track if we've seen * (keyword-only marker)
    kwonly_started = False
    
    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue
        
        # Mark start of keyword-only args
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            kwonly_started = True
            continue
        
        # Only include keyword-only args with defaults
        if not kwonly_started:
            continue
        
        if param.default == inspect.Parameter.empty:
            continue
        
        # Extract type and default
        param_type = type_hints.get(param_name, Any)
        default_value = param.default
        
        # Extract description from docstring if available
        description = _extract_param_description(
            cls.__init__.__doc__, param_name
        )
        
        params[param_name] = ParameterInfo(
            name=param_name,
            type=param_type,
            default=default_value,
            description=description,
        )
    
    return params


def _extract_param_description(docstring: str | None, param_name: str) -> str | None:
    """
    Extract parameter description from docstring.
    
    Supports Google-style docstrings:
        Args:
            param_name: Description here
    """
    if not docstring:
        return None
    
    lines = docstring.split("\n")
    in_args_section = False
    
    for line in lines:
        stripped = line.strip()
        
        if stripped.startswith("Args:"):
            in_args_section = True
            continue
        
        if in_args_section:
            # End of Args section
            if stripped and not stripped.startswith(" ") and not param_name in stripped:
                break
            
            # Check for param
            if param_name in stripped and ":" in stripped:
                parts = stripped.split(":", 1)
                if len(parts) == 2:
                    return parts[1].strip()
    
    return None


def get_configurable_registry() -> dict[str, ConfigMetadata]:
    """Get all registered configurable classes."""
    return _CONFIGURABLE_REGISTRY.copy()


def get_configurable_by_namespace(namespace: str) -> list[ConfigMetadata]:
    """Get all configurables for a specific namespace."""
    return [
        metadata
        for key, metadata in _CONFIGURABLE_REGISTRY.items()
        if metadata.namespace == namespace
    ]
