"""Configurable decorator for explicit configuration control."""

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar, get_type_hints

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
) -> Callable[[type[T]], type[T]]:
    """
    Mark class as configurable.

    Extracts __init__ parameters and registers them in the global
    configuration registry. Enables automatic config generation.

    Args:
        namespace: Configuration namespace (e.g., "vast", "openrtb")
                  Defaults to module name if not provided
        description: Human-readable description for documentation

    Example:
        ```python
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
        ```

        Generates config section:
        ```toml
        [vast]
        # VAST protocol upstream settings
        version = "4.2"
        enable_macros = true
        validate_xml = false
        timeout = 30.0
        ```
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
        cls._config_namespace = ns  # type: ignore[attr-defined]
        cls._config_description = description  # type: ignore[attr-defined]
        cls._config_parameters = params  # type: ignore[attr-defined]

        return cls

    return decorator


def _extract_parameters(cls: type) -> dict[str, ParameterInfo]:
    """
    Extract configurable parameters from class __init__.

    Only extracts keyword-only parameters (after *) to avoid
    including required positional args like `transport`.
    """
    init_method = cls.__init__  # type: ignore[misc]
    sig = inspect.signature(init_method)
    type_hints = get_type_hints(init_method)
    params: dict[str, ParameterInfo] = {}

    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue

        # Only include keyword-only args with defaults
        if param.kind != inspect.Parameter.KEYWORD_ONLY:
            continue

        if param.default == inspect.Parameter.empty:
            continue

        # Extract type and default
        param_type = type_hints.get(param_name, Any)
        default_value = param.default

        # Extract description from docstring if available
        docstring = init_method.__doc__
        description = _extract_param_description(docstring, param_name)

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
            if stripped and not stripped.startswith(" ") and not stripped.startswith(param_name):
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
