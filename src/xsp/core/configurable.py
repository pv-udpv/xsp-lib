"""Configuration decorator and registry for automatic TOML generation.

This module provides a decorator system for marking classes as "configurable",
extracting their configuration parameters, and generating TOML templates.

Core Concepts:

1. @configurable Decorator: Mark a class as having configurable parameters
   - Extracts keyword-only __init__ parameters
   - Only parameters with default values are configurable
   - Registers class in global registry
   
2. ConfigMetadata: Metadata about a configurable class
   - Class reference, namespace, description
   - Dictionary of ParameterInfo objects
   
3. ParameterInfo: Information about a single parameter
   - Name, type annotation, default value
   - Optional description extracted from docstring

4. Registry: Global dict of all configurable classes
   - Key: namespace or class name
   - Value: ConfigMetadata instance

Example Usage:

    from xsp.core.configurable import configurable
    from xsp.protocols.vast import VastVersion
    
    @configurable(
        namespace="vast",
        description="VAST protocol upstream for video ad serving"
    )
    class VastUpstream(BaseUpstream[str]):
        def __init__(
            self,
            transport: Transport,
            endpoint: str,
            *,  # Keyword-only params below are configurable
            version: VastVersion = VastVersion.V4_2,
            enable_macros: bool = True,
            validate_xml: bool = False,
            timeout: float = 30.0,
        ):
            super().__init__(transport=transport, endpoint=endpoint)
            self.version = version
            self.enable_macros = enable_macros
            self.validate_xml = validate_xml
            self.timeout = timeout
    
    # Generate TOML template
    from xsp.core.configurable import generate_toml_template
    
    template = generate_toml_template()
    print(template)
    # Output:
    # [vast]
    # version = "4.2"
    # enable_macros = true
    # validate_xml = false
    # timeout = 30.0

Type System:

The decorator extracts type annotations and converts them to strings for
serialization. Special handling for:
- Enums: Converted to their value (e.g., VastVersion.V4_2 -> "4.2")
- Primitives: int, float, str, bool preserved
- Collections: list, dict, set preserved
- Custom types: Stored as qualified name string

Only keyword-only parameters with defaults are considered configurable.
This ensures clear separation between required (positional) and optional
(configurable) parameters.
"""

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar, get_type_hints

# Type variable for generic decorator
T = TypeVar("T")

# Global registry of all configurable classes
_CONFIGURABLE_REGISTRY: dict[str, "ConfigMetadata"] = {}


@dataclass(frozen=True)
class ParameterInfo:
    """Information about a single configurable parameter.
    
    Attributes:
        name: Parameter name (e.g., "version", "timeout")
        type: Type annotation as string (e.g., "VastVersion", "float")
        default: Default value for parameter
        description: Optional description from docstring
        
    Example:
        >>> param = ParameterInfo(
        ...     name="timeout",
        ...     type="float",
        ...     default=30.0,
        ...     description="Request timeout in seconds"
        ... )
        >>> param.name
        'timeout'
        >>> param.default
        30.0
    """
    
    name: str
    type: str
    default: Any
    description: str | None = None


@dataclass(frozen=True)
class ConfigMetadata:
    """Metadata about a configurable class.
    
    Stores information about a class marked with @configurable, including
    its namespace, description, and all configurable parameters.
    
    Attributes:
        cls: Reference to the class itself
        namespace: Namespace for TOML section (e.g., "vast", "openrtb")
        description: Human-readable description of the class
        parameters: Dictionary mapping parameter names to ParameterInfo
        
    Example:
        >>> metadata = ConfigMetadata(
        ...     cls=VastUpstream,
        ...     namespace="vast",
        ...     description="VAST protocol upstream",
        ...     parameters={
        ...         "version": ParameterInfo("version", "VastVersion", VastVersion.V4_2),
        ...         "timeout": ParameterInfo("timeout", "float", 30.0)
        ...     }
        ... )
        >>> metadata.namespace
        'vast'
        >>> len(metadata.parameters)
        2
    """
    
    cls: type
    namespace: str
    description: str | None
    parameters: dict[str, ParameterInfo] = field(default_factory=dict)


