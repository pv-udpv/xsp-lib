"""Configuration file generator for XSP.

Generates TOML configuration templates from @configurable classes.
"""

from enum import Enum
from typing import Any

from .configurable import get_configurable_registry


class ConfigGenerator:
    """Generate TOML configuration templates."""

    @staticmethod
    def generate_toml() -> str:
        """
        Generate TOML configuration template from registered classes.

        Returns:
            TOML configuration string with all registered configurable classes
        """
        registry = get_configurable_registry()
        if not registry:
            return "# No configurable classes registered\n"

        lines = []

        # Sort namespaces for consistent output
        for namespace in sorted(registry.keys()):
            metadata = registry[namespace]
            lines.append(f"[{namespace}]")
            lines.append(f"# {metadata['description']}")
            lines.append(f"# Source: {metadata['class'].__name__}")
            lines.append("")

            # Sort parameters for consistent output
            for param_name in sorted(metadata["params"].keys()):
                param_info = metadata["params"][param_name]
                
                # Add parameter documentation from docstring if available
                # For now, just add type annotation
                annotation = param_info.get("annotation")
                if annotation:
                    type_name = _format_type(annotation)
                    lines.append(f"# Type: {type_name}")

                # Add default value
                default = param_info["default"]
                toml_value = _to_toml_value(default)
                lines.append(f"{param_name} = {toml_value}")
                lines.append("")

            lines.append("")

        return "\n".join(lines)


def _format_type(annotation: Any) -> str:
    """
    Format type annotation for documentation.

    Args:
        annotation: Type annotation object

    Returns:
        Human-readable type string
    """
    if hasattr(annotation, "__name__"):
        return str(annotation.__name__)
    
    # Handle typing module types
    type_str = str(annotation)
    
    # Clean up typing module prefixes
    if type_str.startswith("typing."):
        type_str = type_str[7:]
    
    # Clean up common patterns
    type_str = type_str.replace("typing.", "")
    
    return type_str


def _to_toml_value(value: Any) -> str:
    """
    Convert Python value to TOML representation.

    Args:
        value: Python value

    Returns:
        TOML string representation
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, Enum):
        # Handle enum values
        return f'"{value.value}"'
    elif isinstance(value, str):
        return f'"{value}"'
    elif isinstance(value, (int, float)):
        return str(value)
    elif value is None:
        return '""'  # TOML doesn't have null, use empty string
    else:
        # For other objects, use string representation
        return f'"{str(value)}"'
