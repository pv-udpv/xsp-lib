"""Configuration decorator for XSP classes.

Provides @configurable decorator to mark classes for configuration management.
"""

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

# Global registry of configurable classes
_CONFIGURABLE_REGISTRY: dict[str, dict[str, Any]] = {}


def configurable(
    *,
    namespace: str,
    description: str,
) -> Callable[[type[T]], type[T]]:
    """
    Decorator to mark a class as configurable.

    Registers the class for configuration generation and management.

    Args:
        namespace: Configuration namespace (e.g., "vast", "vmap", "vast.macros")
        description: Human-readable description of the class

    Returns:
        Class decorator

    Example:
        >>> @configurable(namespace="vast", description="VAST upstream")
        ... class VastUpstream:
        ...     def __init__(self, *, version: str = "4.2"):
        ...         self.version = version
    """

    def decorator(cls: type[T]) -> type[T]:
        """Register class in configurable registry."""
        import inspect

        # Get __init__ signature
        init_sig = inspect.signature(cls.__init__)
        params = {}

        # Extract keyword-only parameters (after *)
        for name, param in init_sig.parameters.items():
            if name in ("self", "args", "kwargs"):
                continue

            # Only process keyword-only parameters with defaults
            if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default != inspect.Parameter.empty:
                params[name] = {
                    "default": param.default,
                    "annotation": param.annotation if param.annotation != inspect.Parameter.empty else None,
                }

        # Register in global registry
        _CONFIGURABLE_REGISTRY[namespace] = {
            "class": cls,
            "description": description,
            "params": params,
        }

        return cls

    return decorator


def get_configurable_registry() -> dict[str, dict[str, Any]]:
    """
    Get the global configurable registry.

    Returns:
        Dictionary mapping namespace to class metadata
    """
    return _CONFIGURABLE_REGISTRY.copy()