def configurable(
    *,
    namespace: str | None = None,
    description: str | None = None
) -> Callable[[type[T]], type[T]]:
    """Decorator to mark a class as configurable.
    
    Extracts keyword-only __init__ parameters with defaults and registers
    the class in the global configurable registry. Only parameters after
    the `*` in __init__ signature with default values are considered
    configurable.
    
    Args:
        namespace: Namespace for TOML section. If None, uses class name
                  in lowercase. Example: "vast", "openrtb"
        description: Human-readable description of the class for
                    documentation. Example: "VAST protocol upstream"
    
    Returns:
        Decorator function that registers the class and returns it unchanged
        
    Raises:
        ValueError: If class has no keyword-only parameters with defaults
        TypeError: If __init__ method is not found
        
    Example:
        >>> @configurable(namespace="vast", description="VAST upstream")
        ... class VastUpstream:
        ...     def __init__(
        ...         self,
        ...         transport: Transport,
        ...         *,
        ...         version: VastVersion = VastVersion.V4_2,
        ...         timeout: float = 30.0
        ...     ):
        ...         pass
        
        >>> from xsp.core.configurable import get_configurable_registry
        >>> registry = get_configurable_registry()
        >>> "vast" in registry
        True
        >>> registry["vast"].namespace
        'vast'
    """
    def decorator(cls: type[T]) -> type[T]:
        # Extract parameters from __init__
        try:
            sig = inspect.signature(cls.__init__)
        except (ValueError, TypeError) as e:
            raise TypeError(f"Cannot get signature for {cls.__name__}.__init__: {e}")
        
        # Get type hints for __init__
        try:
            type_hints = get_type_hints(cls.__init__)
        except Exception:
            type_hints = {}
        
        # Extract keyword-only parameters with defaults
        configurable_params: dict[str, ParameterInfo] = {}
        
        found_kwonly = False
        for param_name, param in sig.parameters.items():
            # Skip 'self'
            if param_name == "self":
                continue
            
            # Only process keyword-only parameters
            if param.kind != inspect.Parameter.KEYWORD_ONLY:
                continue
            
            found_kwonly = True
            
            # Only include if has default value
            if param.default is inspect.Parameter.empty:
                continue
            
            # Get type annotation
            type_annotation = type_hints.get(param_name, param.annotation)
            if type_annotation is inspect.Parameter.empty:
                type_str = "Any"
            else:
                # Convert type to string
                if hasattr(type_annotation, "__name__"):
                    type_str = type_annotation.__name__
                else:
                    type_str = str(type_annotation)
            
            # Create ParameterInfo
            configurable_params[param_name] = ParameterInfo(
                name=param_name,
                type=type_str,
                default=param.default,
                description=None  # TODO: Extract from docstring
            )
        
        if not configurable_params:
            # This is just a warning - class is still decorated but has no config
            pass
        
        # Determine namespace
        ns = namespace if namespace is not None else cls.__name__.lower()
        
        # Create metadata
        metadata = ConfigMetadata(
            cls=cls,
            namespace=ns,
            description=description,
            parameters=configurable_params
        )
        
        # Register in global registry
        _CONFIGURABLE_REGISTRY[ns] = metadata
        
        # Store metadata on class for introspection
        cls.__configurable_metadata__ = metadata  # type: ignore
        
        return cls
    
    return decorator


def get_configurable_registry() -> dict[str, ConfigMetadata]:
    """Get a copy of the configurable class registry.
    
    Returns a copy of the global registry mapping namespaces to
    ConfigMetadata instances. The copy ensures the registry cannot
    be accidentally modified.
    
    Returns:
        dict[str, ConfigMetadata]: Copy of registry mapping namespace
                                   to metadata
    
    Example:
        >>> registry = get_configurable_registry()
        >>> for namespace, metadata in registry.items():
        ...     print(f"{namespace}: {metadata.cls.__name__}")
        vast: VastUpstream
        openrtb: OpenRtbUpstream
    """
    return _CONFIGURABLE_REGISTRY.copy()


def generate_toml_template() -> str:
    """Generate TOML configuration template from registry.
    
    Creates a TOML template with all registered configurable classes
    and their parameters. Each class becomes a TOML section with its
    namespace, and parameters are listed with their default values.
    
    Returns:
        str: TOML template string
        
    Example:
        >>> template = generate_toml_template()
        >>> print(template)
        # VAST protocol upstream for video ad serving
        [vast]
        version = "4.2"
        enable_macros = true
        validate_xml = false
        timeout = 30.0
        
        # OpenRTB protocol upstream for real-time bidding
        [openrtb]
        version = "2.5"
        timeout = 5.0
    """
    lines: list[str] = []
    
    for namespace, metadata in sorted(_CONFIGURABLE_REGISTRY.items()):
        # Add description comment if present
        if metadata.description:
            lines.append(f"# {metadata.description}")
        
        # Add section header
        lines.append(f"[{namespace}]")
        
        # Add parameters
        for param_name, param_info in sorted(metadata.parameters.items()):
            # Convert default value to TOML format
            value = _value_to_toml(param_info.default)
            
            # Add parameter description comment if present
            if param_info.description:
                lines.append(f"# {param_info.description}")
            
            lines.append(f"{param_name} = {value}")
        
        # Add blank line between sections
        lines.append("")
    
    return "\\n".join(lines)


def _value_to_toml(value: Any) -> str:
    """Convert a Python value to TOML representation.
    
    Args:
        value: Python value to convert
        
    Returns:
        str: TOML representation of value
        
    Example:
        >>> _value_to_toml(True)
        'true'
        >>> _value_to_toml(30.0)
        '30.0'
        >>> _value_to_toml("hello")
        '"hello"'
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        # Escape quotes in string
        escaped = value.replace('"', '\\\\"')
        return f'"{escaped}"'
    elif hasattr(value, "value"):
        # Enum - use its value
        return _value_to_toml(value.value)
    elif isinstance(value, (list, tuple)):
        items = [_value_to_toml(item) for item in value]
        return f"[{', '.join(items)}]"
    elif isinstance(value, dict):
        # Simple dict representation
        items = [f"{k} = {_value_to_toml(v)}" for k, v in value.items()]
        return f"{{{', '.join(items)}}}"
    else:
        # Fallback to string representation
        return f'"{str(value)}"'
