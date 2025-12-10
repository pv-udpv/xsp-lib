"""Generate configuration templates from @configurable registry."""

import enum
from collections import defaultdict
from typing import Any

from .configurable import ConfigMetadata, ParameterInfo, get_configurable_registry


class ConfigGenerator:
    """Generate configuration files from @configurable registry."""

    @staticmethod
    def generate_toml(group_by: str = "namespace") -> str:
        """
        Generate TOML configuration template.

        Args:
            group_by: Grouping strategy ("namespace" or "class")

        Returns:
            TOML configuration string
        """
        registry = get_configurable_registry()

        if group_by == "namespace":
            grouped = ConfigGenerator._group_by_namespace(registry)
        elif group_by == "class":
            grouped = ConfigGenerator._group_by_class(registry)
        else:
            raise ValueError(f"Unknown group_by: {group_by}")

        lines = [
            "# XSP-lib Configuration Template",
            "# Auto-generated from @configurable registry",
            "#",
            "# This file contains all configurable parameters from xsp-lib.",
            "# Uncomment and modify values as needed.",
            "",
        ]

        for section, metadata_list in sorted(grouped.items()):
            lines.append(f"[{section}]")

            for metadata in metadata_list:
                if metadata.description:
                    lines.append(f"# {metadata.description}")

                lines.append(f"# Source: {metadata.cls.__name__}")
                lines.append("")

                for param_name, param_info in metadata.parameters.items():
                    # Add parameter description
                    if param_info.description:
                        lines.append(f"# {param_info.description}")

                    # Add type hint as comment
                    type_str = ConfigGenerator._format_type(param_info.type)
                    lines.append(f"# Type: {type_str}")

                    # Add parameter with default value
                    value_str = ConfigGenerator._format_toml_value(param_info.default)
                    lines.append(f"{param_name} = {value_str}")
                    lines.append("")

            lines.append("")  # Extra blank line between sections

        return "\n".join(lines)

    @staticmethod
    def generate_yaml(group_by: str = "namespace") -> str:
        """Generate YAML configuration template."""
        # Similar implementation for YAML
        raise NotImplementedError("YAML generation coming in future PR")

    @staticmethod
    def _group_by_namespace(
        registry: dict[str, ConfigMetadata]
    ) -> dict[str, list[ConfigMetadata]]:
        """Group metadata by namespace."""
        grouped: dict[str, list[ConfigMetadata]] = defaultdict(list)

        for metadata in registry.values():
            grouped[metadata.namespace].append(metadata)

        return grouped

    @staticmethod
    def _group_by_class(
        registry: dict[str, ConfigMetadata]
    ) -> dict[str, list[ConfigMetadata]]:
        """Group metadata by class name (lowercased)."""
        grouped: dict[str, list[ConfigMetadata]] = defaultdict(list)

        for metadata in registry.values():
            key = metadata.cls.__name__.lower()
            grouped[key].append(metadata)

        return grouped

    @staticmethod
    def _format_type(type_hint: type | str) -> str:
        """Format type hint for display."""
        if isinstance(type_hint, str):
            return type_hint

        if hasattr(type_hint, "__name__"):
            return type_hint.__name__

        return str(type_hint)

    @staticmethod
    def _format_toml_value(value: Any) -> str:
        """Format Python value as TOML."""
        if value is None:
            return '""'
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, enum.Enum):
            return f'"{value.value}"'
        elif isinstance(value, str):
            return f'"{value}"'
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, (list, tuple)):
            items = [ConfigGenerator._format_toml_value(item) for item in value]
            return f"[{', '.join(items)}]"
        elif isinstance(value, dict):
            # Inline table format
            items = [
                f"{k} = {ConfigGenerator._format_toml_value(v)}" for k, v in value.items()
            ]
            return f"{{ {', '.join(items)} }}"
        else:
            return f'"{value}"'
