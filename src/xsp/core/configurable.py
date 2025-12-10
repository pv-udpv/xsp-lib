"""Configuration decorator and registry for xsp-lib.

Provides @configurable decorator to mark classes for configuration generation
and a registry to track all configurable classes.
"""

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar, get_type_hints

# Global registry for configurable classes
_CONFIGURABLE_REGISTRY: dict[str, "ConfigurableMetadata"] = {}

T = TypeVar("T")


@dataclass
class ParameterInfo:
    """Information about a configurable parameter."""

    name: str
    type: type | str
    default: Any
    description: str = ""


@dataclass
class ConfigurableMetadata:
    """Metadata for a configurable class."""

    cls: type
    namespace: str
    description: str = ""
    parameters: dict[str, ParameterInfo] = field(default_factory=dict)


def configurable(
    *,
    namespace: str,
    description: str = "",
) -> Callable[[type[T]], type[T]]:
    """
    Decorator to mark a class as configurable.

    Args:
        namespace: Configuration namespace (e.g., "http", "vast")
        description: Optional description of the configurable class

    Returns:
        Decorated class

    Example:
        @configurable(namespace="http", description="HTTP transport settings")
        class HttpTransport:
            def __init__(self, *, timeout: float = 30.0, retries: int = 3):
                pass
    """

    def decorator(cls: type[T]) -> type[T]:
        # Extract parameter information from __init__
        parameters: dict[str, ParameterInfo] = {}

        if hasattr(cls, "__init__"):
            sig = inspect.signature(cls.__init__)
            try:
                type_hints = get_type_hints(cls.__init__)
            except Exception:
                type_hints = {}

            for param_name, param in sig.parameters.items():
                # Skip 'self' parameter
                if param_name == "self":
                    continue

                # Only include keyword-only parameters with defaults
                if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default is not inspect.Parameter.empty:
                    param_type = type_hints.get(param_name, Any)
                    parameters[param_name] = ParameterInfo(
                        name=param_name,
                        type=param_type,
                        default=param.default,
                        description="",
                    )

        # Create and register metadata
        metadata = ConfigurableMetadata(
            cls=cls,
            namespace=namespace,
            description=description,
            parameters=parameters,
        )

        # Use fully qualified name as registry key
        key = f"{cls.__module__}.{cls.__qualname__}"
        _CONFIGURABLE_REGISTRY[key] = metadata

        return cls

    return decorator


def get_configurable_registry() -> dict[str, ConfigurableMetadata]:
    """
    Get the global configurable registry.

    Returns:
        Dictionary mapping class keys to ConfigurableMetadata
    """
    return _CONFIGURABLE_REGISTRY.copy()


def clear_configurable_registry() -> None:
    """Clear the configurable registry (useful for testing)."""
    _CONFIGURABLE_REGISTRY.clear()
