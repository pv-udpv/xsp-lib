"""Configurable decorator for explicit configuration control."""

from __future__ import annotations

from typing import Any, TypeVar, get_type_hints
import inspect
from dataclasses import dataclass, field

T = TypeVar("T")


@dataclass
class ParameterInfo:
    """Information about configurable parameter."""

    name: str
    type_hint: type | str
    default: Any
    description: str | None = None


@dataclass
class ConfigMetadata:
    """Metadata for configurable class."""

    cls: type
    namespace: str
    description: str | None
    parameters: dict[str, ParameterInfo] = field(default_factory=dict)


# Global registry of configurable classes
_CONFIGURABLE_REGISTRY: dict[str, ConfigMetadata] = {}


def configurable(
    *,
    namespace: str | None = None,
    description: str | None = None,
) -> Any:
    """
    Mark class as configurable.

    Extracts __init__ parameters and registers them in the global
    configuration registry. Enables automatic config generation.

    Args:
        namespace: Configuration namespace (e.g., "vast", "openrtb", "http")
                  Defaults to module name if not provided
        description: Human-readable description for documentation

    Example:
        ```python
        @configurable(
            namespace="http",
            description="HTTP transport configuration"
        )
        class HttpTransport:
            def __init__(
                self,
                client: Any | None = None,
                *,
                method: str = "GET",
                timeout: float = 30.0,
                max_retries: int = 3,
            ):
                ...
        ```

        Generates config section:
        ```toml
        [http]
        # HTTP transport configuration
        method = "GET"
        timeout = 30.0
        max_retries = 3
        ```

    Note:
        Only keyword-only parameters (after *) with default values
        are extracted. Required positional args are not configurable.
    """

    def decorator(cls: type[T]) -> type[T]:
        # Determine namespace from module if not provided
        ns = namespace
        if ns is None:
            # Extract from module path: xsp.transports.http -> http
            module_parts = cls.__module__.split(".")
            ns = module_parts[-1] if module_parts else "config"

        # Extract parameters from __init__
        params = _extract_parameters(cls)

        # Create metadata
        metadata = ConfigMetadata(
            cls=cls,
            namespace=ns,
            description=description,
            parameters=params,
        )

        # Register in global registry
        registry_key = f"{ns}.{cls.__name__}"
        _CONFIGURABLE_REGISTRY[registry_key] = metadata

        # Store metadata on class for introspection
        cls._config_namespace = ns  # type: ignore[attr-defined]
        cls._config_description = description  # type: ignore[attr-defined]
        cls._config_parameters = params  # type: ignore[attr-defined]

        return cls

    return decorator


def _extract_parameters(cls: type) -> dict[str, ParameterInfo]:
    """
    Extract configurable parameters from class __init__.

    Only extracts keyword-only parameters (after *) with default values
    to avoid including required positional args.
    """
    try:
        sig = inspect.signature(cls.__init__)
    except (ValueError, TypeError):
        # __init__ not available or is built-in
        return {}

    try:
        type_hints = get_type_hints(cls.__init__)
    except Exception:
        # Type hints may fail for various reasons
        type_hints = {}

    params: dict[str, ParameterInfo] = {}

    # Track if we've entered keyword-only section
    kwonly_started = False

    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue

        # Detect start of keyword-only args
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            kwonly_started = True
            continue

        # Check if this is keyword-only
        is_kwonly = param.kind == inspect.Parameter.KEYWORD_ONLY or kwonly_started

        # Only include keyword-only params with defaults
        if not is_kwonly:
            continue

        if param.default == inspect.Parameter.empty:
            continue

        # Extract type and default
        param_type = type_hints.get(param_name, Any)
        default_value = param.default

        # Extract description from docstring if available
        param_description = _extract_param_description(
            cls.__init__.__doc__, param_name
        )

        params[param_name] = ParameterInfo(
            name=param_name,
            type_hint=param_type,
            default=default_value,
            description=param_description,
        )

    return params


def _extract_param_description(docstring: str | None, param_name: str) -> str | None:
    """
    Extract parameter description from Google-style docstring.

    Example:
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
            # End of Args section (next section or unindented line)
            if stripped and not line.startswith((" ", "\t")):
                break

            # Check if this line contains our parameter
            if param_name in stripped and ":" in stripped:
                parts = stripped.split(":", 1)
                if len(parts) == 2 and param_name in parts[0]:
                    return parts[1].strip()

    return None


def get_configurable_registry() -> dict[str, ConfigMetadata]:
    """Get copy of all registered configurable classes."""
    return _CONFIGURABLE_REGISTRY.copy()


def get_configurable_by_namespace(namespace: str) -> list[ConfigMetadata]:
    """Get all configurables for a specific namespace."""
    return [
        metadata
        for metadata in _CONFIGURABLE_REGISTRY.values()
        if metadata.namespace == namespace
    ]


def clear_registry() -> None:
    """Clear the configurable registry (mainly for testing)."""
    _CONFIGURABLE_REGISTRY.clear()
